import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CAPTION_VARIANTS, RENDERABLE_SCENE_IDS, VARIANTS, type Scene } from "../types/scene";
import { SHOWCASE_DURATION, SHOWCASE_SCENES, sampleFrames } from "./script";

const ALLOWED = new Set([
  "Planning a relocation?",
  "Planning a relocation",
  "Consultation to filing",
  "Goal, family, and budget",
  "International relocation consultation",
  "3 steps to get started",
  "Set your goals and budget",
  "Consultation",
  "Document preparation",
  "Filing",
  "Ready to make your move?",
  "steps to get started",
  "relocation",
  "family",
  "Start",
  "Before",
  "After",
]);

function texts(scene: Scene): string[] {
  switch (scene.type) {
    case "kinetic_hook":
      return [scene.text, ...(scene.emphasis ?? [])];
    case "big_number":
      return [scene.label];
    case "progress_steps":
      return [scene.title ?? "", ...scene.steps.map((step) => step.label)].filter((value) => value.length > 0);
    case "speaker_focus":
      return scene.caption ? [scene.caption] : [];
    case "broll_caption":
      return [scene.text];
    case "timeline":
      return scene.events.flatMap((event) => (event.date ? [event.date, event.label] : [event.label]));
    case "comparison":
      return [scene.left.label, scene.left.detail ?? "", scene.right.label, scene.right.detail ?? ""].filter((value) => value.length > 0);
    case "split_screen":
      return [scene.text];
    case "checklist":
      return scene.items.map((item) => item.label);
    case "stat_reveal":
      return [scene.headline, scene.context ?? ""].filter((value) => value.length > 0);
    case "animated_diagram":
      return [
        scene.title ?? "",
        ...(scene.labels ?? []),
        ...(scene.nodes?.map((node) => node.label) ?? []),
        scene.leftLabel ?? "",
        scene.rightLabel ?? "",
      ].filter((value) => value.length > 0);
    default:
      return [];
  }
}

describe("showcase script", () => {
  it("covers every implemented scene and variant with the demo copy", () => {
    for (const id of RENDERABLE_SCENE_IDS) {
      for (const variant of VARIANTS[id]) {
        assert.equal(
          SHOWCASE_SCENES.some((scene) => scene.type === id && scene.variant === variant),
          true,
          `${id}/${variant}`,
        );
      }
    }
    for (const variant of CAPTION_VARIANTS) {
      assert.equal(
        SHOWCASE_SCENES.some((scene) => scene.type === "broll_caption" && scene.captionVariant === variant),
        true,
        variant,
      );
    }
    for (const scene of SHOWCASE_SCENES) {
      if (scene.type === "big_number") assert.equal(scene.value, 3);
      for (const text of texts(scene)) assert.equal(ALLOWED.has(text), true, text);
    }
    const blob = JSON.stringify(SHOWCASE_SCENES).toLowerCase();
    assert.equal(blob.includes("lorem"), false);
    assert.equal(blob.includes("ipsum"), false);
  });

  it("places sample frames inside the rendered duration", () => {
    assert.equal(SHOWCASE_DURATION, SHOWCASE_SCENES.length * 90);
    const samples = sampleFrames();
    for (const sample of Object.values(samples)) {
      assert.ok(sample.frame >= 0 && sample.frame < SHOWCASE_DURATION, sample.id);
    }
    assert.equal(samples.kineticHook.frame, 72);
    assert.equal(samples.bigNumber.frame, 4 * 90 + 72);
    assert.equal(samples.caption.frame, 16 * 90 + 72);
  });
});
