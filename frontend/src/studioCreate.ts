export type CreatePrompt = "both" | "video" | "reference" | "ready";

/** Owned footage is enough. References stay optional. */
export function createPrompt(hasFile: boolean, referenceCount: number, hasReferenceFile: boolean): CreatePrompt {
  if (hasFile) return "ready";
  if (referenceCount > 0 || hasReferenceFile) return "video";
  return "both";
}

/** File stem, trimmed, capped at the API title limit. Unicode names stay intact. */
export function projectTitleFromFile(name: string): string {
  const stem = name.replace(/\.[^.]+$/, "").replace(/[/\\]/g, "").trim();
  return (stem || "Untitled video").slice(0, 120);
}
