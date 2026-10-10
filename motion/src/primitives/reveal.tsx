import { Children, type ReactNode } from "react";
import { tokenizeWords } from "../utils/words";
import { lockedText } from "../typography/lock";
import { FadeIn, MaskReveal, PopIn, SlideIn } from "./entrances";

export function Stagger({
  children,
  interval = 6,
}: {
  children: ReactNode;
  interval?: number;
}) {
  const items = Children.toArray(children);
  return (
    <>
      {items.map((child, index) => (
        <FadeIn key={index} delay={index * interval} duration={12}>
          {child}
        </FadeIn>
      ))}
    </>
  );
}

export function WordReveal({
  text,
  preset = "fade",
  interval = 5,
  delay = 0,
  gapPx = 0,
  colorFor,
  decorate,
  tokens,
}: {
  text: string;
  preset?: "fade" | "pop" | "mask" | "slide";
  interval?: number;
  delay?: number;
  gapPx?: number;
  colorFor?: (word: string) => string | undefined;
  decorate?: (word: string, index: number) => ReactNode;
  tokens?: readonly string[];
}) {
  const words = tokens && tokens.length > 0 ? [...tokens] : tokenizeWords(text);
  return (
    <span style={{ display: "inline-flex", flexWrap: "nowrap", whiteSpace: "nowrap", alignItems: "baseline" }}>
      {words.map((word, index) => {
        const body = (
          <span style={{ ...lockedText, color: colorFor?.(word) }}>{decorate ? decorate(word, index) : word}</span>
        );
        const wordDelay = delay + index * interval;
        const animated =
          preset === "pop" ? (
            <PopIn inline delay={wordDelay}>
              {body}
            </PopIn>
          ) : preset === "mask" ? (
            <MaskReveal inline delay={wordDelay}>
              {body}
            </MaskReveal>
          ) : preset === "slide" ? (
            <SlideIn inline direction="up" delay={wordDelay} distance={18}>
              {body}
            </SlideIn>
          ) : (
            <FadeIn inline delay={wordDelay}>
              {body}
            </FadeIn>
          );
        return (
          <span
            key={`${word}-${index}`}
            style={{
              display: "inline-flex",
              flex: "0 0 auto",
              whiteSpace: "nowrap",
              marginRight: index < words.length - 1 ? gapPx : 0,
            }}
          >
            {animated}
          </span>
        );
      })}
    </span>
  );
}
