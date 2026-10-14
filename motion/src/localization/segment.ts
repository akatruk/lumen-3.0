import type { SupportedLocale } from "./language-config";

const CLOSE_PUNCT = /^[\p{P}\p{S}]+$/u;
const CLOSER = new Set(["，", "。", "！", "？", "、", "；", "：", ",", ".", "!", "?", ":", ";", ")", "]", "」", "』", "）", "》"]);
const OPENER = new Set(["「", "『", "（", "(", "[", "《", "“", "‘"]);

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

/**
 * Line breaking. English and Russian break only on spaces.
 * Chinese breaks on characters, and closing punctuation stays with the previous character.
 * Digit runs and numeric ranges stay whole so 8000 is not painted as 80 / 00.
 */
export function segmentForLineBreak(text: string): string[] {
  const chars = graphemes(text.trim()).filter((char) => char.trim().length > 0 || char === " ");
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
      tokens.push(pendingOpen + number.token);
      pendingOpen = "";
      index = number.next;
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
