import { CONCEPT_TRIGGER_RULES } from "./presets";
import type { ConceptTriggerHit } from "./schema";

const NUMBER_RE = /(?:^|[^\d])(\d+(?:[.,]\d+)?)(?:\s*%|[^\d]|$)/;
const WORD_NUMBERS: Array<[RegExp, number]> = [
  [/\bthree\b|至少三|三名|三位|\bтри\b/i, 3],
  [/\btwo\b|两名|两位|\bдва\b/i, 2],
  [/\bfour\b|四名|四位|\bчетыре\b/i, 4],
  [/\bfive\b|五名|五位|\bпять\b/i, 5],
];

/** Extract a number the source actually stated. Do not invent. */
export function spokenNumber(text: string): number | undefined {
  const pct = text.match(/(\d+(?:[.,]\d+)?)\s*%/);
  if (pct) {
    const value = Number(pct[1].replace(",", "."));
    if (Number.isFinite(value)) return value;
  }
  const match = text.match(NUMBER_RE);
  if (match) {
    const raw = match[1].replace(",", ".");
    const value = Number(raw);
    if (Number.isFinite(value)) return value;
  }
  for (const [pat, value] of WORD_NUMBERS) {
    if (pat.test(text || "")) return value;
  }
  return undefined;
}

function normalize(text: string): string {
  return text.toLocaleLowerCase("ru-RU");
}

export function matchConceptTriggers(text: string, limit = 3): ConceptTriggerHit[] {
  const hay = normalize(text || "");
  if (!hay.trim()) return [];
  const hits: ConceptTriggerHit[] = [];
  for (const rule of CONCEPT_TRIGGER_RULES) {
    let best: { phrase: string; score: number } | null = null;
    for (const entry of rule.phrases) {
      const needle = normalize(entry.phrase);
      if (!needle || !hay.includes(needle)) continue;
      const score = needle.length / Math.max(hay.length, 1) + needle.length * 0.01;
      if (!best || score > best.score) best = { phrase: entry.phrase, score };
    }
    if (!best) continue;
    const value = rule.valueKey === "spoken_number" ? spokenNumber(text) : undefined;
    hits.push({
      conceptId: rule.conceptId,
      presetId: rule.presetId,
      phrase: best.phrase,
      score: best.score,
      ...(value != null ? { value } : {}),
    });
  }
  hits.sort((a, b) => b.score - a.score || b.phrase.length - a.phrase.length);
  return hits.slice(0, limit);
}

export function primaryConceptTrigger(text: string): ConceptTriggerHit | null {
  return matchConceptTriggers(text, 1)[0] ?? null;
}
