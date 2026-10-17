import assert from "node:assert/strict";
import test from "node:test";
import { segmentForLineBreak } from "./segment.ts";
import { layoutText } from "../utils/textLayout.ts";

const measure = (text: string, fontSize: number) => [...text].length * fontSize;

test("a number stays with its unit", () => {
  const price = segmentForLineBreak("房价涨了8000元");
  assert.equal(price.join(""), "房价涨了8000元");
  assert.ok(price.some((token) => token.includes("8000元")));
  const rate = segmentForLineBreak("回报率12%");
  assert.equal(rate.join(""), "回报率12%");
  assert.ok(rate.some((token) => token.includes("12%")));
  const measure = segmentForLineBreak("问自己三个问题");
  assert.ok(measure.some((token) => token === "三个"));
});

test("chinese wrap does not leave a one-character orphan", () => {
  const layout = layoutText({
    text: "买房送身份听起来是不是特别诱人",
    maxWidth: 7 * 48,
    maxHeight: 400,
    minFontSize: 48,
    maxFontSize: 48,
    lineHeight: 1.2,
    measure,
    locale: "zh-CN",
    wrapMode: "auto",
  });
  const lines = layout.lines.map((line) => line.join(""));
  assert.ok(lines.length >= 2);
  assert.ok([...lines[lines.length - 1]].length >= 2);
  assert.equal(lines.join(""), "买房送身份听起来是不是特别诱人");
});

test("绿卡 stays together and a leftover character is pulled up", () => {
  const card = segmentForLineBreak("还白得个绿卡");
  assert.ok(card.some((token) => token === "绿卡"));
  const layout = layoutText({
    text: "特别诱人",
    maxWidth: 3 * 48,
    maxHeight: 400,
    minFontSize: 48,
    maxFontSize: 48,
    lineHeight: 1.2,
    measure,
    locale: "zh-CN",
  });
  const lines = layout.lines.map((line) => line.join(""));
  assert.ok([...lines[lines.length - 1]].length >= 2);
  assert.equal(lines.join(""), "特别诱人");
});

test("punctuation stays on the previous character", () => {
  const tokens = segmentForLineBreak("身份，护照。");
  assert.ok(tokens.some((token) => token.endsWith("，")));
  assert.ok(tokens.some((token) => token.endsWith("。")));
});

test("english and russian still break on spaces", () => {
  const english = layoutText({
    text: "at least three shareholders",
    maxWidth: 120,
    maxHeight: 200,
    minFontSize: 28,
    maxFontSize: 28,
    lineHeight: 1.2,
    measure: (text, size) => text.length * size * 0.5,
    locale: "en-US",
  });
  assert.ok(english.lines.every((line) => line.every((word) => !word.includes(" "))));
  const russian = layoutText({
    text: "перевод документов",
    maxWidth: 80,
    maxHeight: 200,
    minFontSize: 28,
    maxFontSize: 28,
    lineHeight: 1.2,
    measure: (text, size) => text.length * size * 0.5,
    locale: "ru-RU",
  });
  assert.deepEqual(russian.lines.flat(), ["перевод", "документов"]);
});
