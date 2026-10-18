import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { familyLabel, familyPose, familySpeakerRect, familyStageActive, SPEAKER_DOCK, SPEAKER_EMPHASIS, SPEAKER_OPEN } from "./v2/FamilyStage";
import { GoldV2Film } from "./v2/GoldV2Film";
import {
  COST_BOX,
  DIMENSION_TITLE,
  FAMILY_BOX,
  GOLD_DURATION,
  GOLD_FPS,
  HERO_BOX,
  HERO_MIN,
  SPEAKER_COST,
  SPEAKER_FAMILY,
  SPEAKER_SCENE,
  V2_CAPTION,
  V2_COPY,
  captionAt,
  dimensionAt,
  enterFrame,
  familyFocus,
  heroAt,
  rectsOverlap,
  speakerRect,
} from "./v2/model";

describe("gold standard v2", () => {
  it("is one component", () => {
    assert.equal(typeof GoldV2Film, "function");
  });

  it("localizes dimension titles without duplicating a component", () => {
    assert.deepEqual(DIMENSION_TITLE["zh-CN"], ["使用场景", "家庭结构", "代价"]);
    assert.equal(DIMENSION_TITLE["en-US"][0] === DIMENSION_TITLE["zh-CN"][0], false);
    assert.equal(DIMENSION_TITLE["ru-RU"][2].length > 0, true);
    assert.equal(V2_COPY["zh-CN"].fee.includes("49"), false);
    assert.equal(V2_COPY["en-US"].fee.toLowerCase().includes("dollar"), false);
  });

  it("keeps spoken evidence", () => {
    assert.equal(captionAt(2.4), "第一层叫使用场景");
    assert.equal(captionAt(16.52), "第二层叫家庭结构");
    assert.equal(captionAt(30.44), "第三层叫代价");
    assert.equal(captionAt(32.2), "这里不只是申请费");
  });

  it("changes the hero inside a long dimension", () => {
    assert.equal(dimensionAt(enterFrame(4)), 1);
    assert.equal(heroAt(enterFrame(4)), "none");
    assert.equal(heroAt(enterFrame(6)), "house");
    assert.equal(heroAt(enterFrame(8.2)), "work");
    assert.equal(heroAt(enterFrame(10)), "school");
    assert.equal(heroAt(enterFrame(12)), "stay");
    assert.equal(heroAt(enterFrame(18)), "family");
    assert.equal(familyFocus(enterFrame(26)), "household");
    assert.equal(familyFocus(enterFrame(29)), "parents");
    assert.equal(heroAt(enterFrame(31)), "cost");
  });

  it("keeps the hero larger than a chip and off the caption", () => {
    for (const box of [HERO_BOX, FAMILY_BOX, COST_BOX]) {
      assert.equal(box.width >= HERO_MIN.width, true);
      assert.equal(box.height >= HERO_MIN.height, true);
      assert.equal(rectsOverlap(box, V2_CAPTION), false);
    }
    assert.equal(rectsOverlap(SPEAKER_SCENE, V2_CAPTION), false);
    assert.equal(rectsOverlap(SPEAKER_FAMILY, V2_CAPTION), false);
    assert.equal(rectsOverlap(SPEAKER_COST, V2_CAPTION), false);
    assert.equal(rectsOverlap(SPEAKER_SCENE, HERO_BOX), false);
    assert.equal(rectsOverlap(SPEAKER_FAMILY, FAMILY_BOX), false);
    assert.equal(rectsOverlap(SPEAKER_COST, COST_BOX), false);
  });

  it("moves the speaker and is deterministic", () => {
    const early = speakerRect(10);
    const scene = speakerRect(enterFrame(8));
    assert.equal(early.width, 1080);
    assert.equal(scene.width < 500, true);
    assert.deepEqual(speakerRect(enterFrame(20)), speakerRect(enterFrame(20)));
    assert.equal(Math.round(GOLD_DURATION * GOLD_FPS), 996);
  });

  it("recomposes the family without shrinking the core or covering the caption", () => {
    const lines = { title: "家庭结构", core: "配偶与子女", household: "三口之家", parents: "照顾父母" };
    const open = familyPose(enterFrame(17.2));
    assert.equal(open.people.every((p) => p.opacity === 0), true);
    const core = familyPose(enterFrame(19.6));
    const adults = core.people.filter((p) => p.kind === "adultA" || p.kind === "adultB");
    assert.equal(adults.every((p) => p.opacity > 0.9 && p.box.height >= 840), true);
    assert.equal(core.people.find((p) => p.kind === "youth")?.opacity === 0, true);
    const wide = familyPose(enterFrame(22.4));
    const held = familyPose(enterFrame(22.4));
    assert.deepEqual(wide, held);
    for (const person of wide.people) {
      assert.equal(person.opacity > 0.9, true);
      assert.equal(person.box.left >= 0, true);
      assert.equal(person.box.left + person.box.width <= 1080, true);
      assert.equal(person.box.top + person.box.height <= V2_CAPTION.top - 8, true);
      assert.equal(rectsOverlap(person.box, V2_CAPTION), false);
    }
    const coreAdult = wide.people.find((p) => p.kind === "adultA");
    assert.equal((coreAdult?.box.height ?? 0) >= 840, true);
    const speaker = familySpeakerRect(enterFrame(22.4), SPEAKER_SCENE);
    for (const person of wide.people) {
      assert.equal(person.box.top >= speaker.top + speaker.height - 4, true);
    }
    assert.equal(familyLabel(enterFrame(22.4), "en-US", { ...lines, title: "Family structure" }), "Apply together?");
    assert.equal(familyLabel(enterFrame(22.4), "ru-RU", lines).length > 0, true);
    assert.equal(familyLabel(enterFrame(26), "zh-CN", lines), "三口之家");
    assert.equal(familyLabel(enterFrame(23.8), "zh-CN", lines), "定义不同");
    const opening = familySpeakerRect(enterFrame(17.2), SPEAKER_SCENE);
    assert.equal(opening.height, SPEAKER_OPEN.height);
    assert.equal(opening.height > SPEAKER_DOCK.height, true);
    const emphasis = familySpeakerRect(enterFrame(24.2), SPEAKER_SCENE);
    const emphasisPose = familyPose(enterFrame(24.2));
    assert.equal(emphasisPose.title.left >= emphasis.left + emphasis.width, true);
    assert.equal(emphasis.height, SPEAKER_EMPHASIS.height);
    assert.equal(emphasis.height > speaker.height, true);
    const back = familySpeakerRect(enterFrame(27), SPEAKER_SCENE);
    assert.equal(back.height, SPEAKER_DOCK.height);
  });

  it("holds the new family plate past 24.00 until the cost handoff", () => {
    assert.equal(familyStageActive(enterFrame(16)), false);
    assert.equal(familyStageActive(enterFrame(16.52)), true);
    assert.equal(familyStageActive(enterFrame(24)), true);
    assert.equal(familyStageActive(enterFrame(25)), true);
    assert.equal(familyStageActive(enterFrame(30.44) + 13), true);
    assert.equal(familyStageActive(enterFrame(30.44) + 14), false);
  });
});
