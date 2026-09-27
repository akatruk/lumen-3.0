export const EFFECT_KEYS = ["blur", "glow", "shadow", "color", "speed", "stabilize", "kinetic", "progress", "split", "screen"] as const;
export type EffectKey = (typeof EFFECT_KEYS)[number];
export type LookName = "clean" | "punch" | "soft" | "kinetic" | "split";
export type EffectBoard = { name: LookName; amount: number; effects: Record<EffectKey, boolean> };

const STORAGE = "lumen_effect_board";

function effects(on: EffectKey[]): Record<EffectKey, boolean> {
  return Object.fromEntries(EFFECT_KEYS.map((key) => [key, on.includes(key)])) as Record<EffectKey, boolean>;
}

export const EFFECT_GROUPS: { id: "look" | "light" | "motion" | "graphics"; keys: EffectKey[] }[] = [
  { id: "look", keys: ["color"] },
  { id: "light", keys: ["blur", "glow", "shadow"] },
  { id: "motion", keys: ["speed", "stabilize"] },
  { id: "graphics", keys: ["kinetic", "progress", "split", "screen"] },
];

/** Slider 0–100 mapped onto the 0.4–1.6 strength the style match already applies. */
export function strengthPercent(amount: number): number {
  const clamped = Math.min(1.6, Math.max(0.4, amount));
  return Math.round(((clamped - 0.4) / 1.2) * 100);
}

export function strengthAmount(percent: number): number {
  const p = Math.min(100, Math.max(0, Math.round(percent)));
  return Math.round((0.4 + (p / 100) * 1.2) * 1000) / 1000;
}

export const LOOKS: Record<LookName, EffectBoard> = {
  clean: { name: "clean", amount: 1, effects: effects([]) },
  punch: { name: "punch", amount: 1.1, effects: effects(["color", "speed", "stabilize", "kinetic", "progress"]) },
  soft: { name: "soft", amount: 0.9, effects: effects(["blur", "glow", "shadow", "color"]) },
  kinetic: { name: "kinetic", amount: 1.2, effects: effects(["color", "kinetic", "progress", "speed"]) },
  split: { name: "split", amount: 1, effects: effects(["split", "screen", "color", "progress"]) },
};

export function parseBoard(saved: EffectBoard | null): EffectBoard | null {
  if (!saved || !LOOKS[saved.name] || typeof saved.amount !== "number" || !saved.effects) return null;
  const amount = Math.min(1.6, Math.max(0.4, saved.amount));
  const next = effects(EFFECT_KEYS.filter((key) => saved.effects[key] === true));
  return { name: saved.name, amount, effects: next };
}

export function lookProjectId(): string | null {
  try {
    const back = sessionStorage.getItem("lumen-look-return") || "";
    return /^project\/[a-f0-9]{32}$/.test(back) ? back.slice(8) : null;
  } catch {
    return null;
  }
}

export function readBoard(): EffectBoard | null {
  try {
    return parseBoard(JSON.parse(localStorage.getItem(STORAGE) || "null") as EffectBoard | null);
  } catch {
    return null;
  }
}

export function writeBoard(board: EffectBoard) {
  localStorage.setItem(STORAGE, JSON.stringify(board));
}
