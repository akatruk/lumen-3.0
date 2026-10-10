import type { ReactNode } from "react";
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { LocaleProvider } from "../typography/locale";
import { AutoFitText } from "../typography/AutoFitText";
import { normalizeScene } from "../registry/validateScene";
import { renderScene } from "../registry/motionRegistry";
import { ConceptViz, syncConceptTriggers, type SyncedConceptTrigger } from "../concepts";
import { BackgroundPlate, HeroObject, ParallaxLayers } from "../cinematic";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const media = (name: string) => staticFile(`director-v3/${name}`);

export const DIRECTOR_V3_FPS = 30;
export const DIRECTOR_V3_FRAMES = 600;
const BEAT_FRAMES = [90, 132, 120, 132, 81, 45] as const;

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
};

export type DirectorV3Props = {
  durationSeconds?: number;
  speakerFile?: string;
  visualPlan?: VisualPlan | null;
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
  const opacity = interpolate(frame, [0, 10], [0, 1], clamp);
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
}

function Caption({ text, emphasis, animate = "fade" }: { text: string; emphasis?: string[]; animate?: "fade" | "pop" | "mask" | "slide" }) {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 72,
          width: 936,
          bottom: 280,
          height: 220,
        }}
      >
        <AutoFitText
          text={text}
          maxWidth={936}
          maxHeight={180}
          role={{ min: 56, max: 84, weight: 600, lineHeight: 1.08, tracking: -0.02 }}
          align="center"
          vertical="end"
          wrapMode="auto"
          maxLines={2}
          emphasis={emphasis}
          animate={animate}
          locale="ru-RU"
        />
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
  return (
    <AbsoluteFill style={{ alignItems: "flex-end", justifyContent: "flex-end", padding: "0 48px 360px 0" }}>
      <div
        style={{
          width: 220,
          height: 220,
          borderRadius: "50%",
          overflow: "hidden",
          border: `3px solid ${theme.color.lineStrong}`,
          boxShadow: theme.shadow.soft,
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

function Residency({ file, from, frames, look }: { file: string; from: number; frames: number; look: SceneLook }) {
  const frame = useCurrentFrame();
  const treatment = look.foreground.treatment;
  const rise = treatment === "slide_up" || treatment === "scale_reveal" ? interpolate(frame, [8, 28], [64, 0], clamp) : 0;
  const slide = treatment === "slide_left" ? interpolate(frame, [6, 22], [90, 0], clamp) : 0;
  const scale = treatment === "scale_reveal" ? interpolate(frame, [8, 28], [0.86, 1], clamp) : 1;
  const opacity = interpolate(frame, [6, 18], [0, 1], clamp);
  const speakerRight = look.speaker.layout === "speaker_split_right";
  const staged = look.background.staged;
  const motionPlate = Boolean(staged && /\.(mp4|webm|mov)$/i.test(staged));
  const plate = staged && !motionPlate ? staged : null;
  return (
    <Enter transition={look.transition}>
    <AbsoluteFill style={{ background: theme.color.bg }}>
      <div
        style={{
          position: "absolute",
          left: speakerRight ? undefined : 36,
          right: speakerRight ? 36 : undefined,
          top: 160,
          width: 620,
          height: 1180,
          borderRadius: 32,
          overflow: "hidden",
        }}
      >
        {plate || motionPlate ? (
          <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.06} />
        ) : (
          <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
            <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.06} />
          </Move>
        )}
      </div>
      <div
        style={{
          position: "absolute",
          right: speakerRight ? undefined : 0,
          left: speakerRight ? 0 : undefined,
          top: 340,
          width: 460,
          height: 780,
          opacity,
          transform: `translate(${slide}px, ${rise}px) scale(${scale})`,
        }}
      >
        {motionPlate && staged ? (
          <OffthreadVideo src={media(staged)} volume={0} style={{ width: "100%", height: "70%", objectFit: "cover", borderRadius: 24 }} />
        ) : null}
        {plate ? (
          <Move treatment={look.background.treatment} intensity={look.motionIntensity} frames={frames}>
            <Img src={media(plate)} style={{ width: "100%", height: "70%", objectFit: "cover", borderRadius: 24 }} />
          </Move>
        ) : null}
        <Img
          src={media(look.foreground.staged || "passport.png")}
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            width: "100%",
            height: plate || motionPlate ? "46%" : "100%",
            objectFit: "contain",
          }}
        />
      </div>
      <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
    </AbsoluteFill>
    </Enter>
  );
}

function Consult({ frames, look }: { frames: number; look: SceneLook }) {
  const still = look.background.staged;
  const motionPlate = Boolean(still && /\.(mp4|webm|mov)$/i.test(still));
  return (
    <Enter transition={look.transition}>
    <AbsoluteFill>
      <Move treatment={motionPlate || !still ? "ambient_loop" : look.background.treatment} intensity={look.motionIntensity} frames={frames}>
        {still && !motionPlate ? (
          <Img src={media(still)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : (
          <OffthreadVideo
            src={media(motionPlate && still ? still : "consult.mp4")}
            volume={0}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        )}
      </Move>
      <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
    </AbsoluteFill>
    </Enter>
  );
}

function Beside({ file, from, frames, look }: { file: string; from: number; frames: number; look: SceneLook }) {
  const frame = useCurrentFrame();
  const pace = frames / 132;
  const words = ["Цели", "Семья", "Бюджет"];
  const speakerLeft = look.speaker.layout === "speaker_split_left";
  return (
    <Enter transition={look.transition}>
    <AbsoluteFill style={{ background: theme.color.bg }}>
      <div style={{ position: "absolute", left: speakerLeft ? undefined : 48, right: speakerLeft ? 48 : undefined, top: 360, width: 440 }}>
        {words.map((word, index) => {
          const shown = interpolate(frame, [(10 + index * 16) * pace, (24 + index * 16) * pace], [0, 1], clamp);
          return (
            <div
              key={word}
              style={{
                opacity: shown,
                transform: `translateY(${(1 - shown) * 24}px)`,
                marginBottom: 28,
                padding: "22px 28px",
                borderRadius: 18,
                background: theme.color.bgElevated,
                border: `1px solid ${theme.color.lineStrong}`,
              }}
            >
              <AutoFitText
                text={word}
                maxWidth={380}
                maxHeight={72}
                role={theme.type.title}
                align="left"
                vertical="center"
                locale="ru-RU"
              />
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          right: speakerLeft ? undefined : 36,
          left: speakerLeft ? 36 : undefined,
          top: 180,
          width: 520,
          height: 1240,
          borderRadius: 28,
          overflow: "hidden",
        }}
      >
        <Speaker file={file} startFrom={from} frames={frames} zoomTo={1.04} />
      </div>
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

export function DirectorV3({ durationSeconds = 20, speakerFile = "speaker.mp4", visualPlan = null }: DirectorV3Props) {
  const frames = framesForSeconds(durationSeconds);
  const [hook, residency, consult, beside, steps, ret] = beatsFor(frames);
  const scale = frames / DIRECTOR_V3_FRAMES;
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
  const plate = visualPlan?.backgroundPlate ?? null;
  const hero = visualPlan?.heroObject ?? null;
  return (
    <AbsoluteFill style={{ background: theme.color.bg, fontFamily: theme.font.sans }}>
      <LocaleProvider locale="ru-RU">
      <Audio src={media(speakerFile)} volume={1.6} />
      <Audio src={media("bed.mp3")} volume={(frame) => bedVolume(frame, frames)} />
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
        <Beside file={speakerFile} from={beside.from} frames={beside.duration} look={looks.beside} />
      </Sequence>
      <Sequence from={steps.from} durationInFrames={steps.duration} name="steps">
        <Enter transition={looks.steps.transition}>
          <Steps frames={steps.duration} />
        </Enter>
      </Sequence>
      <Sequence from={ret.from} durationInFrames={ret.duration} name="return">
        <Return file={speakerFile} from={ret.from} frames={ret.duration} look={looks.return} />
      </Sequence>
      {concepts.map((hit) => (
        <Sequence key={`concept-${hit.fromFrame}-${hit.presetId}`} from={hit.fromFrame} durationInFrames={hit.durationInFrames} name={`concept-${hit.presetId}`}>
          <ConceptViz hit={hit} frames={hit.durationInFrames} />
          <Speaker file={speakerFile} startFrom={hit.fromFrame} zoomTo={1.2} circle />
        </Sequence>
      ))}
      {hero ? (
        <Sequence from={residency.from} durationInFrames={residency.duration} name="hero-object">
          <AbsoluteFill style={{ pointerEvents: "none", opacity: 0.92 }}>
            <HeroObject kind={hero} frames={residency.duration} />
          </AbsoluteFill>
        </Sequence>
      ) : null}
      {captions.map((row) => (
        <Sequence key={row.from} from={row.from} durationInFrames={row.duration} name={`cap-${row.from}`}>
          <Caption text={row.text} emphasis={row.emphasis} animate={row.animate} />
        </Sequence>
      ))}
      </LocaleProvider>
    </AbsoluteFill>
  );
}
