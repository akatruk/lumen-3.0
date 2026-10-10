import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { matchConceptTriggers, primaryConceptTrigger, spokenNumber } from "./match";
import { syncConceptTriggers } from "./sync";
import { CONCEPT_PRESETS, CONCEPT_TRIGGER_RULES } from "./presets";
import { CONCEPT_PRESET_IDS } from "./schema";

describe("concept triggers", () => {
  it("lists ten presets and rules cover every preset id", () => {
    assert.equal(CONCEPT_PRESETS.length, 10);
    assert.deepEqual(
      CONCEPT_PRESETS.map((p) => p.id).sort(),
      [...CONCEPT_PRESET_IDS].sort(),
    );
    const covered = new Set(CONCEPT_TRIGGER_RULES.map((r) => r.presetId));
    for (const id of CONCEPT_PRESET_IDS) assert.ok(covered.has(id), id);
  });

  it("matches Russian relocation and residency phrases", () => {
    const move = primaryConceptTrigger("Планируете переезд");
    assert.equal(move?.presetId, "route_link");
    const residency = primaryConceptTrigger("второй вид на жительство");
    assert.equal(residency?.presetId, "document_stamp");
  });

  it("matches English growth and Chinese risk", () => {
    assert.equal(primaryConceptTrigger("profit growth this quarter")?.presetId, "growth_arrow");
    assert.equal(primaryConceptTrigger("市场有风险")?.presetId, "risk_arrow");
  });

  it("does not invent a number when none is spoken", () => {
    assert.equal(spokenNumber("планируете переезд"), undefined);
    assert.equal(spokenNumber("budget is 12 percent"), 12);
  });

  it("syncs caption windows to frame ranges", () => {
    const synced = syncConceptTriggers(
      [
        { from: 0, duration: 66, text: "Планируете переезд" },
        { from: 66, duration: 66, text: "второй вид на жительство" },
        { from: 132, duration: 66, text: "hello world" },
      ],
      1,
    );
    assert.equal(synced.length, 2);
    assert.equal(synced[0].fromFrame, 0);
    assert.equal(synced[0].presetId, "route_link");
    assert.equal(synced[1].presetId, "document_stamp");
  });

  it("ranks longer phrases above short stems", () => {
    const hits = matchConceptTriggers("семьи и бюджета", 3);
    assert.ok(hits.length >= 1);
    assert.equal(hits[0].presetId, "family_cluster");
  });
});
