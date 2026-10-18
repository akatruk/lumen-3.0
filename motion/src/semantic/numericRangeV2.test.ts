import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { NumericRangeV2 } from "./numericRangeV2";
import {
  RANGE_PRESENTATIONS,
  buildRangeModel,
  formatEndpoint,
  graphicRect,
  rangeChoreography,
  rangeLayoutSafety,
  wrapRangeLabel,
} from "./numericRangeModel";

const SALARY = {
  range: { lowText: "1.5万", highText: "2.5万", unit: "泰国", kind: "salary" as const },
  labels: { "zh-CN": "月薪", "en-US": "Monthly pay", "ru-RU": "Месячная оплата" },
};
const CNY = {
  range: { lowText: "3千", highText: "4千", unit: "人民币", kind: "money" as const },
  labels: { "zh-CN": "金额", "en-US": "Amount", "ru-RU": "Сумма" },
};

describe("numeric range v2", () => {
  it("is one component with three presentations", () => {
    assert.equal(typeof NumericRangeV2, "function");
    assert.deepEqual([...RANGE_PRESENTATIONS], ["finance", "editorial", "split"]);
  });

  it("keeps spoken units and does not rename the currency", () => {
    const salary = buildRangeModel(SALARY, "zh-CN");
    const cny = buildRangeModel(CNY, "zh-CN");
    assert.ok(salary && cny);
    assert.equal(salary.unit, "泰国");
    assert.equal(cny.unit, "人民币");
    assert.equal(salary.lowText, "1.5万");
    assert.equal(salary.highText, "2.5万");
    assert.equal(cny.lowText, "3千");
    assert.equal(cny.highText, "4千");
    assert.equal(salary.heading, "月薪");
    assert.equal(cny.heading, "金额");
    for (const model of [salary, cny]) {
      const blob = `${model.unit} ${model.lowDisplay} ${model.highDisplay} ${model.heading}`;
      assert.equal(/THB|฿|泰铢|Baht/.test(blob), false);
    }
  });

  it("formats the numeric body per locale and keeps 万 and 千", () => {
    assert.equal(formatEndpoint("1.5万", "zh-CN"), "1.5万");
    assert.equal(formatEndpoint("1.5万", "en-US"), "1.5万");
    assert.equal(formatEndpoint("1.5万", "ru-RU"), "1,5万");
    assert.equal(formatEndpoint("2.5万", "ru-RU"), "2,5万");
    assert.equal(formatEndpoint("3千", "en-US"), "3千");
    assert.equal(formatEndpoint("4千", "zh-CN"), "4千");
    const ru = buildRangeModel(SALARY, "ru-RU");
    const en = buildRangeModel(SALARY, "en-US");
    assert.equal(ru?.heading, "Месячная оплата");
    assert.equal(ru?.lowDisplay, "1,5万");
    assert.equal(en?.heading, "Monthly pay");
    assert.equal(en?.unit, "泰国");
  });

  it("wraps a long Russian label on spaces and Chinese without splitting a digit run", () => {
    const ru = wrapRangeLabel("Месячная оплата переводчика", "ru-RU", 12);
    assert.ok(ru.length >= 2);
    assert.deepEqual(ru.join(" ").split(/\s+/), ["Месячная", "оплата", "переводчика"]);
    for (const line of ru) assert.equal(line.includes(" "), line.trim().split(/\s+/).length > 1);
    const zh = wrapRangeLabel("每月薪酬区间说明", "zh-CN", 4);
    assert.ok(zh.length >= 2);
    assert.ok(zh.every((line) => [...line].length <= 4));
    assert.equal(zh.join(""), "每月薪酬区间说明");
    const figure = wrapRangeLabel("区间8000元整", "zh-CN", 3);
    assert.equal(figure.some((line) => line.includes("8000")), true);
    assert.equal(figure.some((line) => line === "80"), false);
  });

  it("keeps the same endpoints across presentations and clears face, chest, and captions", () => {
    const models = RANGE_PRESENTATIONS.map(() => buildRangeModel(SALARY, "zh-CN"));
    assert.equal(models.every((model) => model?.lowDisplay === "1.5万" && model.unit === "泰国"), true);
    for (const presentation of RANGE_PRESENTATIONS) {
      const safety = rangeLayoutSafety(presentation);
      assert.equal(safety.faceClear, true, presentation);
      assert.equal(safety.chestClear, true, presentation);
      assert.equal(safety.captionClear, true, presentation);
      assert.equal(safety.faceInsideFrame, true, presentation);
      assert.ok(safety.connector >= 10, presentation);
      const rect = graphicRect(presentation);
      assert.ok(rect.width >= 300 && rect.height >= 700);
    }
    const editorial = rangeLayoutSafety("editorial");
    const split = rangeLayoutSafety("split");
    assert.equal(editorial.connector, 16);
    assert.ok(split.speakerShare >= 0.55 && split.speakerShare <= 0.65);
    assert.ok(split.graphicShare >= 0.35 && split.graphicShare <= 0.45);
    assert.notDeepEqual(graphicRect("finance"), graphicRect("editorial"));
  });

  it("orders entry, reveal, connect, emphasis, and exit for a short and a long segment", () => {
    for (const frames of [48, 60, 156, 240]) {
      const phase = rangeChoreography(frames);
      assert.ok(phase.enter <= phase.lowAt);
      assert.ok(phase.lowAt < phase.highAt);
      assert.ok(phase.highAt < phase.connectAt);
      assert.ok(phase.connectAt < phase.connectEnd);
      assert.ok(phase.connectEnd <= phase.emphasisAt);
      assert.ok(phase.emphasisAt < phase.exitAt);
      assert.ok(phase.exitAt < phase.frames);
    }
  });
});
