/** step.at is seconds after the spoken origin. Subtract the scene start once. */
export function sceneRevealFrame(stepAt: number, sourceOrigin: number, sceneStart: number, fps: number): number {
  return Math.round((sourceOrigin + stepAt - sceneStart) * fps);
}
