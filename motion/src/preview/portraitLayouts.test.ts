import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  PORTRAIT,
  criteriaCardsFor,
  overlapsFaceBand,
  splitMediaRect,
  splitSpeakerRect,
} from "./portraitLayouts";
import { DIRECTOR_V3_FPS, beatsFor, framesForSeconds } from "./DirectorV3";

describe("portraitLayouts", () => {
  it("fills the 1080×1920 canvas without a bottom black void in splits", () => {
    const speaker = splitSpeakerRect("right");
    const media = splitMediaRect("left");
    assert.equal(speaker.top + speaker.height + PORTRAIT.splitSpeaker.bottomClearance, PORTRAIT.height);
    assert.equal(media.height, speaker.height);
    assert.equal(media.width + PORTRAIT.gutter + speaker.width + PORTRAIT.pad * 2, PORTRAIT.width);
    assert.ok(media.width > 400);
    assert.ok(media.height / media.width > 1.4);
  });

  it("keeps face-band overlap detection for upper-center overlays", () => {
    assert.equal(overlapsFaceBand(0.2, 0.2), true);
    assert.equal(overlapsFaceBand(0.7, 0.15), false);
  });

  it("exposes goals/family/budget as relationship explanations in RU/EN/ZH", () => {
    for (const locale of ["ru-RU", "en-US", "zh-CN"]) {
      const cards = criteriaCardsFor(locale);
      assert.equal(cards.length, 3);
      for (const card of cards) {
        assert.ok(card.title.length > 0);
        assert.ok(card.explanation.length > 6);
      }
    }
    assert.match(criteriaCardsFor("ru-RU")[0].explanation, /переезжаете/);
    assert.match(criteriaCardsFor("en-US")[1].explanation, /travels|who/i);
    assert.equal(criteriaCardsFor("zh-CN")[2].title, "预算");
  });

  it("starts the residency media beat before 4s on a 20s cut", () => {
    const frames = framesForSeconds(20);
    const [hook, residency] = beatsFor(frames);
    assert.ok(hook.duration / DIRECTOR_V3_FPS < 4);
    assert.ok(residency.from / DIRECTOR_V3_FPS < 4);
    assert.ok(residency.duration > hook.duration);
  });
});
