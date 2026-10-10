import { CONCEPT_TRIGGER_RULES } from "./presets";
import type { ConceptTriggerHit } from "./schema";

const NUMBER_RE = /(?:^|[^\d])(\d+(?:[.,]\d+)?)(?:[^\d]|$)/;

/** Extract a number the source actually stated. Do not invent. */
export function spokenNumber(text: string): number | undefined {
  const match = text.match(NUMBER_RE);
  if (!match) return undefined;
  const raw = match[1].replace(",", ".");
  const value = Number(raw);
  return Number.isFinite(value) ? value : undefined;
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
