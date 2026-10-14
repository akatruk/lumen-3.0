/**
 * Premium motion tokens. Color and type come from the shared theme.
 * Durations are frame counts at 30fps — deterministic, no wall clock.
 */
export const motionDuration = {
  fadeIn: 12,
  stagger: 8,
  draw: 16,
  travel: 22,
  settle: 10,
  hold: 36,
  exit: 12,
} as const;

export const motionEase = "cubicOut" as const;

/** Minimum contrast role: connectors never stay on a fixed gold. */
export const connectorRole = {
  preferred: "accent",
  minContrast: 3,
} as const;
