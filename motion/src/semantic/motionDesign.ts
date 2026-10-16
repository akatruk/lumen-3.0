/**
 * Shared presentation math for the timeline and the range.
 * Labels and endpoints stay the payload strings. Nothing here names a step
 * or invents a unit, a midpoint, or a percentage.
 */

export function isSpatialProfile(value: string | undefined | null): boolean {
  return value === "spatial_v1";
}

export function timelineRows(labels: readonly string[]): string[] {
  return labels.map((label) => label.trim()).filter(Boolean).slice(0, 5);
}

export function timelineColumn(boxWidth: number, count: number) {
  const rows = Math.max(1, Math.min(5, count));
  const wide = boxWidth >= 700;
  const rail = 28;
  const gutter = 20;
  const inset = wide ? 48 : 8;
  const labelWidth = Math.max(200, Math.min(wide ? 640 : 400, boxWidth - rail - gutter - inset));
  return {
    wide,
    rows,
    rail,
    gutter,
    inset,
    labelWidth,
    connect: rows >= 2,
    activeHeight: wide ? 96 : 72,
    quietHeight: wide ? 52 : 44,
    occupied: rail + gutter + labelWidth,
  };
}

/** Frame windows for one spoken range. Both ends belong to the same beat. */
export function rangeMotionAt(frame: number): { low: number; span: number; high: number } {
  const span = (value: number, start: number, end: number) => {
    if (value <= start) return 0;
    if (value >= end) return 1;
    return (value - start) / (end - start);
  };
  return {
    low: span(frame, 2, 10),
    span: span(frame, 8, 24),
    high: span(frame, 16, 26),
  };
}
