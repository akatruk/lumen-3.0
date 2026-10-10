import type { TimedWord } from "../types/scene";

export function tokenizeWords(text: string): string[] {
  return text.trim().split(/\s+/).filter((word) => word.length > 0);
}

export function wordKey(word: string): string {
  return word.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, "").toLowerCase();
}

export function isEmphasized(word: string, emphasis: readonly string[] | undefined): boolean {
  if (!emphasis || emphasis.length === 0) return false;
  const key = wordKey(word);
  if (!key) return false;
  return emphasis.some((item) => wordKey(item) === key);
}

export function timeWords(text: string, durationInFrames: number): TimedWord[] {
  const tokens = tokenizeWords(text);
  if (tokens.length === 0 || durationInFrames < 1) return [];
  return tokens.map((token, index) => {
    const startFrame = Math.round((durationInFrames * index) / tokens.length);
    const endFrame =
      index === tokens.length - 1
        ? durationInFrames
        : Math.max(startFrame + 1, Math.round((durationInFrames * (index + 1)) / tokens.length));
    return { text: token, startFrame, endFrame };
  });
}
