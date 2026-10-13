"""Lumen Premium 3D Factory V2 — hinged geometry, PBR materials, tight framing.

  blender -b --python media/library/3d_factory/blender_factory_v2.py -- \
    --asset l3d_v2_passport --motion passport_open --out 3d-library-v2
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector, Matrix


def _argv():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--asset", required=True)
    p.add_argument("--motion", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--frames", type=int, default=120)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--skip-render", action="store_true")
    p.add_argument("--engine", default="EEVEE", choices=("EEVEE", "CYCLES"))
    return p.parse_args(_argv())


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def make_pbr(name, *, base, roughness=0.45, metallic=0.0, specular=0.5, noise=0.0, noise_scale=12.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    out.location = (450, 0)
    if noise > 0.001:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = noise_scale
        tex.inputs["Detail"].default_value = 8.0
        tex.location = (-400, 0)
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (-180, 0)
        ramp.color_ramp.elements[0].position = 0.35
        ramp.color_ramp.elements[0].color = (*[max(0, c * 0.85) for c in base], 1)
        ramp.color_ramp.elements[1].position = 0.7
        ramp.color_ramp.elements[1].color = (*[min(1, c * 1.12) for c in base], 1)
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.15 * noise
        bump.inputs["Distance"].default_value = 0.02
        bump.location = (-180, -220)
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = roughness
    else:
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


def bevel(obj, width=0.02, segments=4):
    m = obj.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    return m


def apply_mods(obj):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for mod in list(obj.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        except Exception:
            pass
    obj.select_set(False)


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
    fcurves = getattr(action, "fcurves", None)
    curves = []
    if fcurves is not None:
        curves = list(fcurves)
    else:
        try:
            for layer in action.layers:
                for strip in layer.strips:
                    curves.extend(list(strip.channelbag().fcurves))
        except Exception:
            return
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"


def cube(name, scale, loc=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    o.location = loc
    if parent:
        o.parent = parent
    return o


def cyl(name, radius, depth, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth)
    o = bpy.context.active_object
    o.name = name
    o.location = loc
    o.rotation_euler = Euler(rot, "XYZ")
    if parent:
        o.parent = parent
    return o


def setup_studio(width, height):
    key_l = bpy.data.objects.new("LumenKey", bpy.data.lights.new("LumenKey", "AREA"))
    bpy.context.scene.collection.objects.link(key_l)
    key_l.data.energy = 420
    key_l.data.size = 4.0
    key_l.data.color = (1.0, 0.97, 0.92)
    key_l.location = (2.6, -2.4, 3.6)
    key_l.rotation_euler = Euler((math.radians(52), 0, math.radians(38)), "XYZ")

    fill = bpy.data.objects.new("LumenFill", bpy.data.lights.new("LumenFill", "AREA"))
    bpy.context.scene.collection.objects.link(fill)
    fill.data.energy = 110
    fill.data.size = 5.0
    fill.data.color = (0.82, 0.88, 1.0)
    fill.location = (-3.0, -1.4, 2.2)

    rim = bpy.data.objects.new("LumenRim", bpy.data.lights.new("LumenRim", "AREA"))
    bpy.context.scene.collection.objects.link(rim)
    rim.data.energy = 160
    rim.data.size = 2.5
    rim.data.color = (1.0, 0.9, 0.78)
    rim.location = (-0.2, 3.0, 2.8)

    # Soft bounce
    bounce = bpy.data.objects.new("LumenBounce", bpy.data.lights.new("LumenBounce", "AREA"))
    bpy.context.scene.collection.objects.link(bounce)
    bounce.data.energy = 40
    bounce.data.size = 6.0
    bounce.location = (0, -0.5, -1.2)
    bounce.rotation_euler = Euler((math.radians(-90), 0, 0), "XYZ")

    cam_data = bpy.data.cameras.new("LumenCam")
    cam_data.lens = 70
    cam_data.sensor_width = 36
    # Portrait-aware: slight telephoto for product hero
    cam = bpy.data.objects.new("LumenCam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = (2.4, -3.8, 1.65)
    cam.rotation_euler = Euler((math.radians(70), 0, math.radians(30)), "XYZ")
    bpy.context.scene.camera = cam

    world = bpy.data.worlds.new("LumenWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.015, 0.016, 0.02, 1.0)
    bg.inputs[1].default_value = 0.12

    # No ground plate in alpha masters — opaque floors destroy transparency and
    # inflate subject coverage. Contact shadow is handled in Remotion if needed.
    return cam, None


def frame_camera_on_objects(cam, objects, margin=1.55):
    """Pull camera so combined bbox fills ~45–60% of the portrait frame."""
    coords = []
    for obj in objects:
        if obj.type != "MESH" or obj.name.startswith("Shadow"):
            continue
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            coords.append(world)
    if not coords:
        return
    mn = Vector((min(c.x for c in coords), min(c.y for c in coords), min(c.z for c in coords)))
    mx = Vector((max(c.x for c in coords), max(c.y for c in coords), max(c.z for c in coords)))
    center = (mn + mx) * 0.5
    # Bias slightly upward so top handles stay in frame
    center = Vector((center.x, center.y, center.z + (mx.z - mn.z) * 0.08))
    size = max((mx - mn).length, 0.5)
    direction = (cam.location - center).normalized()
    if direction.length < 0.01:
        direction = Vector((0.55, -0.85, 0.32)).normalized()
    dist = max(3.2, size * margin * 1.75)
    cam.location = center + direction * dist
    track = center - cam.location
    cam.rotation_euler = track.to_track_quat("-Z", "Y").to_euler()


def set_render(scene, *, frames, fps, width, height, out_png_dir: Path, engine: str):
    engines = {i.identifier for i in scene.render.bl_rna.properties["engine"].enum_items}
    if engine == "CYCLES" and "CYCLES" in engines:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 64
        scene.cycles.use_denoising = True
    else:
        scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "CYCLES"
        ee = scene.eevee
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = 96
        if hasattr(ee, "use_raytracing"):
            ee.use_raytracing = True
        if hasattr(ee, "use_shadows"):
            ee.use_shadows = True
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.filepath = str(out_png_dir / "frame_")
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_passport_v2(*, second=False, offset=(0, 0, 0), tint=None):
    """Hinged booklet: back cover fixed, front cover pivots on spine."""
    root = bpy.data.objects.new("PassportRoot" + ("B" if second else "A"), None)
    bpy.context.scene.collection.objects.link(root)
    root.location = offset

    leather_base = tint or (0.05, 0.10, 0.18)
    leather = make_pbr("Leather" + ("B" if second else "A"), base=leather_base, roughness=0.62, metallic=0.04, noise=0.55, noise_scale=28)
    paper = make_pbr("Paper" + ("B" if second else "A"), base=(0.92, 0.90, 0.84), roughness=0.78, metallic=0.0, noise=0.25, noise_scale=40)
    gold = make_pbr("Gold" + ("B" if second else "A"), base=(0.78, 0.62, 0.28), roughness=0.32, metallic=0.92, noise=0.15, noise_scale=20)

    # Back cover (hinge parent)
    hinge = bpy.data.objects.new("SpineHinge" + ("B" if second else "A"), None)
    bpy.context.scene.collection.objects.link(hinge)
    hinge.parent = root
    hinge.location = (-0.55, 0, 0)

    back = cube("BackCover", (1.05, 0.045, 1.48), loc=(0.55, 0.02, 0), parent=hinge)
    assign(back, leather)
    bevel(back, 0.028, 5)
    apply_mods(back)
    smooth(back)

    # Front cover — child of hinge empty so rotation opens booklet
    front_pivot = bpy.data.objects.new("FrontPivot" + ("B" if second else "A"), None)
    bpy.context.scene.collection.objects.link(front_pivot)
    front_pivot.parent = hinge
    front_pivot.location = (0, 0, 0)

    front = cube("FrontCover", (1.05, 0.045, 1.48), loc=(0.55, -0.03, 0), parent=front_pivot)
    assign(front, leather)
    bevel(front, 0.028, 5)
    apply_mods(front)
    smooth(front)

    # Abstract gold foil — geometric plate + ring, NOT government emblem / text
    foil = cube("FoilPlate", (0.42, 0.008, 0.42), loc=(0.55, -0.056, 0.12), parent=front_pivot)
    assign(foil, gold)
    bevel(foil, 0.012, 4)
    apply_mods(foil)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.018, major_segments=48)
    disc = bpy.context.active_object
    disc.name = "FoilRing"
    disc.location = (0.55, -0.062, 0.12)
    disc.rotation_euler = (math.radians(90), 0, 0)
    assign(disc, gold)
    disc.parent = front_pivot

    # Page stack between covers (thin, paper-like)
    pages = []
    for i in range(6):
        sh = cube(f"Page{i}", (0.96, 0.008, 1.36), loc=(0.52, -0.008 + i * 0.005, 0), parent=hinge)
        assign(sh, paper)
        bevel(sh, 0.003, 2)
        apply_mods(sh)
        pages.append(sh)

    # Thin fore-edge gilt (not a thick wood-like spine block)
    gilt = cube("GiltEdge", (0.012, 0.04, 1.36), loc=(1.06, 0, 0), parent=hinge)
    assign(gilt, gold)

    # Closed booklet rests slightly open toward camera for readable silhouette
    root.rotation_euler = Euler((math.radians(18), math.radians(-8), math.radians(-28)), "XYZ")
    return root, {
        "hinge": hinge,
        "front_pivot": front_pivot,
        "front": front,
        "back": back,
        "pages": pages,
        "foil": foil,
    }


def build_suitcase_v2():
    root = bpy.data.objects.new("SuitcaseRoot", None)
    bpy.context.scene.collection.objects.link(root)

    shell = make_pbr("Shell", base=(0.10, 0.32, 0.30), roughness=0.38, metallic=0.18, noise=0.4, noise_scale=18)
    metal = make_pbr("Metal", base=(0.78, 0.78, 0.80), roughness=0.22, metallic=0.95, noise=0.1, noise_scale=30)
    rubber = make_pbr("Rubber", base=(0.08, 0.08, 0.09), roughness=0.85, metallic=0.0, noise=0.2, noise_scale=22)
    zipper = make_pbr("Zip", base=(0.15, 0.15, 0.16), roughness=0.45, metallic=0.6)

    body = cube("Body", (1.05, 0.52, 1.55), loc=(0, 0, 0.15), parent=root)
    assign(body, shell)
    bevel(body, 0.07, 7)
    apply_mods(body)
    smooth(body)

    # Vertical zipper seam (front)
    zip_strip = cube("ZipStrip", (0.04, 0.02, 1.4), loc=(0, -0.27, 0.15), parent=root)
    assign(zip_strip, zipper)

    # Corner protectors
    for i, (x, y, z) in enumerate([
        (-0.48, -0.22, -0.55), (0.48, -0.22, -0.55),
        (-0.48, 0.22, -0.55), (0.48, 0.22, -0.55),
        (-0.48, -0.22, 0.85), (0.48, -0.22, 0.85),
    ]):
        cap = cube(f"Corner{i}", (0.12, 0.1, 0.12), loc=(x, y, z), parent=root)
        assign(cap, metal)
        bevel(cap, 0.02, 3)
        apply_mods(cap)

    # Telescoping handle (retracted → extended animated)
    handle_root = bpy.data.objects.new("HandleRoot", None)
    bpy.context.scene.collection.objects.link(handle_root)
    handle_root.parent = root
    handle_root.location = (0, 0, 0.92)
    for i, x in enumerate((-0.16, 0.16)):
        post = cyl(f"Post{i}", 0.028, 0.55, loc=(x, 0, 0.2), parent=handle_root)
        assign(post, metal)
        smooth(post)
    grip = cyl("Grip", 0.035, 0.4, loc=(0, 0, 0.48), rot=(0, math.radians(90), 0), parent=handle_root)
    assign(grip, metal)

    # Side carry handle
    side = bpy.ops.mesh.primitive_torus_add(major_radius=0.16, minor_radius=0.025, major_segments=32)
    side_h = bpy.context.active_object
    side_h.name = "SideHandle"
    side_h.location = (0.58, 0, 0.25)
    side_h.rotation_euler = (math.radians(90), 0, math.radians(90))
    assign(side_h, metal)
    side_h.parent = root

    # Latches
    for i, x in enumerate((-0.22, 0.22)):
        latch = cube(f"Latch{i}", (0.12, 0.06, 0.08), loc=(x, -0.28, 0.45), parent=root)
        assign(latch, metal)
        bevel(latch, 0.015, 3)
        apply_mods(latch)

    # Wheels with housings
    wheels = []
    for i, (x, y) in enumerate([(-0.32, 0.16), (0.32, 0.16), (-0.32, -0.16), (0.32, -0.16)]):
        house = cube(f"WheelHouse{i}", (0.14, 0.12, 0.12), loc=(x, y, -0.7), parent=root)
        assign(house, shell)
        bevel(house, 0.02, 3)
        apply_mods(house)
        wh = cyl(f"Wheel{i}", 0.09, 0.06, loc=(x, y, -0.78), rot=(math.radians(90), 0, 0), parent=root)
        assign(wh, rubber)
        smooth(wh)
        hub = cyl(f"Hub{i}", 0.03, 0.07, loc=(x, y, -0.78), rot=(math.radians(90), 0, 0), parent=root)
        assign(hub, metal)
        wheels.append(wh)

    root.location = (0, 0, 0.35)
    root.rotation_euler = Euler((math.radians(5), 0, math.radians(18)), "XYZ")
    return root, {"body": body, "handle_root": handle_root, "wheels": wheels, "grip": grip}


def build_folder_v2():
    root = bpy.data.objects.new("FolderRoot", None)
    bpy.context.scene.collection.objects.link(root)

    manila = make_pbr("Manila", base=(0.78, 0.64, 0.42), roughness=0.72, metallic=0.0, noise=0.45, noise_scale=35)
    navy = make_pbr("TabNavy", base=(0.10, 0.16, 0.28), roughness=0.55, metallic=0.05, noise=0.2, noise_scale=20)
    paper = make_pbr("DocPaper", base=(0.95, 0.94, 0.90), roughness=0.8, metallic=0.0, noise=0.2, noise_scale=50)

    # Back panel
    back = cube("FolderBack", (1.35, 0.028, 1.05), loc=(0, 0.04, 0), parent=root)
    assign(back, manila)
    bevel(back, 0.008, 3)
    apply_mods(back)

    # Front flap hinged at bottom edge
    hinge = bpy.data.objects.new("FolderHinge", None)
    bpy.context.scene.collection.objects.link(hinge)
    hinge.parent = root
    hinge.location = (0, 0.02, -0.52)

    front = cube("FolderFront", (1.35, 0.028, 1.0), loc=(0, 0, 0.5), parent=hinge)
    assign(front, manila)
    bevel(front, 0.008, 3)
    apply_mods(front)

    tab = cube("FolderTab", (0.38, 0.032, 0.2), loc=(-0.4, -0.02, 0.95), parent=hinge)
    assign(tab, navy)
    bevel(tab, 0.01, 3)
    apply_mods(tab)

    sheets = []
    for i in range(4):
        sh = cube(f"Doc{i}", (1.2, 0.01, 0.92), loc=(0.02 * i, 0.01 + i * 0.012, 0.02), parent=root)
        assign(sh, paper)
        bevel(sh, 0.003, 2)
        apply_mods(sh)
        sheets.append(sh)

    root.location = (0, 0, 0.15)
    root.rotation_euler = Euler((math.radians(18), 0, math.radians(-12)), "XYZ")
    return root, {"hinge": hinge, "front": front, "back": back, "sheets": sheets, "tab": tab}


# ---------------------------------------------------------------------------
# Motions
# ---------------------------------------------------------------------------

def apply_motion_v2(motion, roots_parts, cam, frames):
    """roots_parts: list of (root, parts) — usually one; two for second_passport."""
    hold = int(frames * 0.75)
    end = frames
    mid = frames // 2

    if motion == "passport_reveal":
        root, parts = roots_parts[0]
        key(root, 1, loc=root.location + Vector((0, 0, -0.35)), scale=(0.2, 0.2, 0.2), rot=Euler((math.radians(25), 0, math.radians(-40)), "XYZ"))
        key(root, 22, loc=root.location.copy(), scale=(1, 1, 1), rot=root.rotation_euler.copy())
        key(root, hold, loc=root.location.copy(), scale=(1, 1, 1))
        key(root, end, loc=root.location + Vector((0.08, 0, 0.05)), scale=(0.96, 0.96, 0.96))
        ease_all(root)

    elif motion == "passport_open":
        root, parts = roots_parts[0]
        pivot = parts["front_pivot"]
        key(root, 1, scale=(0.88, 0.88, 0.88), rot=root.rotation_euler.copy())
        key(root, 16, scale=(1, 1, 1))
        # Open around spine (local Z): cover swings like a book, not a laptop lid
        key(pivot, 1, rot=Euler((0, 0, 0), "XYZ"))
        key(pivot, 40, rot=Euler((0, 0, math.radians(158)), "XYZ"))
        key(pivot, hold, rot=Euler((0, 0, math.radians(158)), "XYZ"))
        key(pivot, end, rot=Euler((0, 0, math.radians(150)), "XYZ"))
        for i, pg in enumerate(parts.get("pages") or []):
            key(pg, 18, loc=pg.location.copy(), rot=Euler((0, 0, 0), "XYZ"))
            key(pg, 44, loc=pg.location + Vector((0.01 * i, -0.01, 0)), rot=Euler((0, 0, math.radians(8 + i * 6)), "XYZ"))
            key(pg, end, loc=pg.location + Vector((0.01 * i, -0.01, 0)), rot=Euler((0, 0, math.radians(8 + i * 6)), "XYZ"))
            ease_all(pg)
        key(root, hold, scale=(1, 1, 1))
        key(root, end, scale=(0.97, 0.97, 0.97))
        ease_all(root)
        ease_all(pivot)

    elif motion == "second_passport_reveal":
        # Two distinct passports arrive staggered
        for idx, (root, parts) in enumerate(roots_parts):
            delay = 1 + idx * 12
            start_x = -0.55 if idx == 0 else 0.55
            key(root, delay, loc=root.location + Vector((start_x, 0.4, -0.2)), scale=(0.15, 0.15, 0.15))
            key(root, delay + 24, loc=root.location.copy(), scale=(1, 1, 1))
            pivot = parts["front_pivot"]
            key(pivot, delay + 20, rot=Euler((0, 0, 0), "XYZ"))
            key(pivot, delay + 48, rot=Euler((math.radians(-40 - idx * 15), 0, 0), "XYZ"))
            key(root, hold, scale=(1, 1, 1))
            key(root, end, scale=(0.95, 0.95, 0.95))
            ease_all(root)
            ease_all(pivot)

    elif motion == "suitcase_arrival":
        root, parts = roots_parts[0]
        hr = parts["handle_root"]
        key(root, 1, loc=root.location + Vector((0, 1.2, 0.3)), scale=(0.85, 0.85, 0.85))
        key(root, 28, loc=root.location.copy(), scale=(1, 1, 1))
        key(hr, 1, scale=(1, 1, 0.35))
        key(hr, 32, scale=(1, 1, 1.0))
        key(root, hold, loc=root.location.copy())
        key(root, end, loc=root.location + Vector((0.05, -0.05, 0)), scale=(0.97, 0.97, 0.97))
        ease_all(root)
        ease_all(hr)

    elif motion == "suitcase_roll":
        root, parts = roots_parts[0]
        base = root.location.copy()
        key(root, 1, loc=base + Vector((-1.4, 0.2, 0)), rot=Euler((math.radians(5), 0, math.radians(35)), "XYZ"))
        key(root, 40, loc=base, rot=Euler((math.radians(5), 0, math.radians(18)), "XYZ"))
        key(root, hold, loc=base + Vector((0.05, 0, 0)))
        key(root, end, loc=base + Vector((0.15, -0.05, 0)))
        for i, wh in enumerate(parts.get("wheels") or []):
            key(wh, 1, rot=Euler((math.radians(90), 0, 0), "XYZ"))
            key(wh, 40, rot=Euler((math.radians(90), math.radians(720), 0), "XYZ"))
            key(wh, end, rot=Euler((math.radians(90), math.radians(900), 0), "XYZ"))
            ease_all(wh)
        ease_all(root)

    elif motion == "suitcase_foreground_pass":
        root, parts = roots_parts[0]
        base = root.location.copy()
        key(root, 1, loc=base + Vector((-2.0, -0.8, -0.1)), scale=(1.15, 1.15, 1.15))
        key(root, mid, loc=base + Vector((0, -0.3, 0.05)), scale=(1.2, 1.2, 1.2))
        key(root, end, loc=base + Vector((2.0, -0.8, -0.1)), scale=(1.1, 1.1, 1.1))
        ease_all(root)

    elif motion == "folder_reveal":
        root, parts = roots_parts[0]
        key(root, 1, loc=root.location + Vector((0, 0, -0.3)), scale=(0.2, 0.2, 0.2))
        key(root, 22, loc=root.location.copy(), scale=(1, 1, 1))
        key(root, hold, scale=(1, 1, 1))
        key(root, end, scale=(0.96, 0.96, 0.96))
        ease_all(root)

    elif motion == "folder_open":
        root, parts = roots_parts[0]
        hinge = parts["hinge"]
        key(root, 1, scale=(0.92, 0.92, 0.92))
        key(root, 12, scale=(1, 1, 1))
        key(hinge, 1, rot=Euler((0, 0, 0), "XYZ"))
        key(hinge, 34, rot=Euler((math.radians(-70), 0, 0), "XYZ"))
        key(hinge, hold, rot=Euler((math.radians(-70), 0, 0), "XYZ"))
        key(hinge, end, rot=Euler((math.radians(-62), 0, 0), "XYZ"))
        for i, sh in enumerate(parts.get("sheets") or []):
            key(sh, 18, loc=sh.location.copy())
            key(sh, 40, loc=sh.location + Vector((0.08 + i * 0.04, 0.06 + i * 0.03, 0.04 + i * 0.02)))
            key(sh, end, loc=sh.location + Vector((0.08 + i * 0.04, 0.06 + i * 0.03, 0.04 + i * 0.02)))
            ease_all(sh)
        ease_all(root)
        ease_all(hinge)

    elif motion == "documents_stack":
        root, parts = roots_parts[0]
        sheets = parts.get("sheets") or []
        key(root, 1, scale=(0.85, 0.85, 0.85))
        key(root, 16, scale=(1, 1, 1))
        for i, sh in enumerate(sheets):
            key(sh, 1, loc=sh.location + Vector((0, 0.4 + i * 0.05, 0.5)), rot=Euler((0, 0, math.radians(12 - i * 4)), "XYZ"))
            key(sh, 18 + i * 8, loc=sh.location.copy(), rot=Euler((0, 0, 0), "XYZ"))
            ease_all(sh)
        key(root, hold, scale=(1, 1, 1))
        key(root, end, scale=(0.97, 0.97, 0.97))
        ease_all(root)

    else:
        raise SystemExit(f"unknown motion: {motion}")


def mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name != "ShadowCatcher"]


def main():
    args = parse_args()
    out = Path(args.out)
    blend_dir = out / "blender"
    glb_dir = out / "models"
    png_dir = out / "alpha_png" / args.asset / args.motion
    meta_dir = out / "metadata"
    preview_dir = out / "previews"
    for d in (blend_dir, glb_dir, png_dir, meta_dir, preview_dir):
        d.mkdir(parents=True, exist_ok=True)

    reset_scene()
    cam, _ground = setup_studio(args.width, args.height)
    set_render(
        bpy.context.scene,
        frames=args.frames,
        fps=args.fps,
        width=args.width,
        height=args.height,
        out_png_dir=png_dir,
        engine=args.engine,
    )

    roots_parts = []
    if args.asset == "l3d_v2_passport":
        if args.motion == "second_passport_reveal":
            a = build_passport_v2(offset=(-0.55, 0, 0.1), tint=(0.05, 0.10, 0.18))
            b = build_passport_v2(second=True, offset=(0.55, 0.05, 0.05), tint=(0.12, 0.08, 0.06))
            roots_parts = [a, b]
        else:
            roots_parts = [build_passport_v2()]
    elif args.asset == "l3d_v2_suitcase":
        roots_parts = [build_suitcase_v2()]
    elif args.asset == "l3d_v2_folder":
        roots_parts = [build_folder_v2()]
    else:
        raise SystemExit(f"unknown asset: {args.asset}")

    apply_motion_v2(args.motion, roots_parts, cam, args.frames)
    frame_camera_on_objects(cam, mesh_objects(), margin=1.25)

    # Export blend + glb
    blend_path = blend_dir / f"{args.asset}_{args.motion}.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    glb_path = glb_dir / f"{args.asset}_{args.motion}.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", export_animations=True)

    if not args.skip_render:
        bpy.ops.render.render(animation=True)
        # Mid-frame preview
        mid = max(1, args.frames // 2)
        bpy.context.scene.frame_set(mid)
        prev = preview_dir / f"{args.asset}_{args.motion}.png"
        bpy.context.scene.render.filepath = str(prev)
        bpy.ops.render.render(write_still=True)

    meta = {
        "assetId": args.asset,
        "motion": args.motion,
        "frames": args.frames,
        "fps": args.fps,
        "resolution": [args.width, args.height],
        "blend": str(blend_path.relative_to(out)),
        "glb": str(glb_path.relative_to(out)),
        "pngDir": str(png_dir.relative_to(out)),
        "engine": bpy.context.scene.render.engine,
        "filmTransparent": True,
        "factory": "v2",
        "qualityStatus": "NEEDS_REWORK",
    }
    (meta_dir / f"{args.asset}_{args.motion}.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({"ok": True, **meta}))


if __name__ == "__main__":
    main()
