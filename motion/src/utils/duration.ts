export const DEFAULT_FPS = 30;
export const MAX_SCENE_FRAMES = DEFAULT_FPS * 60;

export function tryFramesFromSeconds(seconds: number, fps = DEFAULT_FPS): number | undefined {
  if (!Number.isFinite(seconds) || seconds <= 0 || !Number.isFinite(fps) || fps <= 0) return undefined;
  const frames = Math.round(seconds * fps);
  if (frames < 1) return undefined;
  return frames;
}

export function framesFromSeconds(seconds: number, fps = DEFAULT_FPS): number {
  const frames = tryFramesFromSeconds(seconds, fps);
  if (frames == null) throw new Error("seconds must convert to at least one frame");
  return frames;
}

export function secondsFromFrames(frames: number, fps = DEFAULT_FPS): number {
  if (!Number.isFinite(frames) || !Number.isFinite(fps) || fps <= 0) {
    throw new Error("frames and fps must be finite");
  }
  return frames / fps;
}

export function sumDurationFrames(frames: readonly number[]): number {
  return frames.reduce((total, frame) => {
    if (!Number.isInteger(frame) || frame < 1) {
      throw new Error("duration frames must be positive integers");
    }
    return total + frame;
  }, 0);
}
