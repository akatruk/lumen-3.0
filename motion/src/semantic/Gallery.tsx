import { AbsoluteFill, Sequence } from "remotion";
import { theme } from "../themes/tokens";
import type { SupportedLocale } from "../localization/language-config";
import { LocaleProvider } from "../typography/locale";
import { SemanticMotion } from "./SemanticMotion";
import { galleryShots, SHOT_FRAMES, type GalleryLocale } from "./galleryScript";
import { galleryShotsV15 } from "./galleryV15";
import type { SemanticMotionPayload } from "./types";

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

function asV18(shot: SemanticMotionPayload): SemanticMotionPayload {
  return { ...shot, version: "v18", columnScrim: false };
}

export const V18_GALLERY_FRAMES = 45 * SHOT_FRAMES;
export const V18_LOCALE_FRAMES = 15 * SHOT_FRAMES;

export function v18Shots(locale: GalleryLocale, representative: boolean): SemanticMotionPayload[] {
  const all = [...galleryShots(locale), ...galleryShotsV15(locale)].map(asV18);
  if (!representative) return all;
  const seen = new Set<string>();
  return all.filter((shot) => {
    if (shot.layout !== "overlay") return false;
    if (seen.has(shot.visualIntent)) return false;
    seen.add(shot.visualIntent);
    return true;
  });
}

export function SemanticMotionV18Gallery({
  locale = "en-US",
  representative = false,
}: {
  locale?: GalleryLocale | SupportedLocale;
  representative?: boolean;
}) {
  const loc = (locale.startsWith("zh") ? "zh-CN" : locale.startsWith("ru") ? "ru-RU" : "en-US") as GalleryLocale;
  const shots = v18Shots(loc, representative);
  return (
    <LocaleProvider locale={loc}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        {shots.map((shot, index) => (
          <Sequence key={`${shot.componentId}-${shot.layout}-${index}`} from={index * SHOT_FRAMES} durationInFrames={SHOT_FRAMES} name={`${shot.visualIntent}-${shot.layout}`}>
            <AbsoluteFill style={{ background: shot.layout === "full_frame" ? "#1C1917" : "#C4B6A2" }}>
              <SemanticMotion payload={shot} frames={SHOT_FRAMES} />
            </AbsoluteFill>
          </Sequence>
        ))}
      </AbsoluteFill>
    </LocaleProvider>
  );
}

export function SemanticMotionV15Gallery({ locale = "en-US" }: { locale?: GalleryLocale | SupportedLocale }) {
  const loc = (locale.startsWith("zh") ? "zh-CN" : locale.startsWith("ru") ? "ru-RU" : "en-US") as GalleryLocale;
  const shots = galleryShotsV15(loc);
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
