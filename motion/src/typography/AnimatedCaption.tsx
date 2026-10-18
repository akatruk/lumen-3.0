import type { ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { FadeIn, Highlight, ScaleIn } from "../primitives";
import { theme, type TypeRole } from "../themes/tokens";
import type { CaptionVariant, TimedWord } from "../types/scene";
import { timeWords } from "../utils/words";
import { AutoFitText } from "./AutoFitText";

function roleFor(variant: CaptionVariant): TypeRole {
  if (variant === "minimal") return theme.type.captionQuiet;
  if (variant === "impact") return theme.type.hook;
  return theme.type.caption;
}

export function AnimatedCaption({
  text,
  words,
  variant,
  maxWidth,
  maxHeight,
  align = "center",
  vertical = "center",
  durationInFrames,
  tone = "light",
}: {
  text: string;
  words?: TimedWord[];
  variant: CaptionVariant;
  maxWidth: number;
  maxHeight: number;
  align?: "left" | "center" | "right";
  vertical?: "start" | "center" | "end";
  durationInFrames: number;
  tone?: "light" | "dark";
}) {
  const frame = useCurrentFrame();
  const timings = words && words.length > 0 ? words : timeWords(text, durationInFrames);
  const active = timings.findIndex((word) => frame >= word.startFrame && frame < word.endFrame);
  const settled = timings.length > 0 && frame >= timings[timings.length - 1].endFrame - 1;
  const role = roleFor(variant);
  const ink = tone === "dark" ? theme.color.paperInk : theme.color.ink;
  const quiet = tone === "dark" ? theme.color.accentInk : theme.color.muted;
  const shared = { text, maxWidth, maxHeight, align, vertical, role };

  if (variant === "impact") {
    return (
      <ScaleIn>
        <AutoFitText {...shared} color={ink} animate="none" />
      </ScaleIn>
    );
  }
  if (variant === "minimal") {
    return (
      <FadeIn duration={16}>
        <AutoFitText {...shared} color={quiet} animate="none" />
      </FadeIn>
    );
  }
  if (variant === "clean") {
    return <AutoFitText {...shared} color={ink} animate="fade" interval={4} />;
  }

  const decorate = (word: string, index: number): ReactNode => {
    const on = settled || active === -1 ? frame >= (timings[0]?.startFrame ?? 0) : index <= active;
    if (variant === "karaoke") {
      return <span style={{ color: on ? ink : quiet }}>{word}</span>;
    }
    if (index === active) return <Highlight delay={timings[index]?.startFrame ?? 0}>{word}</Highlight>;
    return <span style={{ color: on ? ink : quiet }}>{word}</span>;
  };

  return <AutoFitText {...shared} color={ink} animate="none" decorate={decorate} />;
}
