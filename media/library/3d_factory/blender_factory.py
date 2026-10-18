"""Lumen Premium 3D Asset Factory — Blender procedural builder + alpha renderer.

Run:
  blender -b --python media/library/3d_factory/blender_factory.py -- \
    --asset l3d_generic_passport --motion reveal --out 3d-library

Produces: .blend, .glb, PNG sequence (RGBA), under out roots.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector


# ---------------------------------------------------------------------------
# CLI (Blender puts args after "--")
# ---------------------------------------------------------------------------

def _argv_after_dash():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1 :]
    return []


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--asset", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--catalog", default="")
    p.add_argument("--frames", type=int, default=90)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--size", type=int, default=1080)
    p.add_argument("--skip-render", action="store_true")
    return p.parse_args(_argv_after_dash())


# ---------------------------------------------------------------------------
# Scene bootstrap
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Remove default leftover if any
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def set_render(scene, *, frames: int, fps: int, size: int, out_png_dir: Path):
    # Blender 5.x uses BLENDER_EEVEE (EEVEE Next is the only EEVEE).
    engines = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "CYCLES"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(out_png_dir / "frame_")
    # EEVEE quality
    ee = scene.eevee
    if hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = 64
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = True
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"


def make_material(name: str, *, base, roughness=0.45, metallic=0.0, specular=0.4):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = specular
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = specular
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def assign(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def smooth(obj):
    for poly in obj.data.polygons:
        poly.use_smooth = True


def key(obj, frame, loc=None, rot=None, scale=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert("location", frame=frame)
    if rot is not None:
        obj.rotation_euler = rot
        obj.keyframe_insert("rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert("scale", frame=frame)


def ease_all(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    action = obj.animation_data.action
    # Blender 4+/5: action may use layers/slots; fall back to fcurves attr.
    fcurves = getattr(action, "fcurves", None)
    if fcurves is None:
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    for fc in strip.channelbag().fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = "BEZIER"
                            kp.easing = "EASE_IN_OUT"
            return
        except Exception:
            return
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"


# ---------------------------------------------------------------------------
# Lighting + camera
# ---------------------------------------------------------------------------

def setup_studio():
    # Soft editorial three-point + ground bounce (invisible floor for shadows optional)
    key = bpy.data.objects.new("LumenKey", bpy.data.lights.new("LumenKey", "AREA"))
    bpy.context.scene.collection.objects.link(key)
    key.data.energy = 250
    key.data.size = 3.5
    key.location = (2.4, -2.0, 3.2)
    key.rotation_euler = Euler((math.radians(55), 0, math.radians(35)), "XYZ")

    fill = bpy.data.objects.new("LumenFill", bpy.data.lights.new("LumenFill", "AREA"))
    bpy.context.scene.collection.objects.link(fill)
    fill.data.energy = 80
    fill.data.size = 4.0
    fill.data.color = (0.85, 0.9, 1.0)
    fill.location = (-2.8, -1.2, 2.0)

    rim = bpy.data.objects.new("LumenRim", bpy.data.lights.new("LumenRim", "AREA"))
    bpy.context.scene.collection.objects.link(rim)
    rim.data.energy = 120
    rim.data.size = 2.0
    rim.data.color = (1.0, 0.92, 0.75)
    rim.location = (0.2, 2.6, 2.4)

    cam_data = bpy.data.cameras.new("LumenCam")
    cam_data.lens = 85
    cam = bpy.data.objects.new("LumenCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    # front_three_quarter — readable form, controlled, not spinning
    cam.location = (2.15, -3.35, 1.55)
    cam.rotation_euler = Euler((math.radians(68), 0, math.radians(28)), "XYZ")
    bpy.context.scene.camera = cam

    # World — dark neutral, no HDRI needed for product look
    world = bpy.data.worlds.new("LumenWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.02, 0.025, 1.0)
    bg.inputs[1].default_value = 0.15
    return cam


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------

def build_passport():
    root = bpy.data.objects.new("PassportRoot", None)
    bpy.context.scene.collection.objects.link(root)

    # Closed booklet silhouette (cover thickness dominates — no big white face panel).
    bpy.ops.mesh.primitive_cube_add(size=1)
    cover = bpy.context.active_object
    cover.name = "PassportCover"
    cover.scale = (1.0, 0.16, 1.42)
    bpy.ops.object.transform_apply(scale=True)
    bevel = cover.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.035
    bevel.segments = 5
    navy = make_material("PassportLeather", base=(0.06, 0.12, 0.2), roughness=0.68, metallic=0.02)
    assign(cover, navy)
    smooth(cover)
    cover.parent = root

    gold = make_material("PassportGold", base=(0.82, 0.64, 0.28), roughness=0.28, metallic=0.9)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.26, depth=0.04)
    seal = bpy.context.active_object
    seal.name = "PassportSeal"
    seal.location = (0, 0.095, 0.08)
    seal.rotation_euler = (math.radians(90), 0, 0)
    assign(seal, gold)
    seal.parent = cover
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.02, major_segments=48)
    ring = bpy.context.active_object
    ring.name = "PassportRing"
    ring.location = (0, 0.1, 0.08)
    ring.rotation_euler = (math.radians(90), 0, 0)
    assign(ring, gold)
    ring.parent = cover
    bpy.ops.mesh.primitive_cube_add(size=1)
    spine = bpy.context.active_object
    spine.name = "PassportSpine"
    spine.scale = (0.05, 0.17, 1.42)
    spine.location = (-0.5, 0, 0)
    bpy.ops.object.transform_apply(scale=True)
    assign(spine, gold)
    spine.parent = cover

    # Thin page block peeking at fore-edge only
    bpy.ops.mesh.primitive_cube_add(size=1)
    pages = bpy.context.active_object
    pages.name = "PassportPages"
    pages.scale = (0.92, 0.1, 1.3)
    pages.location = (0.03, -0.02, 0)
    bpy.ops.object.transform_apply(scale=True)
    paper = make_material("PassportPaper", base=(0.9, 0.88, 0.82), roughness=0.82, metallic=0.0)
    assign(pages, paper)
    pages.parent = root

    root.location = (0, 0, 0.1)
    root.rotation_euler = Euler((math.radians(8), 0, math.radians(-18)), "XYZ")
    return root, {"cover": cover, "pages": pages, "seal": seal}


def build_suitcase():
    root = bpy.data.objects.new("SuitcaseRoot", None)
    bpy.context.scene.collection.objects.link(root)

    # Hard-shell upright spinner: taller body, clear top handle, corner wheels.
    bpy.ops.mesh.primitive_cube_add(size=1)
    body = bpy.context.active_object
    body.name = "SuitcaseBody"
    body.scale = (0.95, 0.48, 1.55)
    bpy.ops.object.transform_apply(scale=True)
    bevel = body.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.06
    bevel.segments = 6
    shell = make_material("SuitShell", base=(0.12, 0.36, 0.34), roughness=0.42, metallic=0.12)
    assign(body, shell)
    smooth(body)
    body.parent = root

    metal = make_material("SuitMetal", base=(0.82, 0.82, 0.84), roughness=0.2, metallic=0.95)
    # Top telescoping handle posts + grip
    for i, x in enumerate((-0.18, 0.18)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.55)
        post = bpy.context.active_object
        post.name = f"HandlePost{i}"
        post.location = (x, 0, 1.05)
        assign(post, metal)
        post.parent = root
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.45)
    grip = bpy.context.active_object
    grip.name = "SuitHandle"
    grip.location = (0, 0, 1.32)
    grip.rotation_euler = (0, math.radians(90), 0)
    assign(grip, metal)
    grip.parent = root
    # Side carry handle
    bpy.ops.mesh.primitive_torus_add(major_radius=0.18, minor_radius=0.03)
    side_h = bpy.context.active_object
    side_h.name = "SideHandle"
    side_h.location = (0.55, 0, 0.2)
    side_h.rotation_euler = (math.radians(90), 0, math.radians(90))
    assign(side_h, metal)
    side_h.parent = root
    for i, x in enumerate((-0.28, 0.28)):
        bpy.ops.mesh.primitive_cube_add(size=1)
        latch = bpy.context.active_object
        latch.name = f"Latch{i}"
        latch.scale = (0.1, 0.07, 0.07)
        latch.location = (x, -0.26, 0.35)
        bpy.ops.object.transform_apply(scale=True)
        assign(latch, metal)
        latch.parent = root
    for i, (x, y) in enumerate(((-0.28, 0.18), (0.28, 0.18), (-0.28, -0.18), (0.28, -0.18))):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.1)
        wheel = bpy.context.active_object
        wheel.name = f"Wheel{i}"
        wheel.location = (x, y, -0.85)
        wheel.rotation_euler = (math.radians(90), 0, 0)
        assign(wheel, metal)
        wheel.parent = root

    root.location = (0, 0, 0.25)
    root.rotation_euler = Euler((math.radians(6), 0, math.radians(22)), "XYZ")
    return root, {"body": body, "handle": grip}


def build_globe():
    root = bpy.data.objects.new("GlobeRoot", None)
    bpy.context.scene.collection.objects.link(root)

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.85, segments=48, ring_count=24)
    sphere = bpy.context.active_object
    sphere.name = "GlobeSphere"
    navy = make_material("GlobeOcean", base=(0.1, 0.18, 0.32), roughness=0.35, metallic=0.2)
    assign(sphere, navy)
    smooth(sphere)
    sphere.parent = root

    # Meridians / equator — restrained gold wire
    gold = make_material("GlobeGold", base=(0.78, 0.62, 0.28), roughness=0.3, metallic=0.9)
    for i in range(6):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.86, minor_radius=0.008, major_segments=64)
        ring = bpy.context.active_object
        ring.name = f"Meridian{i}"
        ring.rotation_euler = (0, math.radians(i * 30), 0)
        assign(ring, gold)
        ring.parent = root
    bpy.ops.mesh.primitive_torus_add(major_radius=0.86, minor_radius=0.01, major_segments=64)
    eq = bpy.context.active_object
    eq.name = "Equator"
    eq.rotation_euler = (math.radians(90), 0, 0)
    assign(eq, gold)
    eq.parent = root

    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.35)
    stand = bpy.context.active_object
    stand.name = "GlobeStand"
    stand.location = (0, 0, -1.05)
    wood = make_material("GlobeStand", base=(0.25, 0.18, 0.12), roughness=0.6, metallic=0.0)
    assign(stand, wood)
    stand.parent = root

    root.location = (0, 0, 0.25)
    return root, {"sphere": sphere}


def build_folder():
    root = bpy.data.objects.new("FolderRoot", None)
    bpy.context.scene.collection.objects.link(root)

    paper = make_material("FolderPaper", base=(0.86, 0.74, 0.5), roughness=0.7, metallic=0.0)
    navy = make_material("FolderAccent", base=(0.12, 0.2, 0.34), roughness=0.5, metallic=0.05)

    bpy.ops.mesh.primitive_cube_add(size=1)
    back = bpy.context.active_object
    back.name = "FolderBack"
    back.scale = (1.2, 0.03, 0.95)
    bpy.ops.object.transform_apply(scale=True)
    assign(back, paper)
    back.parent = root

    bpy.ops.mesh.primitive_cube_add(size=1)
    front = bpy.context.active_object
    front.name = "FolderFront"
    front.scale = (1.2, 0.03, 0.95)
    bpy.ops.object.transform_apply(scale=True)
    front.location = (0, 0.04, 0)
    assign(front, paper)
    front.parent = root

    bpy.ops.mesh.primitive_cube_add(size=1)
    tab = bpy.context.active_object
    tab.name = "FolderTab"
    tab.scale = (0.35, 0.035, 0.18)
    tab.location = (-0.35, 0.05, 0.55)
    bpy.ops.object.transform_apply(scale=True)
    assign(tab, navy)
    tab.parent = front

    # Inner sheets
    sheets = []
    for i in range(3):
        bpy.ops.mesh.primitive_cube_add(size=1)
        sh = bpy.context.active_object
        sh.name = f"Sheet{i}"
        sh.scale = (1.05, 0.01, 0.85)
        sh.location = (0, 0.02 + i * 0.015, 0.02)
        bpy.ops.object.transform_apply(scale=True)
        white = make_material(f"SheetMat{i}", base=(0.95, 0.94, 0.9), roughness=0.8, metallic=0.0)
        assign(sh, white)
        sh.parent = root
        sheets.append(sh)

    root.location = (0, 0, 0.1)
    return root, {"front": front, "back": back, "sheets": sheets}


def build_building():
    root = bpy.data.objects.new("BuildingRoot", None)
    bpy.context.scene.collection.objects.link(root)

    concrete = make_material("Concrete", base=(0.55, 0.52, 0.48), roughness=0.65, metallic=0.0)
    glass = make_material("GlassTint", base=(0.35, 0.5, 0.55), roughness=0.15, metallic=0.35)
    accent = make_material("BuildGold", base=(0.7, 0.55, 0.25), roughness=0.4, metallic=0.7)

    bpy.ops.mesh.primitive_cube_add(size=1)
    tower = bpy.context.active_object
    tower.name = "Tower"
    tower.scale = (1.0, 0.85, 2.2)
    tower.location = (0, 0, 0.3)
    bpy.ops.object.transform_apply(location=True, scale=True)
    assign(tower, concrete)
    smooth(tower)
    tower.parent = root

    # Window grid (front face)
    for row in range(5):
        for col in range(3):
            bpy.ops.mesh.primitive_cube_add(size=1)
            win = bpy.context.active_object
            win.name = f"Win{row}_{col}"
            win.scale = (0.18, 0.02, 0.22)
            win.location = (-0.35 + col * 0.35, -0.44, -0.5 + row * 0.4)
            bpy.ops.object.transform_apply(scale=True)
            assign(win, glass)
            win.parent = root

    bpy.ops.mesh.primitive_cube_add(size=1)
    base = bpy.context.active_object
    base.name = "Podium"
    base.scale = (1.25, 1.05, 0.2)
    base.location = (0, 0, -1.0)
    bpy.ops.object.transform_apply(location=True, scale=True)
    assign(base, accent)
    base.parent = root

    root.location = (0, 0, 0.2)
    return root, {"tower": tower}


BUILDERS = {
    "l3d_generic_passport": build_passport,
    "l3d_premium_suitcase": build_suitcase,
    "l3d_global_mobility_globe": build_globe,
    "l3d_document_folder": build_folder,
    "l3d_apartment_building": build_building,
}


# ---------------------------------------------------------------------------
# Motions
# ---------------------------------------------------------------------------

def apply_motion(motion: str, root, parts: dict, cam, frames: int):
    mid = frames // 2
    hold = int(frames * 0.72)
    end = frames

    if motion == "reveal":
        key(root, 1, loc=root.location + Vector((0, 0, -0.4)), scale=(0.15, 0.15, 0.15))
        key(root, 20, loc=root.location.copy(), scale=(1, 1, 1))
        key(root, hold, loc=root.location.copy(), scale=(1, 1, 1))
        key(root, end, loc=root.location + Vector((0.15, 0, 0.1)), scale=(0.92, 0.92, 0.92))
    elif motion == "open":
        key(root, 1, scale=(0.85, 0.85, 0.85))
        key(root, 12, scale=(1, 1, 1))
        cover = parts.get("cover") or parts.get("front")
        if cover:
            key(cover, 1, rot=Euler((0, 0, 0), "XYZ"))
            key(cover, 28, rot=Euler((math.radians(-105 if "cover" in parts else -55), 0, 0), "XYZ"))
            key(cover, hold, rot=cover.rotation_euler.copy())
            key(cover, end, rot=Euler((math.radians(-90 if "cover" in parts else -40), 0, 0), "XYZ"))
        sheets = parts.get("sheets") or []
        for i, sh in enumerate(sheets):
            key(sh, 16, loc=sh.location.copy())
            key(sh, 36, loc=sh.location + Vector((0.05 * (i + 1), 0.08 + i * 0.04, 0.05)))
            key(sh, end, loc=sh.location + Vector((0.05 * (i + 1), 0.08 + i * 0.04, 0.05)))
        key(root, hold, scale=(1, 1, 1))
        key(root, end, scale=(0.95, 0.95, 0.95))
    elif motion == "rotate_subtle":
        key(root, 1, rot=Euler((0, math.radians(-18), math.radians(-12)), "XYZ"), scale=(0.2, 0.2, 0.2))
        key(root, 18, rot=Euler((0, 0, 0), "XYZ"), scale=(1, 1, 1))
        key(root, hold, rot=Euler((0, math.radians(12), math.radians(8)), "XYZ"), scale=(1, 1, 1))
        key(root, end, rot=Euler((0, math.radians(18), math.radians(10)), "XYZ"), scale=(0.96, 0.96, 0.96))
    elif motion == "slide_in":
        # Keep object in-frame for alpha QA (avoid full exit at mid sample).
        key(root, 1, loc=root.location + Vector((-0.85, 0, 0)), scale=(0.92, 0.92, 0.92))
        key(root, 22, loc=root.location.copy(), scale=(1, 1, 1))
        key(root, hold, loc=root.location.copy())
        key(root, end, loc=root.location + Vector((0.12, 0, 0.04)), scale=(0.96, 0.96, 0.96))
    elif motion == "scale_reveal":
        key(root, 1, scale=(0.05, 0.05, 0.05))
        key(root, 24, scale=(1.05, 1.05, 1.05))
        key(root, 32, scale=(1, 1, 1))
        key(root, hold, scale=(1, 1, 1))
        key(root, end, scale=(0.9, 0.9, 0.9))
    elif motion == "floating_hold":
        base = root.location.copy()
        key(root, 1, loc=base + Vector((0, 0, -0.25)), scale=(0.3, 0.3, 0.3))
        key(root, 16, loc=base, scale=(1, 1, 1))
        key(root, mid, loc=base + Vector((0, 0, 0.08)), rot=Euler((0, math.radians(6), 0), "XYZ"))
        key(root, hold, loc=base + Vector((0, 0, 0.02)), rot=Euler((0, math.radians(-4), 0), "XYZ"))
        key(root, end, loc=base + Vector((0.1, 0, 0.05)), scale=(0.93, 0.93, 0.93))
    elif motion == "light_reveal":
        key(root, 1, scale=(0.4, 0.4, 0.4), rot=Euler((0, math.radians(-30), 0), "XYZ"))
        key(root, 24, scale=(1, 1, 1), rot=Euler((0, 0, 0), "XYZ"))
        key(root, hold, rot=Euler((0, math.radians(20), 0), "XYZ"))
        key(root, end, rot=Euler((0, math.radians(28), 0), "XYZ"), scale=(0.95, 0.95, 0.95))
        # Dim→bright key light
        key_light = bpy.data.objects.get("LumenKey")
        if key_light:
            key_light.data.energy = 40
            key_light.keyframe_insert("data.energy" if False else "location", frame=1)  # placeholder
            key_light.data.energy = 40
            # Energy keyframes via data path
            key_light.data.energy = 40
            key_light.data.keyframe_insert("energy", frame=1)
            key_light.data.energy = 280
            key_light.data.keyframe_insert("energy", frame=28)
            key_light.data.energy = 220
            key_light.data.keyframe_insert("energy", frame=end)
    elif motion == "camera_push":
        key(root, 1, scale=(0.85, 0.85, 0.85))
        key(root, 20, scale=(1, 1, 1))
        key(root, hold, scale=(1, 1, 1))
        key(root, end, scale=(1.02, 1.02, 1.02))
        cam_start = cam.location.copy()
        key(cam, 1, loc=cam_start + Vector((0, -0.8, 0.15)))
        key(cam, 28, loc=cam_start)
        key(cam, hold, loc=cam_start + Vector((0, 0.15, -0.05)))
        key(cam, end, loc=cam_start + Vector((0, 0.35, -0.08)))
    elif motion == "depth_entrance":
        key(root, 1, loc=root.location + Vector((0, 1.5, -0.3)), scale=(0.6, 0.6, 0.6))
        key(root, 26, loc=root.location.copy(), scale=(1, 1, 1))
        key(root, hold, loc=root.location.copy())
        key(root, end, loc=root.location + Vector((0.1, -0.1, 0.05)), scale=(0.96, 0.96, 0.96))
    else:
        # Fallback reveal
        apply_motion("reveal", root, parts, cam, frames)
        return

    ease_all(root)
    for p in parts.values():
        if isinstance(p, list):
            for item in p:
                ease_all(item)
        elif p is not None:
            ease_all(p)
    ease_all(cam)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_glb(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=False,
        export_animations=True,
        export_apply=False,
    )


def save_blend(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def main():
    args = parse_args()
    out = Path(args.out).resolve()
    asset = args.asset
    motion = args.motion
    if asset not in BUILDERS:
        raise SystemExit(f"unknown asset: {asset}")

    reset_scene()
    scene = bpy.context.scene
    png_dir = out / "alpha_png" / asset / motion
    png_dir.mkdir(parents=True, exist_ok=True)
    # clear old frames
    for old in png_dir.glob("frame_*.png"):
        old.unlink()

    set_render(scene, frames=args.frames, fps=args.fps, size=args.size, out_png_dir=png_dir)
    cam = setup_studio()
    root, parts = BUILDERS[asset]()
    apply_motion(motion, root, parts, cam, args.frames)

    blend_path = out / "blender" / f"{asset}_{motion}.blend"
    glb_path = out / "models" / f"{asset}_{motion}.glb"
    save_blend(blend_path)
    export_glb(glb_path)

    if not args.skip_render:
        bpy.ops.render.render(animation=True)

    meta = {
        "assetId": asset,
        "motion": motion,
        "frames": args.frames,
        "fps": args.fps,
        "resolution": [args.size, args.size],
        "blend": str(blend_path.relative_to(out)) if blend_path.is_relative_to(out) else str(blend_path),
        "glb": str(glb_path.relative_to(out)) if glb_path.is_relative_to(out) else str(glb_path),
        "pngDir": str(png_dir.relative_to(out)) if png_dir.is_relative_to(out) else str(png_dir),
        "engine": scene.render.engine,
        "filmTransparent": True,
    }
    meta_path = out / "metadata" / f"{asset}_{motion}.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print("FACTORY_OK", json.dumps(meta))


if __name__ == "__main__":
    main()
