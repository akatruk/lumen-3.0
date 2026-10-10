import type { CSSProperties } from "react";

/** A painted word never wraps, hyphenates, or breaks. */
export const lockedText: CSSProperties = {
  whiteSpace: "nowrap",
  wordBreak: "keep-all",
  overflowWrap: "normal",
  hyphens: "none",
  WebkitHyphens: "none",
  display: "inline-block",
  flex: "0 0 auto",
};
