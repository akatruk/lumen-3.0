/** A preview still is taken after the entrance has finished, and before any exit. */
export function getPreviewFrame(
  component: { previewFrame?: number },
  durationInFrames: number,
): number {
  const duration = Math.max(1, Math.floor(durationInFrames));
  const preferred =
    component.previewFrame == null ? Math.floor(duration * 0.75) : Math.floor(component.previewFrame);
  return Math.min(duration - 1, Math.max(0, preferred));
}
