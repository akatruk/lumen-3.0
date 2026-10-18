import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { CATALOG, lookupScene } from "./catalog";
import { normalizeScene, validateScene } from "./validateScene";
import { DEFERRED_SCENE_IDS, RENDERABLE_SCENE_IDS, SCENE_IDS, VARIANTS } from "../types/scene";

const hook = {
  type: "kinetic_hook",
  variant: "word_pop",
  text: "Planning a relocation?",
};

describe("scene schema and registry", () => {
  it("lists every registry id and marks implemented scenes", () => {
    assert.deepEqual(
      CATALOG.map((entry) => entry.id),
      [...SCENE_IDS],
    );
    assert.equal(CATALOG.length, 15);
    assert.deepEqual(
      CATALOG.filter((entry) => entry.implemented).map((entry) => entry.id),
      [...RENDERABLE_SCENE_IDS],
    );
    assert.equal(lookupScene("animated_diagram")?.implemented, true);
    for (const id of DEFERRED_SCENE_IDS) {
      assert.equal(lookupScene(id)?.implemented, false);
      assert.ok((VARIANTS[id] as readonly string[]).length > 0);
    }
    assert.equal(lookupScene("kinetic_hook")?.implemented, true);
    assert.equal(lookupScene("not_a_scene"), undefined);
  });

  it("rejects unknown ids and later-phase ids", () => {
    const unknown = validateScene({ type: "lower_third", text: "Planning a relocation?" });
    assert.equal(unknown.ok, false);
    if (!unknown.ok) assert.match(unknown.errors.join(" "), /Unknown scene id/);

    const diagram = validateScene({ type: "animated_diagram", variant: "growth", title: "Growth path" });
    assert.equal(diagram.ok, true);
    assert.throws(() => normalizeScene({ type: "quote", variant: "editorial", text: "Planning a relocation?" }));
  });

  it("rejects director control of position, css, type size, and color", () => {
    const result = validateScene({
      ...hook,
      x: 12,
      y: 40,
      fontSize: 80,
      color: "#fff",
      style: { transform: "rotate(8deg)" },
      css: "font-size:80px",
    });
    assert.equal(result.ok, false);
    if (!result.ok) {
      const message = result.errors.join(" ");
      for (const key of ["x", "y", "fontSize", "color", "style", "css"]) {
        assert.match(message, new RegExp(key));
      }
    }
  });

  it("rejects a partial word in emphasis and a bad variant", () => {
    const partial = validateScene({ ...hook, emphasis: ["Plannin"] });
    assert.equal(partial.ok, false);
    const spin = validateScene({ ...hook, variant: "spin" });
    assert.equal(spin.ok, false);
    const whole = validateScene({ ...hook, emphasis: ["relocation"] });
    assert.equal(whole.ok, true);
    if (whole.ok && whole.scene.type === "kinetic_hook") {
      assert.deepEqual(whole.scene.emphasis, ["relocation"]);
    }
  });

  it("normalizes duration from seconds and keeps explicit frames", () => {
    const seconds = normalizeScene({
      type: "big_number",
      variant: "count_up",
      value: 3,
      label: "steps to get started",
      durationSeconds: 2,
    });
    assert.equal(seconds.durationInFrames, 60);

    const frames = normalizeScene({ ...hook, durationInFrames: 40, durationSeconds: 2 });
    assert.equal(frames.durationInFrames, 40);

    const fallback = normalizeScene(hook);
    assert.equal(fallback.durationInFrames, 90);
  });

  it("rejects a non-numeric figure, empty steps, and broken timed words", () => {
    const figure = validateScene({
      type: "big_number",
      variant: "impact",
      value: "3",
      label: "steps to get started",
    });
    assert.equal(figure.ok, false);

    const steps = validateScene({
      type: "progress_steps",
      variant: "horizontal",
      title: "3 steps to get started",
      steps: [],
    });
    assert.equal(steps.ok, false);

    const words = validateScene({
      type: "broll_caption",
      variant: "bottom_caption",
      text: "Planning a relocation?",
      words: [
        { text: "Plannin", startFrame: 0, endFrame: 10 },
        { text: "g", startFrame: 10, endFrame: 20 },
      ],
    });
    assert.equal(words.ok, false);
  });

  it("times whole words across the scene", () => {
    const scene = normalizeScene({
      type: "broll_caption",
      variant: "minimal",
      text: "Consultation to filing",
      durationInFrames: 90,
    });
    assert.equal(scene.type, "broll_caption");
    if (scene.type !== "broll_caption") return;
    assert.deepEqual(
      scene.words.map((word) => word.text),
      ["Consultation", "to", "filing"],
    );
    assert.equal(scene.words.at(-1)?.endFrame, 90);
    assert.equal(scene.captionVariant, "clean");
    assert.deepEqual(scene.media, { kind: "placeholder", role: "broll" });
  });

  it("does not render deferred scenes from the registry", () => {
    const source = readFileSync(new URL("./motionRegistry.tsx", import.meta.url), "utf8");
    for (const name of ["KineticHook", "BigNumber", "ProgressSteps", "SpeakerFocus", "BrollCaption"]) {
      assert.equal(source.includes(name), true, name);
    }
    for (const id of DEFERRED_SCENE_IDS) {
      assert.equal(source.includes(`case "${id}"`), false, id);
    }
  });
});
