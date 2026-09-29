export type PictureStart = "queued" | "unapproved" | "busy" | "missing" | "failed";

export function scenesApproved(clips: { approved?: boolean }[] | undefined) {
  return Array.isArray(clips) && clips.length > 0 && clips.every((clip) => clip.approved !== false);
}

export async function startApprovedPicture(projectId: string, revision: number, qualityReview = true): Promise<PictureStart> {
  const response = await fetch(`/api/studio/projects/${projectId}/manual/render`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ revision, quality_review: qualityReview }),
  });
  if (response.status === 409) return "busy";
  if (response.status === 422) return "unapproved";
  if (!response.ok) return "failed";
  return "queued";
}
