import { useMemo, type ReactNode } from "react";
import type { SupportedLocale } from "../localization/language-config";
import { fontFamilyFor } from "../localization/fonts";
import { theme, type TypeRole } from "../themes/tokens";
import { measureForRender } from "../utils/measure";
import { isEmphasized } from "../utils/words";
import { WordReveal } from "../primitives/reveal";
import { fitPhrase } from "./fitPhrase";
import { lockedText } from "./lock";
import { useLocale } from "./locale";

export function AutoFitText({
  text,
  maxWidth,
  maxHeight,
  role,
  color = theme.color.ink,
  align = "left",
  vertical = "center",
  emphasis,
  animate = "none",
  interval = 5,
  wrapMode = "auto",
  decorate,
  locale: localeProp,
  maxLines,
}: {
  text: string;
  maxWidth: number;
  maxHeight: number;
  role: TypeRole;
  color?: string;
  align?: "left" | "center" | "right";
  vertical?: "start" | "center" | "end";
  emphasis?: readonly string[];
  animate?: "none" | "fade" | "pop" | "mask" | "slide";
  interval?: number;
  wrapMode?: "auto" | "word";
  decorate?: (word: string, index: number) => ReactNode;
  locale?: SupportedLocale;
  maxLines?: number;
}) {
  const locale = localeProp ?? useLocale();
  const family = fontFamilyFor(locale);
  const layout = useMemo(
    () =>
      fitPhrase({
        text,
        maxWidth: Math.max(1, maxWidth - 8),
        maxHeight: Math.max(1, maxHeight - 4),
        role,
        wrapMode,
        locale,
        maxLines,
        measure: (value, size) => measureForRender(value, size, family, role.weight, role.tracking),
      }),
    [text, maxWidth, maxHeight, role, wrapMode, locale, maxLines, family],
  );

  const justify = align === "center" ? "center" : align === "right" ? "flex-end" : "flex-start";
  const verticalAlign = vertical === "end" ? "flex-end" : vertical === "start" ? "flex-start" : "center";
  const origin = align === "center" ? "center center" : align === "right" ? "right center" : "left center";
  let offset = 0;

  return (
    <div
      data-fit-overflow={layout.overflow ? "true" : "false"}
      data-font-size={layout.fontSize}
      style={{
        width: maxWidth,
        height: maxHeight,
        display: "flex",
        alignItems: verticalAlign,
        justifyContent: justify,
        overflow: "visible",
      }}
    >
      <div
        style={
          layout.fitScale < 0.999
            ? { transform: `scale(${layout.fitScale})`, transformOrigin: origin }
            : undefined
        }
      >
        <div style={{ display: "flex", flexDirection: "column", alignItems: justify }}>
          {layout.lines.map((words, lineIndex) => {
            const lineOffset = offset;
            offset += words.length;
            const lineStyle = {
              display: "flex",
              flexWrap: "nowrap" as const,
              whiteSpace: "nowrap" as const,
              justifyContent: justify,
              fontFamily: family,
              fontSize: layout.fontSize,
              fontWeight: role.weight,
              letterSpacing: `${role.tracking}em`,
              lineHeight: role.lineHeight,
              color,
            };
            if (animate !== "none") {
              return (
                <div key={lineIndex} style={lineStyle}>
                  <WordReveal
                    text={words.join(layout.spaceWidth > 0 ? " " : "")}
                    tokens={layout.spaceWidth > 0 ? undefined : words}
                    preset={animate}
                    interval={interval}
                    delay={lineOffset * interval}
                    gapPx={layout.spaceWidth}
                    colorFor={(word) => (isEmphasized(word, emphasis) ? theme.color.accent : undefined)}
                    decorate={decorate ? (word, index) => decorate(word, lineOffset + index) : undefined}
                  />
                </div>
              );
            }
            return (
              <div key={lineIndex} style={lineStyle}>
                {words.map((word, wordIndex) => (
                  <span
                    key={`${word}-${wordIndex}`}
                    style={{
                      ...lockedText,
                      marginRight: wordIndex < words.length - 1 ? layout.spaceWidth : 0,
                      color: isEmphasized(word, emphasis) ? theme.color.accent : color,
                    }}
                  >
                    {decorate ? decorate(word, lineOffset + wordIndex) : word}
                  </span>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
