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
import { PORTRAIT, criteriaCardsFor, pipRect, splitMediaRect, splitSpeakerRect } from "./portraitLayouts";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const media = (name: string) => staticFile(`director-v3/${name}`);

export const DIRECTOR_V3_FPS = 30;
export const DIRECTOR_V3_FRAMES = 600;
/** Shorter hook → earlier media beat; avoids 0–19s talking-head lock on 60s cuts. */
const BEAT_FRAMES = [54, 168, 120, 132, 81, 45] as const;

export type CriteriaCardLook = { title: string; explanation: string };

export type SceneLook = {
  sceneId: string;
  speaker: { layout: string };
  background: { treatment: string; staged?: string | null };
  foreground: { treatment: string; staged?: string | null; assetId?: string | null };
  typography: {
    animate?: string;
    headline?: string;
    cards?: CriteriaCardLook[];
    stepsTitle?: string;
    steps?: string[];
    cardMode?: "stack" | "progressive_one" | "none";
  };
  transition: string;
  motionIntensity: "low" | "medium" | "high";
  /** From editing_controls Animation % — false skips purposeful plate motion. */
  animateGraphics?: boolean;
  /** From editing_controls Density % — caps concurrent overlays. */
  overlayBudget?: number;
  headline?: string;
  criteriaCards?: CriteriaCardLook[];
  stepsTitle?: string;
  steps?: string[];
  cardMode?: "stack" | "progressive_one" | "none";
  shotPlan?: Record<string, unknown>;
};

export type EditingControls = {
  animation: number;
  intensity: number;
  motion: number;
  density: number;
  visualEnergy?: string;
  preset?: string;
};

export type TranscriptCaption = {
  start: number;
  end: number;
  text: string;
  source?: string;
};

export type VisualPlan = {
  generationId?: string;
  visualSeed: number;
  artDirection: string;
  scenes: SceneLook[];
  /** Timed phrases from source/target transcript — preferred over caption packs. */
  captions?: TranscriptCaption[];
  captionSource?: string;
  /** When true (default), spoken captions drive concept viz overlays. */
  conceptTriggers?: boolean;
  backgroundPlate?: "ink_lift" | "paper_grain" | "navy_grid" | "gold_veil" | "soft_vignette" | null;
  heroObject?: "passport" | "key" | "globe" | "house" | null;
  language?: SupportedLocale;
  editingControls?: EditingControls | null;
  motionIntensity?: "low" | "medium" | "high";
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
  const raw = plan?.scenes?.find((scene) => scene.sceneId === sceneId) ?? { ...LOOK, sceneId };
  // Animation slider: scenes outside the share keep the host picture, no plate motion.
  if (raw.animateGraphics === false) {
    return {
      ...raw,
      motionIntensity: "low",
      background: { ...raw.background, treatment: "static_editorial" },
    };
  }
  return raw;
}

/** Motion × Intensity → Remotion amplitude gain (speech rate untouched). */
export function editingMotionGain(controls?: EditingControls | null): number {
  if (!controls) return 1;
  const motion = Math.max(0, Math.min(100, Number(controls.motion) || 80));
  const intensity = Math.max(5, Math.min(100, Number(controls.intensity) || 60));
  return Math.max(0.35, Math.min(1.75, (motion / 100) * (0.55 + intensity / 200)));
}

/** Density → max concurrent concept overlays (relevance still wins upstream). */
export function editingConceptCap(controls?: EditingControls | null): number {
  const density = controls ? Number(controls.density) : 70;
  if (density < 25) return 0;
  if (density < 55) return 2;
  if (density < 80) return 4;
  return 8;
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

type CaptionLine = { beat: number; text: string; emphasis?: string[]; share?: number };

/** Caption lines keyed to beat index (hook…return). Timing from beatsFor; text from targetLocale. */
const CAPTION_LINES_RU: CaptionLine[] = [
  { beat: 0, text: "Планируете переезд", emphasis: ["переезд"], share: 1 },
  { beat: 1, text: "второй вид на жительство", emphasis: ["жительство"], share: 0.55 },
  { beat: 1, text: "с чего начать?", emphasis: ["начать"], share: 0.45 },
  { beat: 2, text: "подходящую программу", emphasis: ["программу"], share: 1 },
  { beat: 3, text: "с учетом целей", emphasis: ["целей"], share: 0.45 },
  { beat: 3, text: "семьи и бюджета", emphasis: ["бюджета"], share: 0.55 },
  { beat: 4, text: "весь процесс", emphasis: ["процесс"], share: 1 },
  { beat: 5, text: "консультация и программа", emphasis: ["программа"], share: 1 },
];

const CAPTION_LINES_EN: CaptionLine[] = [
  { beat: 0, text: "Planning a move", emphasis: ["move"], share: 1 },
  { beat: 1, text: "a second residency", emphasis: ["residency"], share: 0.55 },
  { beat: 1, text: "where do you start?", emphasis: ["start"], share: 0.45 },
  { beat: 2, text: "the right program", emphasis: ["program"], share: 1 },
  { beat: 3, text: "for your goals", emphasis: ["goals"], share: 0.45 },
  { beat: 3, text: "family and budget", emphasis: ["budget"], share: 0.55 },
  { beat: 4, text: "the full process", emphasis: ["process"], share: 1 },
  { beat: 5, text: "consult and program", emphasis: ["program"], share: 1 },
];

const CAPTION_LINES_ZH: CaptionLine[] = [
  { beat: 0, text: "计划搬迁吗", emphasis: ["搬迁"], share: 1 },
  { beat: 1, text: "第二居留身份", emphasis: ["居留"], share: 0.55 },
  { beat: 1, text: "从何开始？", emphasis: ["开始"], share: 0.45 },
  { beat: 2, text: "合适的方案", emphasis: ["方案"], share: 1 },
  { beat: 3, text: "结合目标", emphasis: ["目标"], share: 0.45 },
  { beat: 3, text: "家庭与预算", emphasis: ["预算"], share: 0.55 },
  { beat: 4, text: "完整流程", emphasis: ["流程"], share: 1 },
  { beat: 5, text: "咨询与方案", emphasis: ["方案"], share: 1 },
];

function captionLinesFor(locale: string): CaptionLine[] {
  if (locale.startsWith("zh")) return CAPTION_LINES_ZH;
  if (locale.startsWith("en")) return CAPTION_LINES_EN;
  return CAPTION_LINES_RU;
}

function captionsForBeats(beats: { from: number; duration: number }[], locale: string) {
  const pack = captionLinesFor(locale);
  const byBeat = new Map<number, CaptionLine[]>();
  for (const line of pack) {
    const list = byBeat.get(line.beat) || [];
    list.push(line);
    byBeat.set(line.beat, list);
  }
  const rows: { from: number; duration: number; text: string; emphasis?: string[] }[] = [];
  for (const [index, beat] of beats.entries()) {
    const lines = byBeat.get(index) || [];
    if (!lines.length) continue;
    const totalShare = lines.reduce((sum, line) => sum + (line.share ?? 1), 0) || 1;
    let cursor = beat.from;
    lines.forEach((line, lineIndex) => {
      const share = (line.share ?? 1) / totalShare;
      const duration =
        lineIndex === lines.length - 1
          ? beat.from + beat.duration - cursor
          : Math.max(1, Math.round(beat.duration * share));
      rows.push({ from: cursor, duration, text: line.text, emphasis: line.emphasis });
      cursor += duration;
    });
  }
  return rows;
}

/** Prefer real transcript phrases (seconds → frames). Pack is legacy fallback only. */
function captionsFromTranscript(
  phrases: TranscriptCaption[] | undefined,
  totalFrames: number,
  fps = DIRECTOR_V3_FPS,
): { from: number; duration: number; text: string; emphasis?: string[] }[] {
  if (!phrases?.length) return [];
  const rows: { from: number; duration: number; text: string; emphasis?: string[] }[] = [];
  for (const phrase of phrases) {
    const text = String(phrase.text || "").trim();
    if (!text) continue;
    const from = Math.max(0, Math.round(Number(phrase.start || 0) * fps));
    const end = Math.max(from + 1, Math.round(Number(phrase.end || 0) * fps));
    if (from >= totalFrames) continue;
    rows.push({
      from,
      duration: Math.min(totalFrames - from, end - from),
      text,
    });
  }
  return rows;
}

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
  // Plan band sets the base; editingControls Motion/Intensity already folded into scene band.
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
  const frame = useCurrentFrame();
  const clean = String(text || "").trim();
  // Never mount an empty dark plate — backing lives only while text is present.
  if (!clean) return null;
  const enter = interpolate(frame, [0, 8], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 64,
          width: 952,
          bottom: PORTRAIT.captionClearance,
          height: 200,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          opacity: enter,
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
            text={clean}
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
  const pip = pipRect();
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

function KineticHeadline({ text, locale }: { text: string; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 16], [0, 1], clamp);
  if (!text) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 56,
          right: 56,
          top: 220,
          opacity: enter,
          transform: `translateY(${(1 - enter) * 28}px) scale(${0.96 + enter * 0.04})`,
        }}
      >
        <div
          style={{
            padding: "20px 28px",
            borderRadius: 20,
            background: "rgba(12, 11, 10, 0.72)",
            boxShadow: "0 10px 32px rgba(0,0,0,0.35)",
          }}
        >
          <AutoFitText
            text={text}
            maxWidth={940}
            maxHeight={160}
            role={{ min: 56, max: 88, weight: 800, lineHeight: 1.05, tracking: -0.03 }}
            align="left"
            vertical="center"
            wrapMode="auto"
            maxLines={2}
            animate="pop"
            locale={locale}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
}

function Hook({ file, from, frames, look, locale = "ru-RU" }: { file: string; from: number; frames: number; look: SceneLook; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const baseZoom = layoutZoom(look.speaker.layout);
  // Mid-hook punch keeps the opener from reading as a locked still when the beat stretches.
  const punchAt = Math.max(18, Math.round(frames * 0.42));
  const punch = interpolate(frame, [punchAt, punchAt + 16], [0, 0.12], clamp);
  const headline = look.headline || look.typography?.headline || "";
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill>
        <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={baseZoom + punch} />
        </Move>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
        <KineticHeadline text={headline} locale={locale} />
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
  // Never fall back to geometric passport.png — placeholder shelf reads as decoration.
  const fgStaged = look.foreground.staged;
  const supportShelf =
    fgStaged && !/passport\.png$/i.test(fgStaged) && !/document_approval/i.test(fgStaged) ? fgStaged : null;
  const hasPhotoPlate = Boolean(plate || motionPlate);
  // Slide speaker from near-fullscreen toward the split panel (no shrink-to-empty).
  const speakerWidth = interpolate(panelProgress, [0, 1], [PORTRAIT.width - PORTRAIT.pad * 2, speakerBox.width], clamp);
  const speakerLeft = speakerRight
    ? interpolate(panelProgress, [0, 1], [PORTRAIT.pad, speakerBox.left], clamp)
    : PORTRAIT.pad;
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        {/* Full-bleed cover media — landscape sources fill portrait via cover, not letterbox. */}
        {/* Soft ambient plate only — avoid stacked full-frame dimmers crushing midtones. */}
        <AbsoluteFill style={{ opacity: mediaOpacity * 0.28 }}>
          {motionPlate && staged ? (
            <OffthreadVideo src={media(staged)} volume={0} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : plate ? (
            <Img src={media(plate)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <AbsoluteFill style={{ background: theme.gradient.broll }} />
          )}
        </AbsoluteFill>
        {/* Lateral veil only — caption scrim is applied once at the bottom of the stack. */}
        <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(18,17,15,0.12) 0%, rgba(18,17,15,0.02) 50%, rgba(18,17,15,0.14) 100%)" }} />
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
            <AbsoluteFill style={{ background: theme.gradient.image }} />
          )}
          {/* Real library FG only — omit SVG/placeholder shelves when the plate already carries meaning. */}
          {supportShelf && !hasPhotoPlate ? (
            <Img
              src={media(supportShelf)}
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
          ) : null}
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

function Consult({
  file,
  from,
  frames,
  look,
}: {
  file: string;
  from: number;
  frames: number;
  look: SceneLook;
}) {
  const staged = look.background.staged;
  // One cover only: prefer staged library plate; fallback consult.mp4. Never also inset the same source.
  const cover = staged && !/document_approval/i.test(staged) ? staged : "consult.mp4";
  const coverVideo = /\.(mp4|webm|mov)$/i.test(cover);
  const pip = pipRect();
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        <Move treatment="ambient_loop" intensity={look.motionIntensity} frames={frames}>
          {coverVideo ? (
            <OffthreadVideo
              src={media(cover)}
              volume={0}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <Img src={media(cover)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          )}
        </Move>
        {/* Presenter PIP = original speaker at beat offset — never a second library plate. */}
        <div
          style={{
            position: "absolute",
            right: pip.right,
            bottom: pip.bottom,
            width: pip.width,
            height: pip.height,
            borderRadius: PORTRAIT.radius,
            overflow: "hidden",
            boxShadow: theme.shadow.soft,
            border: `1px solid ${theme.color.lineStrong}`,
            background: theme.color.bgElevated,
          }}
        >
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.12} />
        </div>
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
  const planned = look.criteriaCards?.length
    ? look.criteriaCards
    : look.typography?.cards?.length
      ? look.typography.cards
      : null;
  const cards = planned ?? criteriaCardsFor(locale);
  const progressive =
    (look.cardMode || look.typography?.cardMode || "progressive_one") === "progressive_one";
  const speakerLeft = look.speaker.layout === "speaker_split_left";
  const speakerSide = speakerLeft ? "left" : "right";
  const cardSide = speakerLeft ? "right" : "left";
  const speakerBox = splitSpeakerRect(speakerSide);
  const cardBox = splitMediaRect(cardSide);
  const cardCount = Math.max(1, cards.length);
  // One hero card at a time — phone-readable; stack only as legacy fallback.
  const slot = Math.min(
    cardCount - 1,
    Math.max(0, Math.floor((frame / Math.max(1, frames)) * cardCount)),
  );
  const active = cards[slot] || cards[0];
  const slotEnter = interpolate(
    frame,
    [(slot * frames) / cardCount, (slot * frames) / cardCount + 12],
    [0, 1],
    clamp,
  );
  const cardGap = 18;
  const stackHeight = Math.floor((cardBox.height - cardGap * (cardCount - 1)) / cardCount);
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
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
            justifyContent: progressive ? "center" : "flex-start",
          }}
        >
          {progressive && active ? (
            <div
              key={`${active.title}-${slot}`}
              style={{
                height: cardBox.height,
                opacity: slotEnter,
                transform: `translateY(${(1 - slotEnter) * 28}px)`,
                padding: "48px 36px",
                borderRadius: PORTRAIT.radius,
                background: theme.color.bgElevated,
                border: `1px solid ${theme.color.lineStrong}`,
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                boxShadow: theme.shadow.soft,
              }}
            >
              <AutoFitText
                text={active.title}
                maxWidth={cardBox.width - 72}
                maxHeight={160}
                role={{ min: 64, max: 96, weight: 800, lineHeight: 1.05, tracking: -0.02 }}
                align="left"
                vertical="center"
                locale={locale}
              />
              <div style={{ height: 28 }} />
              <AutoFitText
                text={active.explanation}
                maxWidth={cardBox.width - 72}
                maxHeight={280}
                role={{ min: 40, max: 56, weight: 600, lineHeight: 1.25, tracking: -0.01 }}
                align="left"
                vertical="center"
                wrapMode="auto"
                maxLines={4}
                locale={locale}
              />
            </div>
          ) : (
            cards.map((card, index) => {
              const shown = interpolate(frame, [8 + index * 14, 22 + index * 14], [0, 1], clamp);
              return (
                <div
                  key={card.title}
                  style={{
                    height: stackHeight,
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
                    maxHeight={Math.min(64, stackHeight * 0.38)}
                    role={theme.type.title}
                    align="left"
                    vertical="center"
                    locale={locale}
                  />
                  <div style={{ height: 8 }} />
                  <AutoFitText
                    text={card.explanation}
                    maxWidth={cardBox.width - 52}
                    maxHeight={Math.min(120, stackHeight * 0.52)}
                    role={theme.type.caption}
                    align="left"
                    vertical="center"
                    wrapMode="auto"
                    maxLines={2}
                    locale={locale}
                  />
                </div>
              );
            })
          )}
        </div>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      </AbsoluteFill>
    </Enter>
  );
}

function stepsCopy(locale: string) {
  if (locale.startsWith("zh")) {
    return { title: "全程陪同", steps: [{ label: "咨询" }, { label: "方案" }, { label: "文件" }] };
  }
  if (locale.startsWith("en")) {
    return { title: "Guided process", steps: [{ label: "Consult" }, { label: "Program" }, { label: "Documents" }] };
  }
  return { title: "Сопровождение", steps: [{ label: "Консультация" }, { label: "Программа" }, { label: "Документы" }] };
}

function Steps({
  frames,
  locale,
  look,
}: {
  frames: number;
  locale: string;
  look?: SceneLook;
}) {
  const copy = stepsCopy(locale);
  const title = look?.stepsTitle || look?.typography?.stepsTitle || copy.title;
  const stepLabels = look?.steps?.length
    ? look.steps
    : look?.typography?.steps?.length
      ? look.typography.steps
      : copy.steps.map((s) => s.label);
  return renderScene(
    normalizeScene({
      id: "process",
      type: "progress_steps",
      variant: "vertical",
      durationInFrames: frames,
      title,
      steps: stepLabels.map((label) => ({ label })),
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
  // Speech-priority duck: audible bed without masking dialogue.
  const gapStart = Math.round((198 / DIRECTOR_V3_FRAMES) * frames);
  const gapEnd = Math.round((222 / DIRECTOR_V3_FRAMES) * frames);
  const gap = frame >= gapStart && frame < gapEnd ? 0.48 : 0.34;
  return fadeIn * fadeOut * gap;
}

export function DirectorV3({
  durationSeconds = 20,
  speakerFile = "speaker.mp4",
  visualPlan = null,
  locale,
}: DirectorV3Props) {
  const frames = framesForSeconds(durationSeconds);
  const [hook, residency, consult, beside, steps, ret] = beatsFor(frames);
  // targetLocale from the visual plan wins; composition defaultLocale is last resort only.
  const planLocale = (visualPlan?.language || locale || "en-US") as SupportedLocale;
  const looks = {
    hook: sceneLook(visualPlan, "hook"),
    residency: sceneLook(visualPlan, "residency"),
    consult: sceneLook(visualPlan, "consult"),
    beside: sceneLook(visualPlan, "beside"),
    steps: sceneLook(visualPlan, "steps"),
    return: sceneLook(visualPlan, "return"),
  };
  const beatList = [hook, residency, consult, beside, steps, ret];
  const ids = ["hook", "residency", "consult", "beside", "steps", "return"] as const;
  const transcriptCaptions = captionsFromTranscript(visualPlan?.captions, frames);
  const packCaptions = captionsForBeats(beatList, planLocale);
  const captionRows = transcriptCaptions.length ? transcriptCaptions : packCaptions;
  const hookHeadline = (looks.hook.headline || looks.hook.typography?.headline || "").trim();
  const captions = captionRows
    .map((row) => {
      let sceneId: (typeof ids)[number] = "hook";
      beatList.forEach((beat, index) => {
        if (row.from >= beat.from) sceneId = ids[index];
      });
      const animate = (looks[sceneId].typography.animate || "fade") as "fade" | "pop" | "mask" | "slide";
      return { ...row, animate, sceneId };
    })
    // Avoid duplicate kinetic headline + identical bottom caption on the opener.
    .filter((row) => {
      if (!hookHeadline) return true;
      if (row.sceneId !== "hook") return true;
      const t = String(row.text || "").trim();
      return t !== hookHeadline && !hookHeadline.startsWith(t) && !t.startsWith(hookHeadline);
    });
  const controls = visualPlan?.editingControls || null;
  const motionGain = editingMotionGain(controls);
  const conceptCap = editingConceptCap(controls);
  const conceptOn = visualPlan?.conceptTriggers !== false && conceptCap > 0;
  // Captions already use composition frames — do not scale again.
  const concepts: SyncedConceptTrigger[] = conceptOn
    ? syncConceptTriggers(captions, 1).slice(0, conceptCap)
    : [];
  // Editorial layouts already carry the idea — stacking concept cards causes face hits + black voids.
  const layoutOwned = [
    { from: hook.from, to: hook.from + hook.duration, skip: ["document_stamp", "family_cluster", "budget_scale"] },
    { from: residency.from, to: residency.from + residency.duration, skip: ["document_stamp", "family_cluster", "budget_scale", "steps_reveal"] },
    { from: consult.from, to: consult.from + consult.duration, skip: ["comparison_columns", "document_stamp", "steps_reveal", "family_cluster", "budget_scale"] },
    { from: beside.from, to: beside.from + beside.duration, skip: ["family_cluster", "budget_scale", "comparison_columns"] },
    { from: steps.from, to: steps.from + steps.duration, skip: ["steps_reveal"] },
  ] as const;
  // Consult mounts its own speaker PIP — skip concept circle to avoid double presenter.
  const speakerPrimary = [
    { from: hook.from, to: hook.from + hook.duration },
    { from: residency.from, to: residency.from + residency.duration },
    { from: consult.from, to: consult.from + consult.duration },
    { from: beside.from, to: beside.from + beside.duration },
    { from: ret.from, to: ret.from + ret.duration },
  ];
  const plate = visualPlan?.backgroundPlate ?? null;
  // Prefer clean photographic residency over decorative SVG hero (passport rect+circle).
  const residencyHasMedia = Boolean(looks.residency.background.staged);
  const hero = residencyHasMedia ? null : visualPlan?.heroObject ?? null;
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
          intensity={(looks.hook.motionIntensity === "high" ? 1.2 : 0.85) * motionGain}
          layers={[{ depth: 0.4, children: <Hook file={speakerFile} from={hook.from} frames={hook.duration} look={looks.hook} locale={planLocale} /> }]}
        />
      </Sequence>
      <Sequence from={residency.from} durationInFrames={residency.duration} name="residency">
        <Residency file={speakerFile} from={residency.from} frames={residency.duration} look={looks.residency} />
      </Sequence>
      <Sequence from={consult.from} durationInFrames={consult.duration} name="consult">
        <Consult file={speakerFile} from={consult.from} frames={consult.duration} look={looks.consult} />
      </Sequence>
      <Sequence from={beside.from} durationInFrames={beside.duration} name="beside">
        <Beside file={speakerFile} from={beside.from} frames={beside.duration} look={looks.beside} locale={planLocale} />
      </Sequence>
      <Sequence from={steps.from} durationInFrames={steps.duration} name="steps">
        <Enter transition={looks.steps.transition}>
          <Steps frames={steps.duration} locale={planLocale} look={looks.steps} />
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
      {captions
        .filter((row) => String(row.text || "").trim().length > 0 && row.duration > 0)
        .map((row) => (
          <Sequence key={row.from} from={row.from} durationInFrames={row.duration} name={`cap-${row.from}`}>
            <Caption text={row.text} emphasis={row.emphasis} animate={row.animate} locale={planLocale} />
          </Sequence>
        ))}
      </LocaleProvider>
    </AbsoluteFill>
  );
}
