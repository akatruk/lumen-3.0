import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { formatMetric } from "./format";
import { galleryShotV15, galleryShotsV15 } from "./galleryV15";

describe("metric formatting", () => {
  it("groups currency for en, ru, and zh without inventing a code", () => {
    assert.match(formatMetric(120000, "currency", "en-US", "USD"), /120,000 USD/);
    assert.match(formatMetric(120000, "currency", "ru-RU", "USD"), /120[\s\u00a0\u202f]000 USD/);
    assert.match(formatMetric(120000, "currency", "zh-CN", "USD"), /120,000 USD/);
    assert.equal(formatMetric(49, "percent", "zh-CN"), "49%");
    assert.equal(formatMetric(49, "number", "en-US"), "49");
  });
});

describe("v15 gallery", () => {
  it("builds 10 components × 3 layouts in three locales", () => {
    for (const locale of ["en-US", "ru-RU", "zh-CN"] as const) {
      const shots = galleryShotsV15(locale);
      assert.equal(shots.length, 30);
      assert.equal(new Set(shots.map((shot) => shot.componentId)).size, 10);
      assert.equal(new Set(shots.map((shot) => shot.layout)).size, 3);
    }
  });

  it("keeps allocation values and chinese punctuation in the payload", () => {
    const alloc = galleryShotV15("capital_allocation", "overlay", "ru-RU");
    assert.deepEqual((alloc.segments || []).map((segment) => segment.value), [40, 35, 25]);
    assert.match(alloc.segments?.[0]?.label || "", /Операционная/);
    const docs = galleryShotV15("document_workflow", "full_frame", "zh-CN");
    const labels = (docs.steps || []).map((step) => (typeof step === "string" ? step : step.label));
    assert.ok(labels.some((label) => label.includes("、")));
    const change = galleryShotV15("before_after", "speaker_visual", "en-US");
    assert.equal(change.before, "Before investment");
    assert.equal(change.after, "After investment");
    assert.equal("benefit" in change, false);
  });
});
