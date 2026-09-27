export type CreatePrompt = "both" | "video" | "reference" | "ready";

/** A reference file counts. Douyin search results are not the only way in. */
export function createPrompt(hasFile: boolean, referenceCount: number, hasReferenceFile: boolean): CreatePrompt {
  const hasReference = referenceCount > 0 || hasReferenceFile;
  if (!hasFile && !hasReference) return "both";
  if (!hasFile) return "video";
  if (!hasReference) return "reference";
  return "ready";
}
