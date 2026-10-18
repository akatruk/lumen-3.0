/**
 * One editorial sequence. Not mounted by Director.
 */
import { AbsoluteFill, Img, OffthreadVideo, staticFile, useCurrentFrame } from "remotion";
import type { SupportedLocale } from "../../localization/language-config";
import { fontFamilyFor } from "../../localization/fonts";
import { AutoFitText } from "../../typography/AutoFitText";
import { theme } from "../../themes/tokens";
import { CostMark } from "../v2/objects";
import { captionAt } from "../threeLayersModel";
import {
  ACCENT,
  CAPTION_BAND,
  GROUND,
  INK,
  PAPER,
  PLATES,
  STORY_START_FRAME,
  clusterLabel,
  documentBox,
  documentOpacity,
  familyOpacity,
  familyPoses,
  graphicLabel,
  photoOpacity,
  rise,
  speakerBox,
  storyExcerpt,
  type PlateId,
} from "./editorialModel";

export type EditorialProofProps = {
  locale: SupportedLocale;
  speakerFile: string;
};

export const EDITORIAL_PROOF_DEFAULTS: EditorialProofProps = {
  locale: "zh-CN",
  speakerFile: "gold/source-excerpt.mp4",
};

function Fit({
  text,
  width,
  height,
  role,
  color,
  locale,
  align = "left",
}: {
  text: string;
  width: number;
  height: number;
  role: typeof theme.type.title;
  color: string;
  locale: SupportedLocale;
  align?: "left" | "center";
}) {
  if (!text) return null;
  return (
    <AutoFitText text={text} maxWidth={width} maxHeight={height} role={role} color={color} align={align} locale={locale} />
  );
}

export function EditorialProof({ locale, speakerFile }: EditorialProofProps) {
  const frame = useCurrentFrame();
  const excerpt = storyExcerpt(frame);
  const speaker = speakerBox(excerpt);
  const caption = locale === "zh-CN" ? captionAt(excerpt) : "";
  const photo = photoOpacity(excerpt);
  const family = familyOpacity(excerpt);
  const doc = documentOpacity(excerpt);
  const poses = familyPoses(excerpt);
  const paper = documentBox(excerpt);
  const concept = locale === "zh-CN" ? graphicLabel(excerpt) : "";
  const headline = rise(excerpt, 16.52, 0.24) * (1 - rise(excerpt, 18.76, 0.2));
  const cost = rise(excerpt, 30.44, 0.22);
  const coreLabel = clusterLabel(excerpt, ["adultA", "adultB"]);
  const extLabel = clusterLabel(excerpt, ["elderA", "elderB"]);
  const hallScale = 1 + 0.03 * rise(excerpt, 20.52, 4);
  const fullSpeaker = speaker.width > 1000;
  const photoScale = 1 + 0.04 * rise(excerpt, 18.76, 1.92);

  return (
    <AbsoluteFill style={{ background: GROUND, fontFamily: fontFamilyFor(locale) }}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: photo,
          overflow: "hidden",
          zIndex: 1,
        }}
      >
        <Img
          src={staticFile("gold/story-proof/people_door_001.png")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center 40%",
            transform: `scale(${photoScale})`,
          }}
        />
      </div>

      <div style={{ position: "absolute", inset: 0, opacity: family, overflow: "hidden", zIndex: 2 }}>
        <Img
          src={staticFile("gold/story-proof/re_int_hall.png")}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "center 18%",
            transform: `scale(${hallScale})`,
          }}
        />
        {(["adultA", "adultB", "elderA", "elderB", "child", "youth"] as PlateId[]).map((id) => {
          const person = poses.find((row) => row.id === id)!;
          return (
            <Img
              key={id}
              src={staticFile(`gold/family-v4/${PLATES[id].file}`)}
              style={{
                position: "absolute",
                left: person.left,
                top: person.top,
                width: person.width,
                height: person.height,
                opacity: person.opacity,
                objectFit: "contain",
              }}
            />
          );
        })}
        <div style={{ position: "absolute", left: coreLabel.left, top: coreLabel.top, width: coreLabel.width, height: coreLabel.height, opacity: rise(excerpt, 20.6, 0.2) }}>
          <Fit text="配偶未成年子女" width={coreLabel.width} height={coreLabel.height} role={theme.type.support} color={INK} locale={locale} align="center" />
        </div>
        <div style={{ position: "absolute", left: extLabel.left, top: extLabel.top, width: extLabel.width, height: extLabel.height, opacity: rise(excerpt, 21.15, 0.24) }}>
          <Fit text="成年子女和父母" width={extLabel.width} height={extLabel.height} role={theme.type.support} color={INK} locale={locale} align="center" />
        </div>
      </div>

      <div style={{ position: "absolute", left: paper.left, top: paper.top, width: paper.width, height: paper.height, opacity: doc * (1 - cost), zIndex: 6 }}>
        <div style={{ width: "100%", height: "100%", background: PAPER, padding: "64px 48px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ width: 96, height: 10, background: ACCENT, marginBottom: 36 }} />
          <Fit text={concept} width={paper.width - 96} height={780} role={theme.type.number} color={INK} locale={locale} align="center" />
        </div>
      </div>

      <div style={{ position: "absolute", left: paper.left, top: paper.top, width: paper.width, height: paper.height, opacity: doc * cost, zIndex: 6, background: PAPER }}>
        <CostMark fan={1} fee={<Fit text={concept} width={paper.width * 0.72} height={420} role={theme.type.number} color={INK} locale={locale} align="center" />} />
      </div>

      <div
        style={{
          position: "absolute",
          left: 64,
          top: 1468,
          width: 900,
          height: 140,
          opacity: headline,
          zIndex: 6,
          textShadow: "0 2px 16px rgba(0,0,0,0.8)",
        }}
      >
        <Fit text={concept} width={900} height={140} role={theme.type.hook} color={PAPER} locale={locale} />
      </div>

      <div
        style={{
          position: "absolute",
          left: speaker.left,
          top: speaker.top,
          width: speaker.width,
          height: speaker.height,
          overflow: "hidden",
          borderRadius: fullSpeaker ? 0 : 28,
          zIndex: 5,
          boxShadow: fullSpeaker ? "none" : "0 16px 40px rgba(0,0,0,0.35)",
          outline: fullSpeaker ? "none" : "2px solid rgba(243,238,230,0.35)",
        }}
      >
        <OffthreadVideo
          src={staticFile(speakerFile)}
          startFrom={STORY_START_FRAME}
          style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center 22%" }}
        />
      </div>

      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 260,
          background: "linear-gradient(to top, rgba(12,8,6,0.78), rgba(12,8,6,0))",
          zIndex: 7,
          pointerEvents: "none",
        }}
      />
      <div style={{ position: "absolute", left: CAPTION_BAND.left, top: CAPTION_BAND.top, width: CAPTION_BAND.width, height: CAPTION_BAND.height, zIndex: 8 }}>
        <Fit text={caption} width={CAPTION_BAND.width} height={CAPTION_BAND.height} role={theme.type.caption} color={PAPER} locale={locale} />
      </div>
    </AbsoluteFill>
  );
}
