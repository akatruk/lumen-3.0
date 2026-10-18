import assert from "node:assert/strict";
import test from "node:test";
import { cardLines, heldListCategory, type ListScene } from "./documentCards";

const chain: ListScene[] = [
  {
    sceneComposition: { speakerPresentation: "split" },
    typography: { stepCues: [{ text: "四种证据链", start: 44.96 }] },
  },
  {
    sceneComposition: { speakerPresentation: "split" },
    typography: {
      stepCues: [
        { text: "原始积累证明", start: 47.6 },
        { text: "工资完税单", start: 50.08 },
        { text: "分红凭证", start: 51.68 },
        { text: "股东决议", start: 53.44 },
      ],
    },
  },
  {
    sceneComposition: { speakerPresentation: "split" },
    typography: { stepCues: [{ text: "资产变现链条", start: 55.6 }] },
  },
  { sceneComposition: { speakerPresentation: "fullscreen" }, typography: { stepCues: [] } },
  {
    sceneComposition: { speakerPresentation: "split" },
    typography: {
      stepCues: [
        { text: "房产买卖合同", start: 57.84 },
        { text: "股权转让协议", start: 59.76 },
        { text: "银行完税流水", start: 61.76 },
      ],
    },
  },
];

test("the first list keeps its own category", () => {
  assert.equal(heldListCategory(chain, 1), "");
});

test("documents after a talking-head gap keep the previous category", () => {
  assert.equal(heldListCategory(chain, 4), "资产变现链条");
});

test("six-character names stay on one line in the left column", () => {
  for (const text of ["工资完税单", "分红凭证", "股东决议", "房产买卖合同", "股权转让协议", "银行完税流水"]) {
    const fit = cardLines(text, 400, 40);
    assert.deepEqual(fit.lines, [text]);
    assert.ok(fit.size >= 32);
  }
});
