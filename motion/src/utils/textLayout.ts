import { segmentForLineBreak, segmentTextForMotion } from "../localization/segment";
import type { SupportedLocale } from "../localization/language-config";
import { tokenizeWords } from "./words";

export type Measure = (text: string, fontSize: number) => number;

export type TextLayout = {
  fontSize: number;
  lines: string[][];
  spaceWidth: number;
  lineHeightPx: number;
  blockWidth: number;
  blockHeight: number;
  overflow: boolean;
  fitScale: number;
};

export type LayoutInput = {
  text: string;
  maxWidth: number;
  maxHeight: number;
  minFontSize: number;
  maxFontSize: number;
  lineHeight: number;
  measure: Measure;
  wrapMode?: "auto" | "word";
  locale?: SupportedLocale;
  maxLines?: number;
};

function widthOf(text: string, fontSize: number, measure: Measure): number {
  const value = measure(text, fontSize);
  if (!Number.isFinite(value) || value <= 0) {
    return text.length === 0 ? 0 : fontSize * 0.5 * [...text].length;
  }
  return value;
}

function lineWidth(words: readonly string[], fontSize: number, measure: Measure, gap: string): number {
  const space = widthOf(gap, fontSize, measure);
  return words.reduce((sum, word, index) => sum + widthOf(word, fontSize, measure) + (index > 0 ? space : 0), 0);
}

function wrapAuto(words: readonly string[], fontSize: number, maxWidth: number, measure: Measure, gap: string): string[][] {
  const lines: string[][] = [];
  let current: string[] = [];
  for (const word of words) {
    if (current.length === 0) {
      current = [word];
      continue;
    }
    const next = [...current, word];
    if (lineWidth(next, fontSize, measure, gap) <= maxWidth) {
      current = next;
    } else {
      lines.push(current);
      current = [word];
    }
  }
  if (current.length > 0) lines.push(current);
  return lines;
}

function tokensFor(input: LayoutInput): { tokens: string[]; gap: string } {
  if (input.locale === "zh-CN") {
    const tokens = input.wrapMode === "word" ? segmentTextForMotion(input.text, "zh-CN") : segmentForLineBreak(input.text);
    return { tokens, gap: "" };
  }
  return { tokens: tokenizeWords(input.text), gap: " " };
}

type Attempt = {
  lines: string[][];
  fits: boolean;
  spaceWidth: number;
  blockWidth: number;
  blockHeight: number;
};

function attemptAt(input: LayoutInput, fontSize: number, words: readonly string[], gap: string): Attempt {
  const spaceWidth = widthOf(gap, fontSize, input.measure);
  const lines =
    words.length === 0
      ? []
      : input.wrapMode === "word"
        ? words.map((word) => [word])
        : wrapAuto(words, fontSize, input.maxWidth, input.measure, gap);
  if (lines.length === 0) {
    return { lines, fits: true, spaceWidth, blockWidth: 0, blockHeight: 0 };
  }
  const widths = lines.map((line) => lineWidth(line, fontSize, input.measure, gap));
  const blockWidth = Math.max(...widths);
  const lineHeightPx = fontSize * input.lineHeight;
  const blockHeight = lines.length * lineHeightPx;
  const withinLines = input.maxLines == null || lines.length <= input.maxLines;
  const fits = withinLines && blockWidth <= input.maxWidth + 0.01 && blockHeight <= input.maxHeight + 0.01;
  return { lines, fits, spaceWidth, blockWidth, blockHeight };
}

function scaleToFit(blockWidth: number, blockHeight: number, maxWidth: number, maxHeight: number): number {
  const scale = Math.min(maxWidth / Math.max(blockWidth, 1), maxHeight / Math.max(blockHeight, 1));
  if (!Number.isFinite(scale)) return 0.01;
  return Math.max(0.01, Math.min(1, scale));
}

export function layoutText(input: LayoutInput): TextLayout {
  const { tokens: words, gap } = tokensFor(input);
  const minFont = Math.max(1, Math.round(Math.min(input.minFontSize, input.maxFontSize)));
  const maxFont = Math.max(minFont, Math.round(Math.max(input.minFontSize, input.maxFontSize)));
  const empty = (): TextLayout => ({
    fontSize: maxFont,
    lines: [],
    spaceWidth: 0,
    lineHeightPx: maxFont * input.lineHeight,
    blockWidth: 0,
    blockHeight: 0,
    overflow: false,
    fitScale: 1,
  });
  if (words.length === 0) return empty();

  if (!(input.maxWidth > 0) || !(input.maxHeight > 0)) {
    const fallen = attemptAt(input, minFont, words, gap);
    return {
      fontSize: minFont,
      lines: fallen.lines,
      spaceWidth: fallen.spaceWidth,
      lineHeightPx: minFont * input.lineHeight,
      blockWidth: fallen.blockWidth,
      blockHeight: fallen.blockHeight,
      overflow: true,
      fitScale: 0.01,
    };
  }

  let low = minFont;
  let high = maxFont;
  let best: Attempt | null = null;
  let bestSize = minFont;
  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const attempt = attemptAt(input, mid, words, gap);
    if (attempt.fits) {
      best = attempt;
      bestSize = mid;
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  if (best) {
    return {
      fontSize: bestSize,
      lines: best.lines,
      spaceWidth: best.spaceWidth,
      lineHeightPx: bestSize * input.lineHeight,
      blockWidth: best.blockWidth,
      blockHeight: best.blockHeight,
      overflow: false,
      fitScale: 1,
    };
  }

  const fallen = attemptAt(input, minFont, words, gap);
  const fitScale = scaleToFit(fallen.blockWidth, fallen.blockHeight, input.maxWidth, input.maxHeight);
  return {
    fontSize: minFont,
    lines: fallen.lines,
    spaceWidth: fallen.spaceWidth,
    lineHeightPx: minFont * input.lineHeight,
    blockWidth: fallen.blockWidth,
    blockHeight: fallen.blockHeight,
    overflow: fitScale < 0.999,
    fitScale,
  };
}
