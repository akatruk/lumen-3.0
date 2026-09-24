export const EFFECT_KEYS = ["blur", "glow", "shadow", "color", "speed", "stabilize", "kinetic", "progress", "split", "screen"] as const;
export type EffectKey = (typeof EFFECT_KEYS)[number];
export type LookName = "clean" | "punch" | "soft" | "kinetic" | "split";
export type EffectBoard = { name: LookName; amount: number; effects: Record<EffectKey, boolean> };

const STORAGE = "lumen_effect_board";

function effects(on: EffectKey[]): Record<EffectKey, boolean> {
  return Object.fromEntries(EFFECT_KEYS.map((key) => [key, on.includes(key)])) as Record<EffectKey, boolean>;
}

export const LOOKS: Record<LookName, EffectBoard> = {
  clean: { name: "clean", amount: 1, effects: effects([]) },
  punch: { name: "punch", amount: 1.1, effects: effects(["color", "speed", "stabilize", "kinetic", "progress"]) },
  soft: { name: "soft", amount: 0.9, effects: effects(["blur", "glow", "shadow", "color"]) },
  kinetic: { name: "kinetic", amount: 1.2, effects: effects(["color", "kinetic", "progress", "speed"]) },
  split: { name: "split", amount: 1, effects: effects(["split", "screen", "color", "progress"]) },
};

export function readBoard(): EffectBoard | null {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE) || "null") as EffectBoard | null;
    if (!saved || !LOOKS[saved.name] || typeof saved.amount !== "number" || !saved.effects) return null;
    const amount = Math.min(1.6, Math.max(0.4, saved.amount));
    const next = effects(EFFECT_KEYS.filter((key) => saved.effects[key] === true));
    return { name: saved.name, amount, effects: next };
  } catch {
    return null;
  }
}

export function writeBoard(board: EffectBoard) {
  localStorage.setItem(STORAGE, JSON.stringify(board));
}
