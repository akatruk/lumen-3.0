import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rangeKindLabel } from "./numericRange";

describe("numeric range labels", () => {
  it("keeps salary, day rate, and amount apart in three locales", () => {
    assert.equal(rangeKindLabel("salary", "zh-CN"), "月薪");
    assert.equal(rangeKindLabel("salary", "en-US"), "Monthly pay");
    assert.equal(rangeKindLabel("salary", "ru-RU"), "Месячная оплата");
    assert.equal(rangeKindLabel("day_rate", "zh-CN"), "每天");
    assert.equal(rangeKindLabel("day_rate", "en-US"), "Per day");
    assert.equal(rangeKindLabel("day_rate", "ru-RU"), "В день");
    assert.equal(rangeKindLabel("money", "zh-CN"), "金额");
    assert.notEqual(rangeKindLabel("salary", "zh-CN"), "营收");
    assert.notEqual(rangeKindLabel("money", "en-US"), "Revenue");
  });
});
