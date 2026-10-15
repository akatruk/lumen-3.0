import assert from "node:assert/strict";
import test from "node:test";
import { chosenDuration } from "../src/durationChoice.ts";

test("the last five-second stop keeps speech past that stop", () => {
  assert.equal(chosenDuration(60, 63.466667), 63.466667);
  assert.equal(chosenDuration(55, 63.466667), 55);
  assert.equal(chosenDuration(60, 60), 60);
  assert.equal(chosenDuration(45, 63.466667), 45);
});
