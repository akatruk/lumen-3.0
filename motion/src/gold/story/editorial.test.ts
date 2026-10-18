import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import { captionAt } from "../threeLayersModel";
import {
  CAPTION_BAND,
  FEET,
  SPEAKER_A,
  SPEAKER_B,
  SPEAKER_C,
  SPEAKER_D,
  STORY_END,
  STORY_FRAMES,
  STORY_START,
  V1_PROOF_SHA,
  clusterLabel,
  documentBox,
  documentOpacity,
  familyOpacity,
  familyPoses,
  graphicLabel,
  photoOpacity,
  rectsOverlap,
  sceneAt,
  sourceTime,
  speakerBox,
} from "./editorialModel";

test("the proof is one 20–30s excerpt ending on the last gold caption", () => {
  const seconds = STORY_FRAMES / 30;
  assert.ok(seconds >= 20 && seconds <= 30);
  assert.equal(STORY_START + seconds, STORY_END);
  assert.equal(captionAt(STORY_START), "就不要研究依赖长期");
  assert.equal(captionAt(STORY_END - 0.05), "这里不只是申请费");
});

test("four scenes follow the spoken family handoff", () => {
  assert.equal(sceneAt(16.52), "A");
  assert.equal(captionAt(17), "第二层叫家庭结构");
  assert.equal(sceneAt(19.6), "B");
  assert.equal(captionAt(19.6), "配偶未成年子女");
  assert.equal(sceneAt(22.4), "C");
  assert.equal(captionAt(22.4), "成年子女和父母能否一起申请");
  assert.equal(sceneAt(26), "D");
  assert.equal(captionAt(26), "今天适合三口之家的方案");
  assert.equal(captionAt(31), "第三层叫代价");
});

test("speaker scale changes only at the scene cuts", () => {
  assert.deepEqual(speakerBox(17.2), SPEAKER_A);
  assert.ok(speakerBox(19.7).width < SPEAKER_A.width / 2);
  assert.deepEqual(speakerBox(22.4), SPEAKER_C);
  assert.deepEqual(speakerBox(31), SPEAKER_D);
  assert.ok(SPEAKER_D.height > SPEAKER_C.height);
  assert.ok(SPEAKER_B.height < SPEAKER_D.height);
});

test("family plates stay inside the frame and off the caption", () => {
  for (const excerpt of [21.4, 22.4, 24.4]) {
    const people = familyPoses(excerpt);
    assert.equal(people.length, 6);
    for (const person of people) {
      if (person.opacity < 0.5) continue;
      assert.ok(person.left >= 0, person.id);
      assert.ok(person.left + person.width <= 1080, person.id);
      assert.ok(person.top + person.height <= FEET + 1, person.id);
      assert.ok(person.top + person.height <= CAPTION_BAND.top - 8, person.id);
    }
    const speaker = speakerBox(excerpt);
    const core = clusterLabel(excerpt, ["adultA", "adultB"]);
    const extended = clusterLabel(excerpt, ["elderA", "elderB"]);
    assert.ok(!rectsOverlap(core, speaker));
    assert.ok(!rectsOverlap(core, CAPTION_BAND));
    assert.ok(!rectsOverlap(extended, CAPTION_BAND));
    assert.ok(extended.left > core.left + core.width - 8);
  }
  const held = familyPoses(22.4);
  const core = held.filter((person) => ["adultA", "adultB", "child"].includes(person.id));
  const extended = held.filter((person) => ["youth", "elderA", "elderB"].includes(person.id));
  assert.ok(core.every((person) => person.opacity > 0.9));
  assert.ok(extended.every((person) => person.opacity > 0.9));
  assert.ok(Math.min(...core.map((person) => person.left)) < Math.min(...extended.map((person) => person.left)));
});

test("the document is large, beside the speaker, and does not repeat the caption", () => {
  const paper = documentBox(31);
  const speaker = speakerBox(31);
  assert.deepEqual(speaker, SPEAKER_D);
  assert.ok(paper.width >= 480);
  assert.ok(paper.height >= 1100);
  assert.ok(!rectsOverlap(paper, speaker));
  assert.ok(paper.top + paper.height <= CAPTION_BAND.top - 8);
  assert.ok(!rectsOverlap(paper, CAPTION_BAND));
  for (const excerpt of [17, 26, 29, 31, 32.5]) {
    const label = graphicLabel(excerpt);
    assert.ok(label.length > 0);
    assert.notEqual(label, captionAt(excerpt));
    assert.ok(captionAt(excerpt).includes(label));
  }
  assert.equal(graphicLabel(19.6), "");
  assert.equal(graphicLabel(22.4), "");
  assert.equal(graphicLabel(24.5), "");
  assert.ok(Math.abs(sourceTime(16.52) - 59.32) < 0.001);
});

test("scene changes follow the spoken line and the previous file stays put", () => {
  assert.ok(photoOpacity(19.6) > 0.9);
  assert.ok(photoOpacity(20.68) < 0.05);
  assert.ok(familyOpacity(22.4) > 0.95);
  assert.ok(familyOpacity(26) < 0.05);
  assert.ok(documentOpacity(26) > 0.95);
  assert.ok(documentOpacity(22.4) < 0.05);
  assert.equal(graphicLabel(28.4), "三口之家");
  assert.equal(graphicLabel(28.56), "照顾父母");
  const hash = createHash("sha256")
    .update(readFileSync(new URL("../../../../output/cinematic-storytelling/original3-editorial-proof.mp4", import.meta.url)))
    .digest("hex");
  assert.equal(hash, V1_PROOF_SHA);
});
