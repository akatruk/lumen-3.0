import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { ThreeDecisionLayers } from "./ThreeDecisionLayers";
import {
  CAPTIONS,
  GOLD_CAPTION,
  GOLD_DURATION,
  GOLD_FACE,
  GOLD_FPS,
  GOLD_GRAPHIC,
  LAYER_AT,
  LAYER_COPY,
  captionAt,
  enterFrame,
  layerMotion,
  rectsOverlap,
  visibleLayerCount,
} from "./threeLayersModel";

describe("three decision layers", () => {
  it("renders one component", () => {
    assert.equal(typeof ThreeDecisionLayers, "function");
  });

  it("localizes the three spoken labels", () => {
    assert.deepEqual(LAYER_COPY["zh-CN"], ["使用场景", "家庭结构", "代价"]);
    assert.equal(LAYER_COPY["en-US"][1].length > 0, true);
    assert.equal(LAYER_COPY["ru-RU"][2].length > 0, true);
    assert.equal(LAYER_COPY["zh-CN"][0] === LAYER_COPY["en-US"][0], false);
  });

  it("keeps source evidence on the spoken timestamps", () => {
    assert.equal(captionAt(2.4), "第一层叫使用场景");
    assert.equal(captionAt(16.52), "第二层叫家庭结构");
    assert.equal(captionAt(30.44), "第三层叫代价");
    assert.deepEqual(LAYER_AT, [2.4, 16.52, 30.44]);
    assert.equal(CAPTIONS.some((row) => row.text.includes("49")), false);
  });

  it("keeps the graphic off the face and off the caption", () => {
    assert.equal(rectsOverlap(GOLD_GRAPHIC, GOLD_FACE), false);
    assert.equal(rectsOverlap(GOLD_GRAPHIC, GOLD_CAPTION), false);
    assert.equal(rectsOverlap(GOLD_CAPTION, GOLD_FACE), false);
  });

  it("reveals one layer at a time and is deterministic", () => {
    assert.equal(visibleLayerCount(enterFrame(2.4) - 1), 0);
    assert.equal(visibleLayerCount(enterFrame(2.4)), 1);
    assert.equal(visibleLayerCount(enterFrame(16.52)), 2);
    assert.equal(visibleLayerCount(enterFrame(30.44)), 3);
    const a = layerMotion(enterFrame(16.52) + 20, 0);
    const b = layerMotion(enterFrame(16.52) + 20, 0);
    assert.deepEqual(a, b);
    assert.equal(a.reduced, true);
    assert.equal(layerMotion(enterFrame(2.4) + 8, 0).draw > 0, true);
    assert.equal(layerMotion(enterFrame(32.9), 2).opacity > 0.85, true);
    assert.equal(layerMotion(enterFrame(31.2), 2).opacity > 0.9, true);
    assert.equal(layerMotion(Math.round(GOLD_DURATION * GOLD_FPS) - 1, 2).visible, false);
  });
});
