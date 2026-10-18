/**
 * Isolated proof. Not mounted by DirectorV3Preview.
 */
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import type { SupportedLocale } from "../localization/language-config";
import { AutoFitText } from "../typography/AutoFitText";
import { LocaleProvider } from "../typography/locale";
import { theme } from "../themes/tokens";
import { ThreeDecisionLayers } from "./ThreeDecisionLayers";
import { GOLD_CAPTION, GOLD_DURATION, GOLD_FPS, captionAt } from "./threeLayersModel";

export type GoldThreeLayersProps = {
  locale: SupportedLocale;
  speakerFile: string;
};

export const GOLD_THREE_LAYERS_DEFAULTS: GoldThreeLayersProps = {
  locale: "zh-CN",
  speakerFile: "gold/source-excerpt.mp4",
};

export function GoldThreeLayersFilm({ locale, speakerFile }: GoldThreeLayersProps) {
  const frame = useCurrentFrame();
  const seconds = frame / GOLD_FPS;
  const caption = locale === "zh-CN" ? captionAt(seconds) : "";
  return (
    <AbsoluteFill style={{ background: "#141210" }}>
      <OffthreadVideo src={staticFile(speakerFile)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <ThreeDecisionLayers frame={frame} locale={locale} />
      {caption ? (
        <LocaleProvider locale="zh-CN">
          <div
            style={{
              position: "absolute",
              left: GOLD_CAPTION.left,
              top: GOLD_CAPTION.top,
              width: GOLD_CAPTION.width,
              height: GOLD_CAPTION.height,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(20, 18, 16, 0.55)",
              borderRadius: 18,
            }}
          >
            <AutoFitText
              text={caption}
              maxWidth={GOLD_CAPTION.width - 48}
              maxHeight={GOLD_CAPTION.height - 28}
              role={theme.type.caption}
              color="#f7f3ee"
              align="center"
              locale="zh-CN"
            />
          </div>
        </LocaleProvider>
      ) : null}
    </AbsoluteFill>
  );
}

export const GOLD_FRAMES = Math.round(GOLD_DURATION * GOLD_FPS);
