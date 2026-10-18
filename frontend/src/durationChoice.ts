/** Map a 5-second slider stop onto the source length when the stop is the last one. */
export function chosenDuration(next: number, sourceSeconds: number): number {
  const grid = Math.floor(sourceSeconds / 5) * 5;
  if (next + 0.05 >= sourceSeconds) return sourceSeconds;
  if (next >= grid && sourceSeconds - grid > 0.05) return sourceSeconds;
  return next;
}
