import { primaryConceptTrigger } from "./match";
import type { SyncedConceptTrigger } from "./schema";

export type CaptionWindow = {
  from: number;
  duration: number;
  text: string;
  emphasis?: string[];
};

/**
 * Map each caption window to at most one concept viz.
 * Prefer longer/more specific phrase hits. Skip empty windows.
 */
export function syncConceptTriggers(
  captions: readonly CaptionWindow[],
  scale = 1,
): SyncedConceptTrigger[] {
  const synced: SyncedConceptTrigger[] = [];
  for (const row of captions) {
    const hit = primaryConceptTrigger(row.text);
    if (!hit) continue;
    synced.push({
      ...hit,
      fromFrame: Math.round(row.from * scale),
      durationInFrames: Math.max(1, Math.round(row.duration * scale)),
      captionText: row.text,
      labels: row.emphasis,
    });
  }
  return synced;
}
