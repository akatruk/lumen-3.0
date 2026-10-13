import { AbsoluteFill, Sequence } from "remotion";
import { theme } from "../themes/tokens";
import type { SupportedLocale } from "../localization/language-config";
import { LocaleProvider } from "../typography/locale";
import { SemanticMotion } from "./SemanticMotion";
import { galleryShots, SHOT_FRAMES, type GalleryLocale } from "./galleryScript";

export const GALLERY_FRAMES = 15 * SHOT_FRAMES;

export function SemanticMotionV14Gallery({ locale = "en-US" }: { locale?: GalleryLocale | SupportedLocale }) {
  const loc = (locale.startsWith("zh") ? "zh-CN" : locale.startsWith("ru") ? "ru-RU" : "en-US") as GalleryLocale;
  const shots = galleryShots(loc);
  return (
    <LocaleProvider locale={loc}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        {shots.map((shot, index) => (
          <Sequence key={`${shot.componentId}-${shot.layout}-${index}`} from={index * SHOT_FRAMES} durationInFrames={SHOT_FRAMES} name={`${shot.visualIntent}-${shot.layout}`}>
            <AbsoluteFill style={{ background: shot.layout === "full_frame" ? "#0F1720" : "#C4B6A2" }}>
              <SemanticMotion payload={shot} frames={SHOT_FRAMES} />
            </AbsoluteFill>
          </Sequence>
        ))}
      </AbsoluteFill>
    </LocaleProvider>
  );
}
