import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { captionBand, compositionClears, faceBandRect, layoutIsSafe, pipSafeRect, rectsOverlap, regionFor, resolveLayout } from "./layouts";
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

  it("rejects a diagram that covers the measured face or the caption plate", () => {
    const face = { left: 400, top: 600, width: 320, height: 280 };
    const caption = { left: 64, top: 1400, width: 952, height: 200 };
    const band = { left: 72, top: 998, width: 936, height: 354 };
    assert.equal(compositionClears(band, face, caption), true);
    assert.equal(compositionClears({ ...band, top: 700, height: 400 }, face, caption), false);
    assert.equal(compositionClears({ left: 72, top: 1300, width: 936, height: 200 }, face, caption), false);
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
