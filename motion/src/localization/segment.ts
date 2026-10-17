import type { SupportedLocale } from "./language-config";

const CLOSE_PUNCT = /^[\p{P}\p{S}]+$/u;
const CLOSER = new Set(["，", "。", "！", "？", "、", "；", "：", ",", ".", "!", "?", ":", ";", ")", "]", "」", "』", "）", "》"]);
const OPENER = new Set(["「", "『", "（", "(", "[", "《", "“", "‘"]);
const UNIT = new Set(["万", "亿", "元", "块", "年", "月", "日", "岁", "平", "米", "㎡", "%", "％", "个", "次", "层", "步", "套", "间"]);

function graphemes(text: string): string[] {
  if (typeof Intl.Segmenter === "function") {
    return [...new Intl.Segmenter(undefined, { granularity: "grapheme" }).segment(text)].map((part) => part.segment);
  }
  return [...text];
}

function words(text: string, locale: string): string[] {
  if (typeof Intl.Segmenter === "function") {
    return [...new Intl.Segmenter(locale, { granularity: "word" }).segment(text)]
      .map((part) => part.segment)
      .filter((part) => part.trim().length > 0);
  }
  return [...text].filter((part) => part.trim().length > 0);
}

function attachClosers(parts: string[]): string[] {
  const out: string[] = [];
  for (const part of parts) {
    if (out.length > 0 && [...part].every((char) => CLOSER.has(char) || CLOSE_PUNCT.test(char))) {
      out[out.length - 1] += part;
    } else {
      out.push(part);
    }
  }
  return out;
}

/** Motion beats. Chinese stays in natural phrases. Latin and Cyrillic stay whole words. */
export function segmentTextForMotion(text: string, locale: SupportedLocale): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (locale === "zh-CN") return attachClosers(words(trimmed, "zh-CN"));
  return trimmed.split(/\s+/).filter((word) => word.length > 0);
}

function isDigit(char: string): boolean {
  return /^\d$/.test(char);
}

/** A spoken figure stays one token: 8000, 1.5, 8000-1. CJK still breaks around it. */
function takeNumber(chars: string[], index: number): { token: string; next: number } | null {
  if (!isDigit(chars[index] || "")) return null;
  let token = chars[index];
  let cursor = index + 1;
  while (cursor < chars.length) {
    const char = chars[cursor];
    if (isDigit(char)) {
      token += char;
      cursor += 1;
      continue;
    }
    if ((char === "." || char === ",") && isDigit(chars[cursor + 1] || "")) {
      token += char + chars[cursor + 1];
      cursor += 2;
      continue;
    }
    if (/^[–—\-~]$/.test(char) && isDigit(chars[cursor + 1] || "")) {
      token += char;
      cursor += 1;
      continue;
    }
    break;
  }
  return { token, next: cursor };
}

const CJK_NUM = new Set([..."零一二三四五六七八九十百千万两"]);

function isUnitWord(token: string): boolean {
  return [...token].every((char) => UNIT.has(char));
}

function isAsciiNumber(token: string): boolean {
  return /^\d/.test(token);
}

/** Word pieces, then glue a range to its unit and a numeral to 个/万/元. */
function tokensFromWords(parts: string[]): string[] {
  const words = attachClosers(parts);
  const tokens: string[] = [];
  let index = 0;
  while (index < words.length) {
    const word = words[index];
    if (isAsciiNumber(word)) {
      let token = word;
      index += 1;
      if (/[-–—~]$/.test(token) && index < words.length && /\d/.test(words[index])) {
        token += words[index];
        index += 1;
      }
      while (index < words.length) {
        const next = words[index];
        if (/^[–—\-~-]$/.test(next) && isAsciiNumber(words[index + 1] || "")) {
          token += next + words[index + 1];
          index += 2;
          continue;
        }
        if (isUnitWord(next) || UNIT.has(next)) {
          token += next;
          index += 1;
          continue;
        }
        break;
      }
      tokens.push(token);
      continue;
    }
    if ([...word].every((char) => CJK_NUM.has(char)) && isUnitWord(words[index + 1] || "")) {
      tokens.push(word + words[index + 1]);
      index += 2;
      continue;
    }
    tokens.push(word);
    index += 1;
  }
  return tokens;
}

/**
 * Line breaking. English and Russian break only on spaces.
 * Chinese breaks on words, and closing punctuation stays with the previous word.
 * Digit runs, ranges, and the following unit stay one token (8000-1万, 三个).
 */
export function segmentForLineBreak(text: string): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  if (/[\u4e00-\u9fff]/.test(trimmed) && typeof Intl.Segmenter === "function") {
    const parts = [...new Intl.Segmenter("zh-CN", { granularity: "word" }).segment(trimmed)]
      .map((part) => part.segment)
      .filter((part) => part.trim().length > 0);
    return tokensFromWords(parts);
  }
  const chars = graphemes(trimmed).filter((char) => char.trim().length > 0 || char === " ");
  const tokens: string[] = [];
  let pendingOpen = "";
  let index = 0;
  while (index < chars.length) {
    const char = chars[index];
    if (char === " ") {
      index += 1;
      continue;
    }
    if (OPENER.has(char)) {
      pendingOpen += char;
      index += 1;
      continue;
    }
    const number = takeNumber(chars, index);
    if (number) {
      let token = pendingOpen + number.token;
      pendingOpen = "";
      index = number.next;
      while (UNIT.has(chars[index] || "")) {
        token += chars[index];
        index += 1;
      }
      tokens.push(token);
      continue;
    }
    const piece = pendingOpen + char;
    pendingOpen = "";
    if (tokens.length > 0 && CLOSER.has(char)) tokens[tokens.length - 1] += piece;
    else tokens.push(piece);
    index += 1;
  }
  if (pendingOpen && tokens.length > 0) tokens[tokens.length - 1] += pendingOpen;
  else if (pendingOpen) tokens.push(pendingOpen);
  return tokens;
}
