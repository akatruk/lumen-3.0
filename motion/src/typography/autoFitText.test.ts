import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import { theme } from "../themes/tokens";
import { safeContentBox } from "../utils/safeArea";
import { tokenizeWords } from "../utils/words";
import { fitPhrase } from "./fitPhrase";
import { lockedText } from "./lock";

const PHRASES = [
  "Planning a relocation",
  "Consultation to filing",
  "Goal, family, and budget",
  "International relocation consultation",
] as const;

const BROKEN = [/Plannin(?!g)/, /relocatio(?!n)/, /Consulatio(?!n)/, /famil(?!y)/, /budg(?!et)/];

function assertIntact(source: string, lines: string[][]) {
  const produced = lines.flat();
  assert.deepEqual(produced, tokenizeWords(source), source);
  const joined = produced.join(" ");
  for (const pattern of BROKEN) {
    assert.equal(pattern.test(joined), false, `${source} matched ${pattern}`);
  }
  for (const line of lines) {
    for (const word of line) assert.equal(word.includes(" "), false);
  }
  assert.equal(joined, source.trim().replace(/\s+/g, " "));
}

describe("AutoFitText layout", () => {
  const safe = safeContentBox();

  for (const phrase of PHRASES) {
    it(`keeps every word whole: ${phrase}`, () => {
      for (const maxWidth of [40, 90, 140, 220, 360, 520, safe.width, 1200]) {
        for (const maxHeight of [80, 220, 1400]) {
          for (const wrapMode of ["auto", "word"] as const) {
            const layout = fitPhrase({
              text: phrase,
              maxWidth,
              maxHeight,
              role: theme.type.caption,
              wrapMode,
            });
            assertIntact(phrase, layout.lines);
            assert.equal(Number.isFinite(layout.fontSize), true);
            assert.ok(layout.fitScale > 0 && layout.fitScale <= 1);
            if (wrapMode === "word") assert.equal(layout.lines.length, tokenizeWords(phrase).length);
          }
        }
      }
    });
  }

  it("does not produce the known mid-word fragments", () => {
    const fragments = ["Plannin", "relocatio", "Consulatio", "famil", "budg"];
    for (const phrase of PHRASES) {
      const layout = fitPhrase({
        text: phrase,
        maxWidth: 96,
        maxHeight: 480,
        role: theme.type.hook,
      });
      const tokens = layout.lines.flat();
      for (const fragment of fragments) {
        assert.equal(tokens.includes(fragment), false, fragment);
      }
    }
  });

  it("shrinks the font when the box gets narrower", () => {
    const wide = fitPhrase({
      text: "Planning a relocation",
      maxWidth: 2000,
      maxHeight: 800,
      role: theme.type.hook,
    });
    const narrow = fitPhrase({
      text: "Planning a relocation",
      maxWidth: 240,
      maxHeight: 800,
      role: theme.type.hook,
    });
    assert.ok(narrow.fontSize < wide.fontSize);
    assert.equal(wide.lines.length, 1);
    assert.ok(narrow.lines.length > 1);
  });

  it("keeps punctuation on the word and fails gracefully when the box is tiny", () => {
    const layout = fitPhrase({
      text: "Planning a relocation?",
      maxWidth: 48,
      maxHeight: 36,
      role: { min: 32, max: 32, weight: 600, lineHeight: 1.1, tracking: 0 },
    });
    assert.deepEqual(layout.lines.flat(), ["Planning", "a", "relocation?"]);
    assert.equal(layout.overflow, true);
    assert.ok(layout.fitScale < 1);
  });

  it("is deterministic for the same phrase", () => {
    const once = fitPhrase({
      text: "International relocation consultation",
      maxWidth: safe.width,
      maxHeight: 400,
      role: theme.type.caption,
    });
    const twice = fitPhrase({
      text: "International relocation consultation",
      maxWidth: safe.width,
      maxHeight: 400,
      role: theme.type.caption,
    });
    assert.deepEqual(once, twice);
  });

  it("fits the preview phrases on two lines", () => {
    const role = { min: 56, max: 84, weight: 600, lineHeight: 1.08, tracking: -0.02 };
    const box = { maxWidth: 936, maxHeight: 180, role, wrapMode: "auto" as const, maxLines: 2 };
    const phrases = [
      { text: "Planning an international relocation", locale: "en-US" as const },
      { text: "正在计划移居国外吗？", locale: "zh-CN" as const },
      { text: "Планируете переезд", locale: "ru-RU" as const },
      { text: "второй вид на жительство", locale: "ru-RU" as const },
      { text: "с чего начать?", locale: "ru-RU" as const },
    ];
    for (const phrase of phrases) {
      const layout = fitPhrase({ ...box, text: phrase.text, locale: phrase.locale });
      assert.ok(layout.lines.length <= 2, phrase.text);
      assert.equal(layout.overflow, false, phrase.text);
      assert.ok(layout.fontSize >= 56, phrase.text);
    }
    const tooLong = fitPhrase({ ...box, text: "Планируете международный переезд", locale: "ru-RU" });
    assert.equal(tooLong.overflow, true);
    for (const part of ["Планируете", "международный переезд"]) {
      const layout = fitPhrase({ ...box, text: part, locale: "ru-RU" });
      assert.equal(layout.overflow, false, part);
      assert.ok(layout.lines.length <= 2, part);
    }
  });

  it("paints words with nowrap and keep-all", () => {
    assert.equal(lockedText.whiteSpace, "nowrap");
    assert.equal(lockedText.wordBreak, "keep-all");
    assert.equal(lockedText.hyphens, "none");
    const source = readFileSync(new URL("./AutoFitText.tsx", import.meta.url), "utf8");
    assert.equal(source.includes("break-all"), false);
    assert.equal(source.includes("fitPhrase"), true);
    assert.equal(source.includes("WordReveal"), true);
  });
});
