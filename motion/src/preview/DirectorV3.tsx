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
import { sceneThemeFromPlate } from "../utils/adaptiveLineStyle";
import { BusinessMotion, type BusinessMotionPayload } from "./BusinessMotion";
import { SemanticMotion } from "../semantic/SemanticMotion";
import type { SemanticMotionPayload } from "../semantic/types";
import type { BackgroundPlateTreatment } from "../cinematic/BackgroundPlate";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const media = (name: string) => staticFile(`director-v3/${name}`);

export const DIRECTOR_V3_FPS = 30;
export const DIRECTOR_V3_FRAMES = 600;
/** Shorter hook → earlier media beat; avoids 0–19s talking-head lock on 60s cuts. */
const BEAT_FRAMES_SHORT = [54, 168, 120, 132, 81, 45] as const;
/** V8 long-form (~60s @ 30fps = 1800 frames). */
const BEAT_FRAMES_LONG = [90, 180, 210, 300, 240, 180, 150, 180, 150, 120] as const;

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
  semanticMotion?: {
    staged?: string | null;
    file?: string;
    assetId?: string;
    motionFamily?: string;
    display?: "float" | "cutaway" | "omit" | string;
  };
  /** V9 composition intelligence — one primary idea, minimal containers. */
  composition?: {
    containerPolicy?: string;
    speakerProtection?: boolean;
    captionRegion?: string;
    visualComplexity?: string;
    suppressHeadline?: boolean;
    suppressHero?: boolean;
    suppressConcepts?: boolean;
    primarySubject?: string;
    secondaryVisual?: string;
    floatObject?: {
      staged?: string | null;
      file?: string;
      assetId?: string;
      placement?: string;
      areaShare?: number;
      background?: string;
      format?: string;
      frameCount?: number;
      scaleProfile?: "hero" | "supporting" | "foreground" | "background" | string;
      minPx?: number;
      maxPx?: number;
      family?: string;
    } | null;
  };
  primaryVisualRole?: string;
  containerPolicy?: string;
  speakerProtection?: boolean;
  captionRegion?: string;
  /** V11.1 evidence-backed business semantic motion (Remotion deterministic). */
  businessMotion?: BusinessMotionPayload | null;
  /** V14 semantic diagram. Present only when SEMANTIC_MOTION_V14_ENABLED stamped the plan. */
  semanticMotionV14?: SemanticMotionPayload | null;
  /** V16 layout decision. Absent when the composer flag is off. */
  sceneComposition?: {
    speakerPresentation?: "fullscreen" | "split" | string;
    layout?: string;
  } | null;
  /** Spoken span for a title. Absent means the title holds for the whole beat. */
  emphasisRange?: [number, number] | number[];
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
  backgroundPlate?: BackgroundPlateTreatment | null;
  heroObject?: "passport" | "key" | "globe" | "house" | null;
  language?: SupportedLocale;
  editingControls?: EditingControls | null;
  motionIntensity?: "low" | "medium" | "high";
  form?: string;
  beatWeights?: number[];
  compositionPolicy?: string;
  shotPlanVersion?: string;
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

export function beatsFor(frames: number, weights?: readonly number[] | number[]) {
  const base =
    weights && weights.length
      ? [...weights]
      : frames >= 45 * DIRECTOR_V3_FPS
        ? [...BEAT_FRAMES_LONG]
        : [...BEAT_FRAMES_SHORT];
  const totalWeight = base.reduce((sum, w) => sum + w, 0) || 1;
  let cursor = 0;
  const lengths = base.slice(0, -1).map((weight) => {
    const length = Math.max(1, Math.round((weight / totalWeight) * frames));
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

/** V8 legacy: opaque webm inside a bordered shelf — avoided by V9. */
function SemanticMotionClip({
  staged,
  frames,
}: {
  staged: string;
  frames: number;
}) {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 14], [0, 1], clamp);
  const exit = interpolate(frame, [Math.max(16, frames - 16), frames - 1], [1, 0.25], clamp);
  const scale = interpolate(frame, [0, Math.min(24, frames)], [0.92, 1], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: enter * exit }}>
      <div
        style={{
          position: "absolute",
          left: 28,
          bottom: PORTRAIT.captionClearance + 200,
          width: 520,
          height: 520,
          borderRadius: PORTRAIT.radius,
          overflow: "hidden",
          boxShadow: theme.shadow.soft,
          border: `2px solid ${theme.color.lineStrong}`,
          background: "rgba(12,11,10,0.45)",
          transform: `scale(${scale})`,
          transformOrigin: "bottom left",
        }}
      >
        <OffthreadVideo
          src={media(staged)}
          volume={0}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>
    </AbsoluteFill>
  );
}

const SCALE_PROFILE_LIMITS: Record<string, { minPx: number; maxPx: number }> = {
  hero: { minPx: 400, maxPx: 560 },
  supporting: { minPx: 300, maxPx: 440 },
  foreground: { minPx: 340, maxPx: 500 },
  background: { minPx: 200, maxPx: 280 },
};

/** V9/V10.1: floating transparent SVG/PNG, RGBA PNG sequence, or true-alpha video. */
function FloatingForeground({
  staged,
  frames,
  placement = "speaker_left_lower",
  areaShare = 0.12,
  format,
  frameCount,
  scaleProfile,
  minPx,
  maxPx,
}: {
  staged: string;
  frames: number;
  placement?: string;
  areaShare?: number;
  format?: string;
  frameCount?: number;
  scaleProfile?: string;
  minPx?: number;
  maxPx?: number;
}) {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 12], [0, 1], clamp);
  const exit = interpolate(frame, [Math.max(18, frames - 14), frames - 1], [1, 0], clamp);
  const scale = interpolate(frame, [0, Math.min(20, frames)], [0.86, 1], clamp);
  const limits =
    SCALE_PROFILE_LIMITS[scaleProfile || ""] ||
    (scaleProfile === "hero"
      ? SCALE_PROFILE_LIMITS.hero
      : { minPx: minPx ?? 220, maxPx: maxPx ?? 340 });
  const lo = minPx ?? limits.minPx;
  const hi = maxPx ?? limits.maxPx;
  const rawSize = Math.round(Math.min(hi, Math.max(lo, PORTRAIT.width * areaShare * 2.2)));
  const rightSide = placement.includes("right");
  // Face-safe: keep the float box in the lower third, outside the face column.
  // Hero cutaways belong in a dedicated layout — never grow into the mouth/eye band.
  const bottom = PORTRAIT.captionClearance + (scaleProfile === "hero" ? 100 : 140);
  const side = rightSide ? { right: 36 } : { left: 36 };
  const faceSafeMax = Math.round(PORTRAIT.height * 0.34);
  const size = Math.min(rawSize, faceSafeMax);
  const isPngSeq = format === "png_seq" || (!/\.(webm|mov|mp4|svg|png|jpg|jpeg|webp)$/i.test(staged) && Boolean(frameCount));
  const isVideo = !isPngSeq && /\.(webm|mov|mp4)$/i.test(staged);
  const mediaStyle = {
    width: "100%",
    height: "100%",
    objectFit: "contain" as const,
    background: "transparent",
  };
  let body: ReactNode = null;
  if (isPngSeq) {
    const total = Math.max(1, frameCount || 90);
    // Play once then hold last frame (no decorative loop).
    const idx = Math.min(total - 1, Math.floor((frame / Math.max(1, Math.min(frames, total))) * total));
    const pad = String(idx + 1).padStart(4, "0");
    const src = media(`${staged.replace(/\/$/, "")}/frame_${pad}.png`);
    body = <Img src={src} style={mediaStyle} />;
  } else if (isVideo) {
    body = <OffthreadVideo src={media(staged)} volume={0} transparent style={mediaStyle} />;
  } else {
    body = <Img src={media(staged)} style={mediaStyle} />;
  }
  return (
    <AbsoluteFill style={{ pointerEvents: "none", opacity: enter * exit }}>
      <div
        style={{
          position: "absolute",
          ...side,
          bottom,
          width: size,
          height: size,
          background: "transparent",
          border: "none",
          boxShadow: "none",
          transform: `scale(${scale})`,
          transformOrigin: rightSide ? "bottom right" : "bottom left",
        }}
      >
        {body}
      </div>
    </AbsoluteFill>
  );
}

function V14Stage({
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
  const layout = look.semanticMotionV14?.layout || "overlay";
  const mode = look.semanticMotionV14?.speakerMode;
  const speakerRect = look.semanticMotionV14?.speakerRect;
  if (mode === "split" && speakerRect) {
    const staged = look.background.staged;
    const motionRect = look.semanticMotionV14?.motionRect;
    const motionPlate = Boolean(staged && /\.(mp4|webm|mov)$/i.test(staged));
    const plate = motionRect
      ? { left: motionRect.left, top: motionRect.top, width: motionRect.width, height: 1920 - motionRect.top }
      : null;
    return (
      <Enter transition={look.transition}>
        <AbsoluteFill style={{ background: theme.color.bg }}>
          {plate && staged ? (
            <div style={{ position: "absolute", ...plate, overflow: "hidden", borderRadius: PORTRAIT.radius }}>
              {motionPlate ? (
                <OffthreadVideo src={media(staged)} volume={0} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              ) : (
                <Img src={media(staged)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              )}
            </div>
          ) : null}
          <div
            style={{
              position: "absolute",
              left: speakerRect.left,
              top: speakerRect.top,
              width: speakerRect.width,
              height: speakerRect.height,
              overflow: "hidden",
            }}
          >
            <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.02} />
          </div>
        </AbsoluteFill>
      </Enter>
    );
  }
  if (mode === "fullscreen" || layout === "overlay") {
    return (
      <Enter transition={look.transition}>
        <AbsoluteFill>
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.04} />
          <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
        </AbsoluteFill>
      </Enter>
    );
  }
  if (layout === "speaker_visual") {
    const mediaSide = look.semanticMotionV14?.mediaSide === "right" ? "right" : "left";
    const speakerSide = mediaSide === "left" ? "right" : "left";
    const box = splitSpeakerRect(speakerSide);
    return (
      <Enter transition={look.transition}>
        <AbsoluteFill style={{ background: theme.color.bg }}>
          <div
            style={{
              position: "absolute",
              left: box.left,
              top: box.top,
              width: box.width,
              height: box.height,
              borderRadius: PORTRAIT.radius,
              overflow: "hidden",
            }}
          >
            <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.08} />
          </div>
        </AbsoluteFill>
      </Enter>
    );
  }
  if (layout === "full_frame") {
    const pip = pipRect();
    return (
      <Enter transition={look.transition}>
        <AbsoluteFill style={{ background: "#0F1720" }}>
          <div
            style={{
              position: "absolute",
              right: pip.right,
              bottom: pip.bottom,
              width: pip.width,
              height: pip.height,
              borderRadius: PORTRAIT.radius,
              overflow: "hidden",
              border: `1px solid ${theme.color.line}`,
            }}
          >
            <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.12} />
          </div>
        </AbsoluteFill>
      </Enter>
    );
  }
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill>
        <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.04} />
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      </AbsoluteFill>
    </Enter>
  );
}

function SceneRouter({
  look,
  file,
  from,
  frames,
  locale,
  plate,
}: {
  look: SceneLook;
  file: string;
  from: number;
  frames: number;
  locale: SupportedLocale;
  plate?: string | null;
}) {
  const layout = look.speaker?.layout || "speaker_fullscreen";
  const sid = look.sceneId;
  const floatObj = look.composition?.floatObject;
  const floatStaged = floatObj?.staged || null;
  const motionDisplay = look.semanticMotion?.display;
  const motionStaged =
    motionDisplay === "omit" || floatStaged
      ? null
      : look.semanticMotion?.staged || null;
  const suppressHeadline = Boolean(look.composition?.suppressHeadline);
  const v14 = look.semanticMotionV14?.componentId ? look.semanticMotionV14 : null;
  const presentation = look.sceneComposition?.speakerPresentation;
  const hasPlate = Boolean(look.background?.staged || look.background?.file || look.background?.assetId);
  const framing = look.speaker?.framing || look.execution?.speakerFraming || "";
  const cutawayWithoutPlate =
    !hasPlate &&
    (framing === "split" ||
      framing === "pip" ||
      layout.includes("split") ||
      layout.includes("with_media") ||
      layout.includes("diagram") ||
      sid === "consult" ||
      sid === "proof" ||
      sid === "context" ||
      sid === "residency" ||
      sid === "steps" ||
      sid === "beside");
  const emphasisLine = look.headline || look.typography?.headline || "";
  let body: ReactNode = null;
  if (v14) {
    body = <V14Stage file={file} from={from} frames={frames} look={look} />;
  } else if (presentation === "emphasis" && emphasisLine) {
    body = (
      <Hook file={file} from={from} frames={frames} look={look} locale={locale} />
    );
  } else if (presentation === "graphic") {
    body = <CleanSteps file={file} from={from} frames={frames} look={look} locale={locale} />;
  } else if (presentation === "split" && hasPlate) {
    body = <Residency file={file} from={from} frames={frames} look={look} />;
  } else if (presentation === "split" && (look.steps?.length || look.typography?.steps?.length)) {
    body = <SpokenSplit file={file} from={from} frames={frames} look={look} locale={locale} />;
  } else if (presentation === "fullscreen" || presentation === "speaker" || cutawayWithoutPlate) {
    body = (
      <Enter transition={look.transition}>
        <AbsoluteFill>
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={layoutZoom(layout)} />
          <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
        </AbsoluteFill>
      </Enter>
    );
  } else if (sid === "beside" || look.cardMode === "progressive_one" || look.typography?.cardMode === "progressive_one") {
    body = <Beside file={file} from={from} frames={frames} look={look} locale={locale} />;
  } else if (sid === "steps" || look.stepsTitle || look.typography?.stepsTitle) {
    // V9: speaker-led progressive steps — no full-screen black card stack.
    const clean = look.composition?.containerPolicy === "minimal" || look.composition?.suppressConcepts;
    body = clean ? (
      <CleanSteps file={file} from={from} frames={frames} look={look} locale={locale} />
    ) : (
      <Enter transition={look.transition}>
        <Steps frames={frames} locale={locale} look={look} />
      </Enter>
    );
  } else if (
    layout.includes("with_media") ||
    sid === "consult" ||
    sid === "proof"
  ) {
    body = <Consult file={file} from={from} frames={frames} look={look} />;
  } else if (
    layout.includes("split") ||
    layout.includes("foreground") ||
    sid === "residency" ||
    sid === "context"
  ) {
    body = <Residency file={file} from={from} frames={frames} look={look} />;
  } else if (sid === "hook" || sid === "problem") {
    body = (
      <Hook
        file={file}
        from={from}
        frames={frames}
        look={look}
        locale={locale}
        suppressHeadline={suppressHeadline}
      />
    );
  } else {
    body = <Return file={file} from={from} frames={frames} look={look} />;
  }
  const business = look.businessMotion;
  // Beside progressive cards already carry the claim — skip overlapping diagram.
  const showBusiness =
    !v14 &&
    Boolean(business?.component) &&
    !(sid === "beside" && (look.typography?.cards?.length || look.criteriaCards?.length));
  // V11.2: when BusinessMotion owns the beat, skip decorative float (avoids face/hair pile-up).
  const showFloat = Boolean(floatStaged) && !showBusiness;
  return (
    <AbsoluteFill>
      {body}
      {v14 ? (
        <SemanticMotion
          payload={{
            ...v14,
            sceneTheme: v14.sceneTheme || sceneThemeFromPlate(plate) || "photo",
          }}
          frames={frames}
        />
      ) : null}
      {showBusiness && business ? (
        <BusinessMotion
          motion={{
            ...business,
            sceneTheme: business.sceneTheme || sceneThemeFromPlate(plate) || "photo",
          }}
          frames={frames}
        />
      ) : null}
      {showFloat && floatStaged ? (
        <FloatingForeground
          staged={floatStaged}
          frames={frames}
          placement={floatObj?.placement || "speaker_left_lower"}
          areaShare={floatObj?.areaShare || 0.12}
          format={floatObj?.format}
          frameCount={floatObj?.frameCount}
          scaleProfile={floatObj?.scaleProfile}
          minPx={floatObj?.minPx}
          maxPx={floatObj?.maxPx}
        />
      ) : null}
      {/* Legacy boxed webm only when V9 did not substitute a float object. */}
      {!floatStaged && motionStaged && motionDisplay !== "omit" ? (
        <SemanticMotionClip staged={motionStaged} frames={frames} />
      ) : null}
    </AbsoluteFill>
  );
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
  const raw: { from: number; end: number; text: string }[] = [];
  for (const phrase of phrases) {
    const text = String(phrase.text || "").trim();
    if (!text) continue;
    const from = Math.max(0, Math.round(Number(phrase.start || 0) * fps));
    const end = Math.max(from + 1, Math.round(Number(phrase.end || 0) * fps));
    if (from >= totalFrames) continue;
    raw.push({ from, end: Math.min(totalFrames, end), text });
  }
  // Phrase grouping: merge short adjacent lines into 1–2 line mobile captions.
  const grouped: { from: number; end: number; text: string }[] = [];
  for (const row of raw) {
    const prev = grouped[grouped.length - 1];
    const gap = prev ? row.from - prev.end : 999;
    const combined = prev ? `${prev.text} ${row.text}`.trim() : row.text;
    const cjk = (value: string) => (value.match(/[\u4e00-\u9fff]/g) || []).length;
    // A Chinese sentence has no spaces. Gluing adjacent lines paints a caption wall.
    const canMerge =
      prev &&
      gap <= Math.round(0.35 * fps) &&
      combined.length <= 72 &&
      !prev.text.includes("\n") &&
      cjk(prev.text) <= 2 &&
      cjk(row.text) <= 2;
    if (canMerge && prev) {
      prev.end = row.end;
      prev.text = combined;
    } else {
      grouped.push({ ...row });
    }
  }
  return grouped.map((row) => ({
    from: row.from,
    duration: Math.max(1, row.end - row.from),
    text: row.text,
  }));
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
          left: 120,
          width: 840,
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
            maxWidth: 760,
            padding: "12px 28px 14px",
            borderRadius: 18,
            background: "rgba(8, 7, 6, 0.55)",
            boxShadow: "0 4px 16px rgba(0,0,0,0.28)",
          }}
        >
          <AutoFitText
            text={clean}
            maxWidth={680}
            maxHeight={152}
            role={{ min: 48, max: 64, weight: 700, lineHeight: 1.14, tracking: -0.02 }}
            align="center"
            vertical="center"
            wrapMode="auto"
            maxLines={2}
            emphasis={emphasis}
            animate="none"
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
          left: 140,
          right: 140,
          top: 1040,
          opacity: enter,
          transform: `translateY(${(1 - enter) * 28}px) scale(${0.96 + enter * 0.04})`,
        }}
      >
        <div
          style={{
            padding: "12px 8px",
            background: "transparent",
            boxShadow: "none",
          }}
        >
          <AutoFitText
            text={text}
            maxWidth={800}
            maxHeight={112}
            role={{ min: 40, max: 64, weight: 760, lineHeight: 1.08, tracking: -0.02 }}
            align="center"
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

function Hook({
  file,
  from,
  frames,
  look,
  locale = "ru-RU",
  suppressHeadline = false,
}: {
  file: string;
  from: number;
  frames: number;
  look: SceneLook;
  locale?: SupportedLocale;
  suppressHeadline?: boolean;
}) {
  const frame = useCurrentFrame();
  const baseZoom = layoutZoom(look.speaker.layout);
  const emphasis = look.sceneComposition?.speakerPresentation === "emphasis";
  // Mid-hook punch keeps the opener from reading as a locked still when the beat stretches.
  // Emphasis already uses speaker_medium. An extra punch would push the face into the title.
  const punchAt = Math.max(18, Math.round(frames * 0.42));
  const punch = emphasis ? 0 : interpolate(frame, [punchAt, punchAt + 16], [0, 0.12], clamp);
  const headline = suppressHeadline || look.emphasisRange?.length === 2
    ? ""
    : look.headline || look.typography?.headline || "";
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill>
        <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={baseZoom + punch} />
        </Move>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
        {headline ? <KineticHeadline text={headline} locale={locale} /> : null}
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

/** Split already used by Residency. The side panel is the spoken ordinal line, not a stock plate. */
function SpokenSplit({
  file,
  from,
  frames,
  look,
  locale = "en-US",
}: {
  file: string;
  from: number;
  frames: number;
  look: SceneLook;
  locale?: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  const steps = look.steps?.length ? look.steps : look.typography?.steps || [];
  const count = Math.max(1, steps.length);
  const slot = Math.min(count - 1, Math.max(0, Math.floor((frame / Math.max(1, frames)) * count)));
  const label = steps[slot] || steps[0] || "";
  const speakerBox = splitSpeakerRect("right");
  const mediaBox = splitMediaRect("left");
  const enter = interpolate(frame, [0, 12], [0, 1], clamp);
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        <div
          style={{
            position: "absolute",
            left: mediaBox.left,
            top: mediaBox.top,
            width: mediaBox.width,
            height: mediaBox.height,
            borderRadius: PORTRAIT.radius,
            overflow: "hidden",
            background: theme.color.bgElevated,
            opacity: enter,
            padding: 28,
            boxSizing: "border-box",
          }}
        >
          <AutoFitText
            text={label}
            maxWidth={Math.max(80, mediaBox.width - 56)}
            maxHeight={Math.max(80, mediaBox.height - 56)}
            role={theme.type.title}
            align="left"
            vertical="center"
            wrapMode="auto"
            maxLines={5}
            locale={locale}
          />
        </div>
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
          }}
        >
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.08} />
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

/** V9 steps: speaker stays primary; one large step label at a time — no card chrome. */
function CleanSteps({
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
  const copy = stepsCopy(locale);
  const title = look.stepsTitle || look.typography?.stepsTitle || copy.title;
  const stepLabels = look.steps?.length
    ? look.steps
    : look.typography?.steps?.length
      ? look.typography.steps
      : copy.steps.map((s) => s.label);
  const count = Math.max(1, stepLabels.length);
  const slot = Math.min(count - 1, Math.max(0, Math.floor((frame / Math.max(1, frames)) * count)));
  const label = stepLabels[slot] || stepLabels[0];
  const enter = interpolate(
    frame,
    [(slot * frames) / count, (slot * frames) / count + 10],
    [0, 1],
    clamp,
  );
  return (
    <Enter transition={look.transition}>
      <AbsoluteFill>
        <Move treatment={look.background.treatment || "static_editorial"} intensity={look.motionIntensity} frames={frames}>
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.1} />
        </Move>
        <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
        <AbsoluteFill style={{ pointerEvents: "none" }}>
          <div
            style={{
              position: "absolute",
              left: 56,
              right: 56,
              top: 200,
              opacity: enter,
              transform: `translateY(${(1 - enter) * 20}px)`,
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 600, color: theme.color.muted, marginBottom: 12, letterSpacing: 0.04 }}>
              {title}
            </div>
            {/* V11.2: never paint "{n} {label}" as one phrase — reads as invented headcount ("2 Shareholders"). */}
            <div style={{ fontSize: 28, fontWeight: 600, color: theme.color.accent, marginBottom: 8, letterSpacing: 0.06 }}>
              {locale.startsWith("zh") ? `步骤 ${slot + 1}` : locale.startsWith("en") ? `Step ${slot + 1}` : `Шаг ${slot + 1}`}
            </div>
            <div style={{ fontSize: 72, fontWeight: 800, color: theme.color.paper, letterSpacing: -0.03, lineHeight: 1.05 }}>
              {label}
            </div>
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    </Enter>
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
  const planLocale = (visualPlan?.language || locale || "en-US") as SupportedLocale;
  const sceneIds =
    visualPlan?.scenes?.length
      ? visualPlan.scenes.map((s) => s.sceneId)
      : ["hook", "residency", "consult", "beside", "steps", "return"];
  const weights =
    visualPlan?.beatWeights?.length === sceneIds.length
      ? visualPlan.beatWeights
      : undefined;
  const beatList = beatsFor(frames, weights);
  // Align beat count to scene count (pad/trim safely).
  while (beatList.length < sceneIds.length) {
    const last = beatList[beatList.length - 1] || { from: 0, duration: frames };
    beatList.push({ from: last.from + last.duration, duration: Math.max(1, Math.round(frames / sceneIds.length)) });
  }
  const looks = Object.fromEntries(sceneIds.map((id) => [id, sceneLook(visualPlan, id)])) as Record<string, SceneLook>;
  const transcriptCaptions = captionsFromTranscript(visualPlan?.captions, frames);
  const packCaptions = captionsForBeats(beatList, planLocale);
  const captionRows = transcriptCaptions.length ? transcriptCaptions : packCaptions;
  const hookHeadline = (looks.hook?.headline || looks.hook?.typography?.headline || "").trim();
  const captions = captionRows
    .map((row) => {
      let sceneId = sceneIds[0] || "hook";
      beatList.forEach((beat, index) => {
        if (row.from >= beat.from) sceneId = sceneIds[Math.min(index, sceneIds.length - 1)];
      });
      const animate = (looks[sceneId]?.typography?.animate || "fade") as "fade" | "pop" | "mask" | "slide";
      return { ...row, animate, sceneId };
    })
    .filter((row) => {
      if (!hookHeadline) return true;
      if (row.sceneId !== "hook") return true;
      const t = String(row.text || "").trim();
      // Hide only an exact duplicate of the title. A longer spoken line that
      // merely contains the title stays on screen, under the caption inset.
      return t !== hookHeadline;
    });
  const controls = visualPlan?.editingControls || null;
  const motionGain = editingMotionGain(controls);
  const cleanV9 = visualPlan?.compositionPolicy === "v9_clean" || visualPlan?.shotPlanVersion === "v9";
  // V9: composition budget — no competing concept stack on long-form.
  const conceptCap = cleanV9 ? 0 : Math.max(editingConceptCap(controls), durationSeconds >= 45 ? 10 : 0);
  const conceptOn = visualPlan?.conceptTriggers !== false && conceptCap > 0;
  const concepts: SyncedConceptTrigger[] = conceptOn
    ? syncConceptTriggers(captions, 1).slice(0, conceptCap)
    : [];
  // Skip only when the beat already owns a progressive card / steps diagram.
  const layoutOwned = sceneIds.map((id, index) => {
    const beat = beatList[index];
    const skip: string[] = [];
    if (id === "beside") skip.push("family_cluster", "budget_scale", "comparison_columns");
    if (id === "steps") skip.push("steps_reveal");
    return { from: beat.from, to: beat.from + beat.duration, skip };
  });
  const speakerPrimary = sceneIds
    .map((id, index) => {
      const framing = looks[id]?.speaker?.layout || "";
      if (framing.includes("with_media") || framing.includes("diagram") || id === "consult" || id === "proof" || id === "steps") {
        return null;
      }
      const beat = beatList[index];
      return { from: beat.from, to: beat.from + beat.duration };
    })
    .filter(Boolean) as { from: number; to: number }[];
  const plate = visualPlan?.backgroundPlate ?? null;
  const hookBeat = beatList[0];
  const hero = cleanV9 ? null : visualPlan?.heroObject ?? null;
  const heroBeat =
    beatList[sceneIds.indexOf("problem")] ||
    beatList[sceneIds.indexOf("hook")] ||
    hookBeat;
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
      {sceneIds.map((id, index) => {
        const beat = beatList[index];
        const look = looks[id];
        const intensity = (look.motionIntensity === "high" ? 1.2 : 0.85) * motionGain;
        return (
          <Sequence key={`${id}-${index}`} from={beat.from} durationInFrames={beat.duration} name={id}>
            {id === "hook" ? (
              <ParallaxLayers
                frames={beat.duration}
                intensity={intensity}
                layers={[
                  {
                    depth: 0.4,
                    children: (
                      <SceneRouter
                        look={look}
                        file={speakerFile}
                        from={beat.from}
                        frames={beat.duration}
                        locale={planLocale}
                        plate={plate}
                      />
                    ),
                  },
                ]}
              />
            ) : (
              <SceneRouter
                look={look}
                file={speakerFile}
                from={beat.from}
                frames={beat.duration}
                locale={planLocale}
                plate={plate}
              />
            )}
          </Sequence>
        );
      })}
      {concepts.map((hit) => {
        const owned = layoutOwned.find((range) => hit.fromFrame >= range.from && hit.fromFrame < range.to);
        if (owned && owned.skip.includes(hit.presetId)) return null;
        const beat = beatList.find((b) => hit.fromFrame >= b.from && hit.fromFrame < b.from + b.duration);
        const dur = Math.max(1, Math.min(hit.durationInFrames, (beat ? beat.from + beat.duration : frames) - hit.fromFrame));
        const speakerOn = speakerPrimary.some((range) => hit.fromFrame >= range.from && hit.fromFrame < range.to);
        const showPip = !speakerOn && dur >= 36;
        return (
          <Sequence key={`concept-${hit.fromFrame}-${hit.presetId}`} from={hit.fromFrame} durationInFrames={dur} name={`concept-${hit.presetId}`}>
            <ConceptViz hit={hit} frames={dur} />
            {showPip ? <Speaker file={speakerFile} startFrom={hit.fromFrame} zoomTo={1.14} circle /> : null}
          </Sequence>
        );
      })}
      {hero && heroBeat ? (
        <Sequence from={heroBeat.from} durationInFrames={Math.min(heroBeat.duration, Math.round(4.5 * DIRECTOR_V3_FPS))} name="hero-object">
          <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.92 }}>
            <HeroObject kind={hero} frames={Math.min(heroBeat.duration, Math.round(4.5 * DIRECTOR_V3_FPS))} />
          </AbsoluteFill>
        </Sequence>
      ) : null}
      {(visualPlan?.scenes || []).map((scene, index) => {
        const range = scene.emphasisRange;
        const title = (scene.headline || scene.typography?.headline || "").trim();
        if (!range || range.length !== 2 || !title) return null;
        if (scene.sceneComposition?.speakerPresentation !== "emphasis") return null;
        const lead = 0.4;
        const tail = 0.4;
        const start = Math.max(0, Number(range[0]) - lead);
        const end = Number(range[1]) + tail;
        const from = Math.max(0, Math.round(start * DIRECTOR_V3_FPS));
        const duration = Math.max(1, Math.round((end - start) * DIRECTOR_V3_FPS));
        return (
          <Sequence key={`emphasis-${scene.sceneId}-${index}`} from={from} durationInFrames={duration} name={`emphasis-${scene.sceneId}`}>
            <KineticHeadline text={title} locale={planLocale} />
          </Sequence>
        );
      })}
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
