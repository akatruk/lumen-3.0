export type StepCue = { text: string; start: number };

export type ListScene = {
  sceneComposition?: { speakerPresentation?: string } | null;
  speaker?: { framing?: string };
  typography?: { stepCues?: StepCue[] };
};

/** One line when the column can hold the phrase. Otherwise a balanced break, never a one-character tail. */
export function cardLines(text: string, inner: number, maxSize: number) {
  const chars = [...text];
  const size = Math.min(maxSize, Math.floor(inner / Math.max(chars.length, 1)));
  if (size >= 32 || chars.length < 2) return { size: Math.max(size, 28), lines: [text] };
  let cut = Math.ceil(chars.length / 2);
  if (chars.length - cut < 2) cut = chars.length - 2;
  return { size: 32, lines: [chars.slice(0, cut).join(""), chars.slice(cut).join("")] };
}

/**
 * A one-label scene, then a talking-head gap, then a list: the earlier label
 * stays the category and every cue in the list is a card.
 */
export function heldListCategory(scenes: ListScene[], index: number) {
  const prev = scenes[index - 1];
  const earlier = scenes[index - 2];
  if (!prev || !earlier) return "";
  const prevPresentation = prev.sceneComposition?.speakerPresentation || prev.speaker?.framing || "";
  const earlierCues = earlier.typography?.stepCues || [];
  const ownCues = scenes[index]?.typography?.stepCues || [];
  if (
    (prevPresentation === "fullscreen" || prevPresentation === "speaker") &&
    earlierCues.length === 1 &&
    ownCues.length > 1
  ) {
    return earlierCues[0].text;
  }
  return "";
}
