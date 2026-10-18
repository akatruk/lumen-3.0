import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { sceneRevealFrame } from "./time";

describe("timeline clock", () => {
  it("maps event-local steps onto speech time when the scene starts at the cluster", () => {
    const origin = 42.8;
    const fps = 30;
    assert.equal(sceneRevealFrame(2.4, origin, origin, fps), Math.round(2.4 * fps));
    assert.equal(sceneRevealFrame(16.52, origin, origin, fps), Math.round(16.52 * fps));
    assert.equal(sceneRevealFrame(30.44, origin, origin, fps), Math.round(30.44 * fps));
  });

  it("does not reveal a later step early when the scene starts before the cluster", () => {
    const frame = sceneRevealFrame(2.4, 42.8, 40.0, 30);
    assert.equal(frame, Math.round((45.2 - 40.0) * 30));
    assert.ok(frame > Math.round(2.4 * 30));
  });

  it("hides a step until its spoken time and does not subtract the origin twice", () => {
    const reveal = sceneRevealFrame(30.44, 42.8, 42.8, 30);
    assert.equal(reveal, Math.round(30.44 * 30));
    assert.ok(reveal > sceneRevealFrame(16.52, 42.8, 42.8, 30));
  });
});
