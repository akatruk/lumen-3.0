/**
 * Isolated reference-driven proof. Not mounted by Director.
 */
import { AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import type { SupportedLocale } from "../../localization/language-config";
import { fontFamilyFor } from "../../localization/fonts";
import { AutoFitText } from "../../typography/AutoFitText";
import { LocaleProvider } from "../../typography/locale";
import { theme } from "../../themes/tokens";
import { FamilyStage, familyHandoff, familySpeakerRect, familyStageActive, type FamilyLines } from "./FamilyStage";
import { CostMark, FamilyMark, HouseMark, SchoolMark, StayMark, WorkMark } from "./objects";
import {
  COST_BOX,
  DIMENSION_TITLE,
  FAMILY_BOX,
  GOLD_FPS,
  HERO_BOX,
  V2_CAPTION,
  V2_COPY,
  captionAt,
  costFan,
  dimensionAt,
  enterFrame,
  exitMix,
  familyExtended,
  familyFocus,
  heroAt,
  easeOut,
  heroEnter,
  heroLabel,
  plateOpacity,
  speakerRect,
} from "./model";

const PAPER = "#f3eee6";
const PLATE = "#241e1a";

export type GoldV2Props = {
  locale: SupportedLocale;
  speakerFile: string;
};

export const GOLD_V2_DEFAULTS: GoldV2Props = {
  locale: "zh-CN",
  speakerFile: "gold/source-excerpt.mp4",
};

function familySpeaker(frame: number, fallback: { left: number; top: number; width: number; height: number }) {
  return familySpeakerRect(frame, fallback);
}

function Label({ text, locale, width }: { text: string; locale: SupportedLocale; width: number }) {
  if (!text) return null;
  return (
    <AutoFitText text={text} maxWidth={width} maxHeight={88} role={theme.type.title} color={PAPER} locale={locale} />
  );
}

export function GoldV2Film({ locale, speakerFile }: GoldV2Props) {
  const frame = useCurrentFrame();
  const hero = heroAt(frame);
  const enter = heroEnter(frame);
  const dim = dimensionAt(frame);
  const plate = plateOpacity(frame);
  const exit = exitMix(frame);
  const graphicOpacity = plate * (exit < 0.8 ? 1 : (1 - exit) / 0.2);
  const graphicShift = exit * -220;
  const speaker = speakerRect(frame);
  const focus = familyFocus(frame);
  const copy = V2_COPY[locale];
  const title =
    dim === 0 ? copy.kicker : DIMENSION_TITLE[locale][dim - 1];
  const caption = locale === "zh-CN" ? captionAt(frame / GOLD_FPS) : "";
  const label = heroLabel(locale, hero, focus);
  const heroBox = hero === "family" ? FAMILY_BOX : hero === "cost" ? COST_BOX : HERO_BOX;
  const radius = dim === 0 ? 0 : 28;
  const familyCut = familyStageActive(frame);
  const handoff = familyCut ? familyHandoff(frame) : 1;
  const familyStart = enterFrame(16.52);
  const speakerHeld = familySpeaker(frame, speaker);
  const stayExit = frame >= familyStart && frame < familyStart + 12
    ? 1 - easeOut((frame - familyStart) / 12)
    : 0;

  return (
    <AbsoluteFill style={{ background: "#14110f", fontFamily: fontFamilyFor(locale) }}>
      <AbsoluteFill style={{ background: PLATE, opacity: plate }} />
      <div
        style={{
          position: "absolute",
          left: speakerHeld.left,
          top: speakerHeld.top,
          width: speakerHeld.width,
          height: speakerHeld.height,
          overflow: "hidden",
          borderRadius: radius,
          boxShadow: dim === 0 ? "none" : "0 16px 40px rgba(0,0,0,0.35)",
          outline: dim === 0 ? "none" : "2px solid rgba(243,238,230,0.35)",
          zIndex: familyCut ? 5 : 2,
        }}
      >
        <OffthreadVideo
          src={staticFile(speakerFile)}
          style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center 22%" }}
        />
      </div>
      {plate > 0.02 ? (
        <LocaleProvider locale={locale}>
          <div
            style={{
              position: "absolute",
              left: heroBox.left,
              top: dim === 3 ? 96 : 48,
              width: heroBox.width,
              opacity: graphicOpacity * (hero === "family" && familyCut ? 0 : 1),
              transform: `translateY(${graphicShift}px)`,
              zIndex: 3,
            }}
          >
            <AutoFitText
              text={title}
              maxWidth={heroBox.width}
              maxHeight={84}
              role={theme.type.title}
              color={PAPER}
              locale={locale}
            />
          </div>
          <div
            style={{
              position: "absolute",
              left: heroBox.left,
              top: dim === 2 ? 200 : 360,
              width: heroBox.width,
              height: dim === 2 ? 980 : 860,
              opacity: graphicOpacity * (hero === "none" ? 0 : enter) * (hero === "family" && familyCut ? 0 : 1),
              transform: `translateY(${(1 - enter) * 28 + graphicShift}px)`,
              zIndex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              gap: 12,
            }}
          >
            {hero === "house" ? <div style={{ height: 640 }}><HouseMark /></div> : null}
            {hero === "work" ? <div style={{ height: 560 }}><WorkMark /></div> : null}
            {hero === "school" ? <div style={{ height: 560 }}><SchoolMark /></div> : null}
            {hero === "stay" ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                <Label text={copy.few} locale={locale} width={heroBox.width} />
                <div style={{ height: 360 }}>
                  <StayMark />
                </div>
                <Label text={copy.long} locale={locale} width={heroBox.width} />
              </div>
            ) : null}
            {hero === "family" ? <FamilyMark extended={familyExtended(frame)} focus={focus} /> : null}
            {hero === "cost" ? (
              <CostMark
                fan={costFan(frame)}
                fee={
                  <AutoFitText
                    text={copy.fee}
                    maxWidth={360}
                    maxHeight={72}
                    role={theme.type.title}
                    color="#1c1612"
                    locale={locale}
                  />
                }
              />
            ) : null}
          </div>
          {stayExit > 0.02 ? (
            <div
              style={{
                position: "absolute",
                left: 640,
                top: 430,
                width: 360,
                height: 280,
                opacity: stayExit,
                zIndex: 1,
              }}
            >
              <StayMark />
            </div>
          ) : null}
          {familyCut ? (
            <div style={{ position: "absolute", inset: 0, opacity: 1 - handoff, zIndex: 1 }}>
              <FamilyStage
                frame={frame}
                locale={locale}
                lines={{
                  title: DIMENSION_TITLE[locale][1],
                  core: copy.spouse,
                  household: copy.household,
                  parents: copy.parents,
                } satisfies FamilyLines}
              />
            </div>
          ) : null}
          {hero !== "none" && hero !== "stay" && hero !== "cost" ? (
            <div
              style={{
                position: "absolute",
                left: heroBox.left,
                top: dim === 2 ? 1200 : 1280,
                width: heroBox.width,
                opacity: graphicOpacity * enter * (hero === "family" && familyCut ? 0 : 1),
                zIndex: 3,
              }}
            >
              <Label text={label} locale={locale} width={heroBox.width} />
            </div>
          ) : null}
        </LocaleProvider>
      ) : null}
      {caption ? (
        <LocaleProvider locale="zh-CN">
          <div
            style={{
              position: "absolute",
              left: V2_CAPTION.left,
              top: V2_CAPTION.top,
              width: V2_CAPTION.width,
              height: V2_CAPTION.height,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "rgba(20,16,14,0.78)",
              borderRadius: 16,
              zIndex: 4,
            }}
          >
            <AutoFitText
              text={caption}
              maxWidth={V2_CAPTION.width - 48}
              maxHeight={V2_CAPTION.height - 28}
              role={theme.type.caption}
              color={PAPER}
              align="center"
              locale="zh-CN"
            />
          </div>
        </LocaleProvider>
      ) : null}
    </AbsoluteFill>
  );
}
