import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CANVAS, SAFE_INSET } from "../themes/tokens";
import { framesFromSeconds, secondsFromFrames, sumDurationFrames, tryFramesFromSeconds } from "./duration";
import { safeContentBox } from "./safeArea";

describe("duration calculations", () => {
  it("converts seconds at 30fps", () => {
    assert.equal(framesFromSeconds(2), 60);
    assert.equal(framesFromSeconds(2.5), 75);
    assert.equal(framesFromSeconds(1 / 30), 1);
    assert.equal(secondsFromFrames(90), 3);
    assert.equal(tryFramesFromSeconds(0), undefined);
    assert.equal(tryFramesFromSeconds(-1), undefined);
  });

  it("sums scene durations", () => {
    assert.equal(sumDurationFrames([90, 90, 90]), 270);
    assert.throws(() => sumDurationFrames([90, 0]));
  });
});

describe("safe area", () => {
  it("insets a 1080x1920 frame for short-form UI", () => {
    const box = safeContentBox();
    assert.equal(CANVAS.width, 1080);
    assert.equal(CANVAS.height, 1920);
    assert.equal(CANVAS.fps, 30);
    assert.equal(box.x, SAFE_INSET.left);
    assert.equal(box.y, SAFE_INSET.top);
    assert.equal(box.width, 1080 - SAFE_INSET.left - SAFE_INSET.right);
    assert.equal(box.height, 1920 - SAFE_INSET.top - SAFE_INSET.bottom);
    assert.equal(box.width, 888);
    assert.equal(box.height, 1420);
  });
});
