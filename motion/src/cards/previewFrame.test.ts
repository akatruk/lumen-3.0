import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { CARD_HOLD } from "./MultilingualCardShowcase";
import { getPreviewFrame } from "./previewFrame";

describe("getPreviewFrame", () => {
  it("uses 75 percent of the card once the fade has finished", () => {
    assert.equal(getPreviewFrame({}, CARD_HOLD), 33);
    assert.equal(getPreviewFrame({}, 45), Math.floor(45 * 0.75));
  });

  it("lets a component name its own settled frame", () => {
    assert.equal(getPreviewFrame({ previewFrame: 40 }, 45), 40);
  });

  it("stays inside the card and never uses the last exit frame", () => {
    assert.equal(getPreviewFrame({ previewFrame: 90 }, 45), 44);
    assert.equal(getPreviewFrame({}, 1), 0);
  });
});
