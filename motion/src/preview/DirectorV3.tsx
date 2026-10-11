import type { ReactNode } from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { LocaleProvider } from "../typography/locale";
import { AutoFitText } from "../typography/AutoFitText";
import type { SupportedLocale } from "../localization/language-config";
import { normalizeScene } from "../registry/validateScene";
import { renderScene } from "../registry/motionRegistry";
import { ConceptViz, syncConceptTriggers, type SyncedConceptTrigger } from "../concepts";
import { BackgroundPlate, HeroObject, ParallaxLayers } from "../cinematic";
import { PORTRAIT, criteriaCardsFor, splitMediaRect, splitSpeakerRect } from "./portraitLayouts";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const media = (name: string) => staticFile(`director-v3/${name}`);

export const DIRECTOR_V3_FPS = 30;
export const DIRECTOR_V3_FRAMES = 600;
/** Shorter hook → earlier media beat; avoids 0–19s talking-head lock on 60s cuts. */
const BEAT_FRAMES = [54, 168, 120, 132, 81, 45] as const;

export type SceneLook = {
  sceneId: string;
  speaker: { layout: string };
  background: { treatment: string; staged?: string | null };
  foreground: { treatment: string; staged?: string | null; assetId?: string | null };
  typography: { animate?: string };
  transition: string;
  motionIntensity: "low" | "medium" | "high";
};

export type VisualPlan = {
  generationId?: string;
  visualSeed: number;
  artDirection: string;
  scenes: SceneLook[];
  /** When true (default), spoken captions drive concept viz overlays. */
  conceptTriggers?: boolean;
  backgroundPlate?: "ink_lift" | "paper_grain" | "navy_grid" | "gold_veil" | "soft_vignette" | null;
  heroObject?: "passport" | "key" | "globe" | "house" | null;
  language?: SupportedLocale;
};

export type DirectorV3Props = {
  durationSeconds?: number;
  speakerFile?: string;
  visualPlan?: VisualPlan | null;
  locale?: SupportedLocale;
};

const LOOK: SceneLook = {
  sceneId: "hook",
  speaker: { layout: "speaker_fullscreen" },
  background: { treatment: "slow_zoom_in" },
  foreground: { treatment: "scale_reveal" },
  typography: { animate: "fade" },
  transition: "cut",
  motionIntensity: "medium",
};

export function sceneLook(plan: VisualPlan | null | undefined, sceneId: string): SceneLook {
  return plan?.scenes?.find((scene) => scene.sceneId === sceneId) ?? { ...LOOK, sceneId };
}

export function framesForSeconds(seconds: number) {
  const safe = Number.isFinite(seconds) ? seconds : 20;
  return Math.max(DIRECTOR_V3_FPS, Math.round(safe * DIRECTOR_V3_FPS));
}

export function beatsFor(frames: number) {
  let cursor = 0;
  const lengths = BEAT_FRAMES.slice(0, -1).map((weight) => {
    const length = Math.max(1, Math.round((weight / DIRECTOR_V3_FRAMES) * frames));
    cursor += length;
    return length;
  });
  lengths.push(Math.max(1, frames - cursor));
  let from = 0;
  return lengths.map((duration) => {
    const beat = { from, duration };
    from += duration;
    return beat;
  });
}

const CAPTIONS: { from: number; duration: number; text: string; emphasis?: string[] }[] = [
  { from: 0, duration: 66, text: "Планируете переезд", emphasis: ["переезд"] },
  { from: 66, duration: 66, text: "второй вид на жительство", emphasis: ["жительство"] },
  { from: 132, duration: 66, text: "с чего начать?", emphasis: ["начать"] },
  { from: 222, duration: 66, text: "подходящую программу", emphasis: ["программу"] },
  { from: 288, duration: 72, text: "с учетом целей", emphasis: ["целей"] },
  { from: 360, duration: 93, text: "семьи и бюджета", emphasis: ["бюджета"] },
  { from: 474, duration: 54, text: "весь процесс", emphasis: ["процесс"] },
  { from: 528, duration: 72, text: "консультация и программа", emphasis: ["программа"] },
];

function Move({
  treatment,
  intensity,
  frames,
  children,
}: {
  treatment: string;
  intensity: SceneLook["motionIntensity"];
  frames: number;
  children: ReactNode;
}) {
  const frame = useCurrentFrame();
  const span = Math.max(1, frames - 1);
  const gain = intensity === "high" ? 1.4 : intensity === "low" ? 0.55 : 1;
  if (treatment === "gradient_reveal") {
    const opacity = interpolate(frame, [0, Math.min(16, span)], [0.45, 1], clamp);
    return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
  }
  if (treatment === "static_editorial" || treatment === "ambient_loop") {
    return <AbsoluteFill>{children}</AbsoluteFill>;
  }
  if (treatment === "slow_zoom_out") {
    const scale = interpolate(frame, [0, span], [1 + 0.07 * gain, 1], clamp);
    return <AbsoluteFill style={{ transform: `scale(${scale})` }}>{children}</AbsoluteFill>;
  }
  if (treatment === "vertical_pan") {
    const y = interpolate(frame, [0, span], [28 * gain, -28 * gain], clamp);
    return <AbsoluteFill style={{ transform: `translateY(${y}px) scale(1.08)` }}>{children}</AbsoluteFill>;
  }
  if (treatment === "parallax_depth") {
    const scale = interpolate(frame, [0, span], [1.02, 1.08 * Math.min(gain, 1.15)], clamp);
    const y = interpolate(frame, [0, span], [10, -16], clamp);
    return <AbsoluteFill style={{ transform: `translateY(${y}px) scale(${scale})` }}>{children}</AbsoluteFill>;
  }
  if (treatment === "mask_reveal") {
    const reveal = interpolate(frame, [0, Math.min(18, span)], [18, 100], clamp);
    return <AbsoluteFill style={{ clipPath: `inset(${(100 - reveal) / 2}% 0 0 0)` }}>{children}</AbsoluteFill>;
  }
  if (treatment === "horizontal_pan" || treatment === "subtle_drift" || treatment === "cinematic_crop") {
    const distance = treatment === "horizontal_pan" ? 36 : 14;
    const x = interpolate(frame, [0, span], [distance * gain, -distance * gain], clamp);
    return <AbsoluteFill style={{ transform: `translateX(${x}px) scale(1.08)` }}>{children}</AbsoluteFill>;
  }
  const scale = interpolate(frame, [0, span], [1, 1 + 0.08 * gain], clamp);
  return <AbsoluteFill style={{ transform: `scale(${scale})` }}>{children}</AbsoluteFill>;
}

function Enter({ transition, children }: { transition: string; children: ReactNode }) {
  const frame = useCurrentFrame();
  if (!transition || transition === "cut") return <>{children}</>;
  if (transition === "mask_wipe") {
    const reveal = interpolate(frame, [0, 12], [8, 100], clamp);
    return <AbsoluteFill style={{ clipPath: `inset(0 ${100 - reveal}% 0 0)` }}>{children}</AbsoluteFill>;
  }
  // Never fade from empty black — keep the picture readable through the crossfade.
  const opacity = interpolate(frame, [0, 10], [0.55, 1], clamp);
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
}

function Caption({
  text,
  emphasis,
  animate = "fade",
  locale = "ru-RU",
}: {
  text: string;
  emphasis?: string[];
  animate?: "fade" | "pop" | "mask" | "slide";
  locale?: SupportedLocale;
}) {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 64,
          width: 952,
          bottom: PORTRAIT.captionClearance - 60,
          height: 240,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
        }}
      >
        <div
          data-caption-backing="dark"
          style={{
            maxWidth: 920,
            padding: "22px 36px 26px",
            borderRadius: 22,
            background: "rgba(12, 11, 10, 0.78)",
            boxShadow: "0 8px 28px rgba(0,0,0,0.4)",
          }}
        >
          <AutoFitText
            text={text}
            maxWidth={848}
            maxHeight={168}
            role={{ min: 64, max: 92, weight: 700, lineHeight: 1.1, tracking: -0.02 }}
            align="center"
            vertical="center"
            wrapMode="auto"
            maxLines={2}
            emphasis={emphasis}
            animate={animate}
            locale={locale}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
}

function Speaker({
  file,
  startFrom,
  zoomTo,
  crop,
  circle = false,
}: {
  file: string;
  startFrom: number;
  frames?: number;
  zoomTo: number;
  crop?: string;
  circle?: boolean;
}) {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 14], [0, 1], clamp);
  const video = (
    <AbsoluteFill style={{ ...(crop ? { clipPath: crop } : {}), transform: `scale(${zoomTo})` }}>
      <OffthreadVideo
        src={media(file)}
        startFrom={startFrom}
        volume={0}
        style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center 22%" }}
      />
    </AbsoluteFill>
  );
  if (!circle) return video;
  // Rounded portrait PIP — continuous scale from full frame, never a tiny face circle.
  const pip = PORTRAIT.conceptPip;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          right: pip.right,
          bottom: pip.bottom,
          width: pip.width,
          height: pip.height,
          borderRadius: PORTRAIT.radius,
          overflow: "hidden",
          border: `3px solid ${theme.color.lineStrong}`,
          boxShadow: theme.shadow.soft,
          opacity: enter,
          transform: `translateY(${(1 - enter) * 36}px) scale(${0.92 + enter * 0.08})`,
        }}
      >
        {video}
      </div>
    </AbsoluteFill>
  );
}

function layoutZoom(layout: string) {
  if (layout === "speaker_closeup") return 1.28;
  if (layout === "speaker_medium") return 1.08;
  if (layout === "speaker_punch_in") return 1.18;
  return 1.04;
}

function Hook({ file, from, frames, look }: { file: string; from: number; frames: number; look: SceneLook }) {
  const frame = useCurrentFrame();
  const baseZoom = layoutZoom(look.speaker.layout);
  // Mid-hook punch keeps the opener from reading as a locked still when the beat stretches.
  const punchAt = Math.max(18, Math.round(frames * 0.42));
  const punch = interpolate(frame, [punchAt, punchAt + 16], [0, 0.12], clamp);
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill>
        <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={baseZoom + punch} />
        </Move>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      </AbsoluteFill>
    </Enter>
  );
}

function Residency({ file, from, frames, look }: { file: string; from: number; frames: number; look: SceneLook }) {
  const frame = useCurrentFrame();
  const enterEnd = Math.min(28, Math.max(16, Math.round(frames * 0.22)));
  const holdStart = enterEnd;
  const exitStart = Math.max(holdStart + 12, frames - 18);
  const panelProgress = interpolate(frame, [0, enterEnd], [0, 1], clamp);
  const exitProgress = interpolate(frame, [exitStart, frames - 1], [0, 1], clamp);
  const mediaOpacity = interpolate(frame, [4, enterEnd], [0, 1], clamp) * (1 - exitProgress * 0.35);
  const speakerRight = look.speaker.layout !== "speaker_split_left";
  const speakerSide = speakerRight ? "right" : "left";
  const mediaSide = speakerRight ? "left" : "right";
  const speakerBox = splitSpeakerRect(speakerSide);
  const mediaBox = splitMediaRect(mediaSide);
  const staged = look.background.staged;
  const motionPlate = Boolean(staged && /\.(mp4|webm|mov)$/i.test(staged));
  const plate = staged && !motionPlate ? staged : null;
  const support = look.foreground.staged || "passport.png";
  // Slide speaker from near-fullscreen toward the split panel (no shrink-to-empty).
  const speakerWidth = interpolate(panelProgress, [0, 1], [PORTRAIT.width - PORTRAIT.pad * 2, speakerBox.width], clamp);
  const speakerLeft = speakerRight
    ? interpolate(panelProgress, [0, 1], [PORTRAIT.pad, speakerBox.left], clamp)
    : PORTRAIT.pad;
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        {/* Full-bleed cover media — landscape sources fill portrait via cover, not letterbox. */}
        <AbsoluteFill style={{ opacity: mediaOpacity * 0.55 }}>
          {motionPlate && staged ? (
            <OffthreadVideo src={media(staged)} volume={0} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : plate ? (
            <Img src={media(plate)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <AbsoluteFill style={{ background: theme.gradient.broll }} />
          )}
        </AbsoluteFill>
        <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(18,17,15,0.55) 0%, rgba(18,17,15,0.2) 45%, rgba(18,17,15,0.65) 100%)" }} />
        <div
          style={{
            position: "absolute",
            left: mediaBox.left,
            top: mediaBox.top,
            width: mediaBox.width,
            height: mediaBox.height,
            borderRadius: PORTRAIT.radius,
            overflow: "hidden",
            opacity: mediaOpacity,
            transform: `translateY(${(1 - panelProgress) * 28}px)`,
            boxShadow: theme.shadow.soft,
          }}
        >
          {motionPlate && staged ? (
            <OffthreadVideo src={media(staged)} volume={0} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : plate ? (
            <Img src={media(plate)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <Img src={media(support)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          )}
          <Img
            src={media(support)}
            style={{
              position: "absolute",
              right: 16,
              bottom: 16,
              width: "42%",
              height: "38%",
              objectFit: "contain",
              filter: "drop-shadow(0 12px 24px rgba(0,0,0,0.45))",
            }}
          />
        </div>
        <div
          style={{
            position: "absolute",
            left: speakerLeft,
            top: speakerBox.top,
            width: speakerWidth,
            height: speakerBox.height,
            borderRadius: PORTRAIT.radius,
            overflow: "hidden",
            boxShadow: theme.shadow.soft,
          }}
        >
          <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
            <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.08} />
          </Move>
        </div>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      </AbsoluteFill>
    </Enter>
  );
}

function Consult({ frames, look }: { frames: number; look: SceneLook }) {
  const still = look.background.staged;
  const motionPlate = Boolean(still && /\.(mp4|webm|mov)$/i.test(still));
  // Always fill the portrait canvas with a cover plate; stamp/webm assets ride as midground.
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        <Move treatment="ambient_loop" intensity={look.motionIntensity} frames={frames}>
          <OffthreadVideo
            src={media("consult.mp4")}
            volume={0}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </Move>
        {still && !motionPlate ? (
          <AbsoluteFill style={{ opacity: 0.92 }}>
            <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
              <Img src={media(still)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </Move>
          </AbsoluteFill>
        ) : null}
        {/* Sparse stamp/webm plates sit on black canvases — do not mount them as panels. */}
        {motionPlate && still && /\.(mp4|mov)$/i.test(still) ? (
          <div
            style={{
              position: "absolute",
              left: PORTRAIT.pad,
              bottom: PORTRAIT.captionClearance + 24,
              width: 360,
              height: 420,
              borderRadius: PORTRAIT.radius,
              overflow: "hidden",
              boxShadow: theme.shadow.soft,
              background: theme.color.bgElevated,
              border: `1px solid ${theme.color.lineStrong}`,
            }}
          >
            <OffthreadVideo
              src={media(still)}
              volume={0}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          </div>
        ) : null}
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      </AbsoluteFill>
    </Enter>
  );
}

function Beside({
  file,
  from,
  frames,
  look,
  locale = "ru-RU",
}: {
  file: string;
  from: number;
  frames: number;
  look: SceneLook;
  locale?: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  const enterEnd = Math.min(24, Math.max(14, Math.round(frames * 0.18)));
  const panelProgress = interpolate(frame, [0, enterEnd], [0, 1], clamp);
  const cards = criteriaCardsFor(locale);
  const speakerLeft = look.speaker.layout === "speaker_split_left";
  const speakerSide = speakerLeft ? "left" : "right";
  const cardSide = speakerLeft ? "right" : "left";
  const speakerBox = splitSpeakerRect(speakerSide);
  const cardBox = splitMediaRect(cardSide);
  const cardCount = cards.length;
  const cardGap = 18;
  const cardHeight = Math.floor((cardBox.height - cardGap * (cardCount - 1)) / cardCount);
  const pace = frames / 132;
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        <AbsoluteFill style={{ background: theme.gradient.speaker, opacity: 0.85 }} />
        <div
          style={{
            position: "absolute",
            left: speakerBox.left,
            top: speakerBox.top,
            width: speakerBox.width,
            height: speakerBox.height,
            borderRadius: PORTRAIT.radius,
            overflow: "hidden",
            boxShadow: theme.shadow.soft,
            transform: `translateX(${(1 - panelProgress) * (speakerLeft ? -40 : 40)}px)`,
          }}
        >
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.06} />
        </div>
        <div
          style={{
            position: "absolute",
            left: cardBox.left,
            top: cardBox.top,
            width: cardBox.width,
            height: cardBox.height,
            display: "flex",
            flexDirection: "column",
            gap: cardGap,
          }}
        >
          {cards.map((card, index) => {
            const shown = interpolate(
              frame,
              [(8 + index * 14) * pace, (22 + index * 14) * pace],
              [0, 1],
              clamp,
            );
            return (
              <div
                key={card.title}
                style={{
                  height: cardHeight,
                  opacity: shown,
                  transform: `translateY(${(1 - shown) * 28}px)`,
                  padding: "22px 26px",
                  borderRadius: PORTRAIT.radius - 4,
                  background: theme.color.bgElevated,
                  border: `1px solid ${theme.color.lineStrong}`,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  boxShadow: theme.shadow.soft,
                }}
              >
                <AutoFitText
                  text={card.title}
                  maxWidth={cardBox.width - 52}
                  maxHeight={Math.min(64, cardHeight * 0.38)}
                  role={theme.type.title}
                  align="left"
                  vertical="center"
                  locale={locale}
                />
                <div style={{ height: 8 }} />
                <AutoFitText
                  text={card.explanation}
                  maxWidth={cardBox.width - 52}
                  maxHeight={Math.min(88, cardHeight * 0.42)}
                  role={theme.type.support}
                  align="left"
                  vertical="center"
                  wrapMode="auto"
                  maxLines={2}
                  locale={locale}
                />
              </div>
            );
          })}
        </div>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      </AbsoluteFill>
    </Enter>
  );
}

function Steps({ frames }: { frames: number }) {
  return renderScene(
    normalizeScene({
      id: "process",
      type: "progress_steps",
      variant: "vertical",
      durationInFrames: frames,
      title: "Сопровождение",
      steps: [{ label: "Консультация" }, { label: "Программа" }, { label: "Документы" }],
      transition: { type: "cut", durationInFrames: 0 },
    }),
  );
}

function Return({ file, from, frames, look }: { file: string; from: number; frames: number; look: SceneLook }) {
  return (
    <Enter transition={look.transition}>
    <AbsoluteFill>
      <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
        <Speaker file={file} startFrom={from} frames={frames} zoomTo={layoutZoom(look.speaker.layout)} />
      </Move>
      <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
    </AbsoluteFill>
    </Enter>
  );
}

function bedVolume(frame: number, frames: number) {
  const fadeIn = interpolate(frame, [0, 15], [0, 1], clamp);
  const fadeOut = interpolate(frame, [Math.max(16, frames - 30), frames - 1], [1, 0], clamp);
  const gapStart = Math.round((198 / DIRECTOR_V3_FRAMES) * frames);
  const gapEnd = Math.round((222 / DIRECTOR_V3_FRAMES) * frames);
  const gap = frame >= gapStart && frame < gapEnd ? 0.4 : 0.26;
  return fadeIn * fadeOut * gap;
}

export function DirectorV3({
  durationSeconds = 20,
  speakerFile = "speaker.mp4",
  visualPlan = null,
  locale = "ru-RU",
}: DirectorV3Props) {
  const frames = framesForSeconds(durationSeconds);
  const [hook, residency, consult, beside, steps, ret] = beatsFor(frames);
  const scale = frames / DIRECTOR_V3_FRAMES;
  const planLocale = visualPlan?.language || locale;
  const looks = {
    hook: sceneLook(visualPlan, "hook"),
    residency: sceneLook(visualPlan, "residency"),
    consult: sceneLook(visualPlan, "consult"),
    beside: sceneLook(visualPlan, "beside"),
    steps: sceneLook(visualPlan, "steps"),
    return: sceneLook(visualPlan, "return"),
  };
  const captions = CAPTIONS.map((row) => {
    const from = Math.round(row.from * scale);
    const beatAt = [hook, residency, consult, beside, steps, ret];
    const ids = ["hook", "residency", "consult", "beside", "steps", "return"] as const;
    let sceneId: (typeof ids)[number] = "hook";
    beatAt.forEach((beat, index) => {
      if (from >= beat.from) sceneId = ids[index];
    });
    const animate = (looks[sceneId].typography.animate || "fade") as "fade" | "pop" | "mask" | "slide";
    return {
      ...row,
      from,
      duration: Math.max(1, Math.round(row.duration * scale)),
      animate,
    };
  });
  const conceptOn = visualPlan?.conceptTriggers !== false;
  const concepts: SyncedConceptTrigger[] = conceptOn ? syncConceptTriggers(CAPTIONS, scale) : [];
  // Editorial layouts already carry the idea — stacking concept cards causes face hits + black voids.
  const layoutOwned = [
    { from: residency.from, to: residency.from + residency.duration, skip: ["document_stamp", "family_cluster", "budget_scale"] },
    { from: consult.from, to: consult.from + consult.duration, skip: ["comparison_columns", "document_stamp", "steps_reveal"] },
    { from: beside.from, to: beside.from + beside.duration, skip: ["family_cluster", "budget_scale", "comparison_columns"] },
    { from: steps.from, to: steps.from + steps.duration, skip: ["steps_reveal"] },
  ] as const;
  const speakerPrimary = [
    { from: hook.from, to: hook.from + hook.duration },
    { from: residency.from, to: residency.from + residency.duration },
    { from: beside.from, to: beside.from + beside.duration },
    { from: ret.from, to: ret.from + ret.duration },
  ];
  const plate = visualPlan?.backgroundPlate ?? null;
  const hero = visualPlan?.heroObject ?? null;
  return (
    <AbsoluteFill style={{ background: theme.color.bg, fontFamily: theme.font.sans }}>
      <LocaleProvider locale={planLocale}>
      <Audio src={media(speakerFile)} volume={1.6} />
      <Audio src={media("bed.mp3")} volume={(f) => bedVolume(f, frames)} />
      {plate ? (
        <Sequence from={0} durationInFrames={frames} name="plate">
          <BackgroundPlate treatment={plate} frames={frames} intensity={1} />
        </Sequence>
      ) : null}
      <Sequence from={hook.from} durationInFrames={hook.duration} name="hook">
        <ParallaxLayers
          frames={hook.duration}
          intensity={looks.hook.motionIntensity === "high" ? 1.2 : 0.85}
          layers={[{ depth: 0.4, children: <Hook file={speakerFile} from={hook.from} frames={hook.duration} look={looks.hook} /> }]}
        />
      </Sequence>
      <Sequence from={residency.from} durationInFrames={residency.duration} name="residency">
        <Residency file={speakerFile} from={residency.from} frames={residency.duration} look={looks.residency} />
      </Sequence>
      <Sequence from={consult.from} durationInFrames={consult.duration} name="consult">
        <Consult frames={consult.duration} look={looks.consult} />
      </Sequence>
      <Sequence from={beside.from} durationInFrames={beside.duration} name="beside">
        <Beside file={speakerFile} from={beside.from} frames={beside.duration} look={looks.beside} locale={planLocale} />
      </Sequence>
      <Sequence from={steps.from} durationInFrames={steps.duration} name="steps">
        <Enter transition={looks.steps.transition}>
          <Steps frames={steps.duration} />
        </Enter>
      </Sequence>
      <Sequence from={ret.from} durationInFrames={ret.duration} name="return">
        <Return file={speakerFile} from={ret.from} frames={ret.duration} look={looks.return} />
      </Sequence>
      {concepts.map((hit) => {
        const owned = layoutOwned.find((range) => hit.fromFrame >= range.from && hit.fromFrame < range.to);
        if (owned && (owned.skip as readonly string[]).includes(hit.presetId)) return null;
        // Clip concept to the current beat so overlays do not hang over an empty cut.
        const beatEnd =
          [hook, residency, consult, beside, steps, ret].find(
            (beat) => hit.fromFrame >= beat.from && hit.fromFrame < beat.from + beat.duration,
          )?.duration ?? hit.durationInFrames;
        const beatFrom =
          [hook, residency, consult, beside, steps, ret].find(
            (beat) => hit.fromFrame >= beat.from && hit.fromFrame < beat.from + beat.duration,
          )?.from ?? hit.fromFrame;
        const dur = Math.max(1, Math.min(hit.durationInFrames, beatFrom + beatEnd - hit.fromFrame));
        const speakerOn = speakerPrimary.some((range) => hit.fromFrame >= range.from && hit.fromFrame < range.to);
        const showPip = !speakerOn && dur >= 36;
        return (
          <Sequence key={`concept-${hit.fromFrame}-${hit.presetId}`} from={hit.fromFrame} durationInFrames={dur} name={`concept-${hit.presetId}`}>
            <ConceptViz hit={hit} frames={dur} />
            {showPip ? <Speaker file={speakerFile} startFrom={hit.fromFrame} zoomTo={1.14} circle /> : null}
          </Sequence>
        );
      })}
      {hero ? (
        <Sequence from={residency.from} durationInFrames={residency.duration} name="hero-object">
          <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.92 }}>
            <HeroObject kind={hero} frames={residency.duration} />
          </AbsoluteFill>
        </Sequence>
      ) : null}
      {captions.map((row) => (
        <Sequence key={row.from} from={row.from} durationInFrames={row.duration} name={`cap-${row.from}`}>
          <Caption text={row.text} emphasis={row.emphasis} animate={row.animate} locale={planLocale} />
        </Sequence>
      ))}
      </LocaleProvider>
    </AbsoluteFill>
  );
}
