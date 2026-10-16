import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { theme } from "../themes/tokens";
import { fitPhrase } from "../typography/fitPhrase";
import { rangeMotionAt, timelineColumn, timelineRows } from "./motionDesign";

describe("timeline presentation", () => {
  it("keeps two to five source labels and does not rename them as steps", () => {
    const rows = timelineRows(["使用场景", "家庭结构", "代价", "第四", "第五", "第六"]);
    assert.deepEqual(rows, ["使用场景", "家庭结构", "代价", "第四", "第五"]);
    assert.equal(rows.some((label) => label.includes("步骤")), false);
    assert.equal(timelineColumn(952, rows.length).connect, true);
    assert.equal(timelineColumn(504, 2).connect, true);
  });

  it("uses a single label without inventing a second item", () => {
    const rows = timelineRows(["代价"]);
    assert.deepEqual(rows, ["代价"]);
    assert.equal(timelineColumn(952, rows.length).connect, false);
  });

  it("fits the column inside the editorial and the split graphic", () => {
    for (const width of [952, 504]) {
      const column = timelineColumn(width, 3);
      assert.ok(column.occupied <= width, `${width} occupied ${column.occupied}`);
      assert.ok(column.labelWidth >= 200);
      assert.ok(column.activeHeight > column.quietHeight);
    }
  });

  it("wraps Chinese, Russian, and English inside the label box", () => {
    const chinese = fitPhrase({
      text: "配偶、未成年子女和父母能否一起申请。",
      maxWidth: 420,
      maxHeight: 96,
      role: theme.type.title,
      locale: "zh-CN",
      maxLines: 2,
    });
    assert.equal(chinese.overflow, false);
    assert.ok(chinese.lines.flat().join("").includes("偶、"));
    const english = fitPhrase({
      text: "Bank accounts, work permits and visa applications",
      maxWidth: 400,
      maxHeight: 96,
      role: theme.type.support,
      locale: "en-US",
      maxLines: 2,
    });
    assert.equal(english.overflow, false);
    assert.ok(english.lines.length === 2);
    const russian = fitPhrase({
      text: "Несовершеннолетние дети и родители",
      maxWidth: timelineColumn(504, 3).labelWidth,
      maxHeight: 96,
      role: theme.type.support,
      locale: "ru-RU",
      maxLines: 2,
    });
    const word = russian.lines.flat().find((part) => part.includes("Несовершеннолетние"));
    assert.ok(word);
    assert.ok(russian.fitScale >= 0.75);
    assert.ok(russian.blockWidth * russian.fitScale <= timelineColumn(504, 3).labelWidth + 1);
  });
});

describe("numeric range motion", () => {
  it("reveals the low end, then the span, then the high end", () => {
    const start = rangeMotionAt(0);
    assert.deepEqual(start, { low: 0, span: 0, high: 0 });
    const mid = rangeMotionAt(12);
    assert.equal(mid.low, 1);
    assert.ok(mid.span > 0 && mid.span < 1);
    assert.equal(mid.high, 0);
    const held = rangeMotionAt(30);
    assert.deepEqual(held, { low: 1, span: 1, high: 1 });
    assert.deepEqual(rangeMotionAt(30), rangeMotionAt(30));
  });

  it("does not publish a midpoint or a percent", () => {
    const motion = rangeMotionAt(20);
    assert.equal("mid" in motion, false);
    assert.equal("percent" in motion, false);
  });
});
