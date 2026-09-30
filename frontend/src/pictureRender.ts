export type PictureStart = "queued" | "unapproved" | "busy" | "missing" | "failed";

let animationFlush: (() => Promise<number | null>) | null = null;

export function registerAnimationFlush(fn: (() => Promise<number | null>) | null) {
  animationFlush = fn;
}

export async function flushAnimationEdit(): Promise<number | null> {
  return animationFlush ? animationFlush() : null;
}

export function scenesApproved(clips: { approved?: boolean }[] | undefined) {
  return Array.isArray(clips) && clips.length > 0 && clips.every((clip) => clip.approved !== false);
}

export async function startApprovedPicture(projectId: string, revision: number, qualityReview = true): Promise<PictureStart> {
  const flushed = await flushAnimationEdit();
  const response = await fetch(`/api/studio/projects/${projectId}/manual/render`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision: flushed ?? revision, quality_review: qualityReview }),
  });
  if (response.status === 409) return "busy";
  if (response.status === 422) return "unapproved";
  if (!response.ok) return "failed";
  return "queued";
}
