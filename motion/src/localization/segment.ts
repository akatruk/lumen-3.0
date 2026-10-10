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

/**
 * Line breaking. English and Russian break only on spaces.
 * Chinese breaks on characters, and closing punctuation stays with the previous character.
 */
export function segmentForLineBreak(text: string): string[] {
  const chars = graphemes(text.trim()).filter((char) => char.trim().length > 0 || char === " ");
  const tokens: string[] = [];
  let pendingOpen = "";
  for (const char of chars) {
    if (char === " ") continue;
    if (OPENER.has(char)) {
      pendingOpen += char;
      continue;
    }
    const piece = pendingOpen + char;
    pendingOpen = "";
    if (tokens.length > 0 && CLOSER.has(char)) tokens[tokens.length - 1] += piece;
    else tokens.push(piece);
  }
  if (pendingOpen && tokens.length > 0) tokens[tokens.length - 1] += pendingOpen;
  else if (pendingOpen) tokens.push(pendingOpen);
  return tokens;
}
