import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { captionBand, faceBandRect, layoutIsSafe, pipSafeRect, rectsOverlap, regionFor, resolveLayout } from "./layouts";
import { galleryShot, galleryShots } from "./galleryScript";

describe("semantic motion layout safety", () => {
  it("keeps overlay off the face band and the caption band", () => {
    const rect = regionFor("overlay");
    assert.equal(layoutIsSafe("overlay"), true);
    assert.equal(rectsOverlap(rect, faceBandRect()), false);
    assert.equal(rectsOverlap(rect, captionBand()), false);
  });

  it("keeps full-frame graphics off the speaker PIP and captions", () => {
    const rect = regionFor("full_frame");
    assert.equal(layoutIsSafe("full_frame"), true);
    assert.equal(rectsOverlap(rect, pipSafeRect()), false);
    assert.equal(rectsOverlap(rect, captionBand()), false);
  });

  it("keeps speaker-visual graphics out of the speaker column", () => {
    assert.equal(layoutIsSafe("speaker_visual", "left"), true);
    assert.equal(layoutIsSafe("speaker_visual", "right"), true);
  });

  it("falls back when a layout would be unsafe", () => {
    const resolved = resolveLayout("overlay", "left");
    assert.equal(resolved.layout, "overlay");
    assert.equal(resolved.fallback, false);
    assert.ok(resolved.rect.height > 200);
  });
});

describe("gallery covers 15 variants in three locales", () => {
  it("builds 5 components × 3 layouts", () => {
    for (const locale of ["en-US", "ru-RU", "zh-CN"] as const) {
      const shots = galleryShots(locale);
      assert.equal(shots.length, 15);
      assert.equal(new Set(shots.map((s) => s.componentId)).size, 5);
      assert.equal(new Set(shots.map((s) => s.layout)).size, 3);
    }
  });

  it("ownership preview states 49% and does not invent 51%", () => {
    const shot = galleryShot("ownership_split", "overlay", "en-US");
    assert.deepEqual(
      (shot.values || []).map((v) => v.value),
      [49],
    );
    assert.equal(shot.values?.[0]?.qualifier, "at_most");
  });
});
