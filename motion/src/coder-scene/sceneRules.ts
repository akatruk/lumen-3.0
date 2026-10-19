// Reusable readability rules for the experimental coder scene.
// Clip text and timings stay in fragment.ts.
export const CJK_FONT = '"Noto Sans CJK SC", "PingFang SC", "Hiragino Sans GB", sans-serif';

export type BoardMetrics = {
  padX: number;
  padY: number;
  gap: number;
  slotHeight: number;
  categoryWidth: number;
  documentWidth: number;
  categoryHeight: number;
  documentHeight: number;
  categoryFont: number;
  documentFont: number;
  activeScale: number;
};

export function boardMetrics(width: number, height: number, groupSize: number): BoardMetrics {
  const count = Math.max(1, groupSize);
  const padX = Math.round(width * 0.04);
  const padY = Math.round(height * 0.035);
  const gap = Math.round(height * 0.022);
  const slotHeight = (height - padY * 2 - gap * (count - 1)) / count;
  const activeScale = 1.06;
  const categoryWidth = Math.floor((width - padX * 2) / activeScale);
  const documentWidth = Math.floor(categoryWidth * 0.9);
  const categoryHeight = Math.floor(slotHeight * 0.78);
  const documentHeight = Math.floor(slotHeight * 0.7);
  const categoryFont = Math.min(64, Math.floor(categoryHeight * 0.34));
  const documentFont = Math.min(56, Math.floor(documentHeight * 0.36));
  return {
    padX,
    padY,
    gap,
    slotHeight,
    categoryWidth,
    documentWidth,
    categoryHeight,
    documentHeight,
    categoryFont,
    documentFont,
    activeScale,
  };
}

export function slotTop(metrics: BoardMetrics, index: number): number {
  return metrics.padY + index * (metrics.slotHeight + metrics.gap);
}

export type FittedLabel = {
  fontSize: number;
  lines: string[];
  overflow: boolean;
};

/** Keep the supplied names intact. Two lines is the maximum. */
export function fitLabel(
  text: string,
  innerWidth: number,
  preferredFont: number,
  minFont = 28,
  protectedLabels: readonly string[] = [],
): FittedLabel {
  const tokens = tokenize(text, protectedLabels);
  let fontSize = preferredFont;
  while (fontSize >= minFont) {
    const lines = wrapTokens(tokens, innerWidth, fontSize);
    if (lines && lines.length <= 2 && lines.every((line) => line.length * fontSize <= innerWidth + 1)) {
      return {fontSize, lines, overflow: false};
    }
    fontSize -= 2;
  }
  const fallback = wrapTokens(tokens, innerWidth, minFont) ?? [text];
  const lines = fallback.slice(0, 2);
  return {fontSize: minFont, lines, overflow: lines.join('') !== text};
}

function tokenize(text: string, protectedLabels: readonly string[]): string[] {
  const labels = [...protectedLabels].filter(Boolean).sort((a, b) => b.length - a.length);
  const tokens: string[] = [];
  let rest = text;
  while (rest.length) {
    const hit = labels.find((label) => rest.startsWith(label));
    if (hit) {
      tokens.push(hit);
      rest = rest.slice(hit.length);
      continue;
    }
    tokens.push(rest[0]);
    rest = rest.slice(1);
  }
  return tokens;
}

function wrapTokens(tokens: string[], innerWidth: number, fontSize: number): string[] | null {
  const lines: string[] = [];
  let current = '';
  for (const token of tokens) {
    if (token.length * fontSize > innerWidth) return null;
    const next = current + token;
    if (next.length * fontSize <= innerWidth) {
      current = next;
      continue;
    }
    if (!current) return null;
    lines.push(current);
    current = token;
  }
  if (current) lines.push(current);
  return lines;
}

export function captionFont(text: string, width: number, height: number): number {
  const lines = text.split('\n');
  const longest = Math.max(...lines.map((line) => line.length), 1);
  const byWidth = Math.floor((width * 0.92) / longest);
  const byHeight = Math.floor(height / (lines.length * 1.25));
  return Math.max(42, Math.min(72, byWidth, byHeight));
}
