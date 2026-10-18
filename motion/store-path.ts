import {existsSync, mkdirSync} from "node:fs";
import path from "node:path";

/** 100GB volume on lumen-fix. Absent on laptops, so local runs keep writing under motion/. */
export const VOLUME_STORE = "/mnt/volume_nyc1_1791446889637/lumen-motion";

export function motionStore(): string {
  const fromEnv = process.env.MOTION_STORE?.trim();
  if (fromEnv) return fromEnv;
  if (existsSync("/mnt/volume_nyc1_1791446889637")) return VOLUME_STORE;
  return path.resolve("output");
}

export function ensureStore(): string {
  const root = motionStore();
  const onVolume = Boolean(process.env.MOTION_STORE?.trim()) || root === VOLUME_STORE;
  if (!onVolume) return root;
  for (const name of ["output", "public", "cache", "preview-frames"]) {
    mkdirSync(path.join(root, name), {recursive: true});
  }
  return root;
}
