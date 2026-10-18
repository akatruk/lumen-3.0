/**
 * Family plate, excerpt 16.52 through the cost handoff.
 * Times are excerpt-relative. Source = excerpt + 42.80.
 * Same six V4 plates. No house icon.
 */
import { Img, staticFile } from "remotion";
import type { SupportedLocale } from "../../localization/language-config";
import { AutoFitText } from "../../typography/AutoFitText";
import { theme } from "../../themes/tokens";
import { SPEAKER_COST, SPEAKER_SCENE, easeOut, enterFrame } from "./model";

const PAPER = "#f3eee6";
const ACCENT = "#9c3b2e";

const START = enterFrame(16.52);
const CORE = enterFrame(18.76);
const EXTENDED = enterFrame(20.68);
const DEFINITION = enterFrame(23.6);
const HOUSEHOLD = enterFrame(24.92);
const PARENTS = enterFrame(28.56);
const COST = enterFrame(30.44);
const HANDOFF = 14;
const FEET = 1572;

const ASK: Record<SupportedLocale, string> = {
  "zh-CN": "能否一起申请",
  "en-US": "Apply together?",
  "ru-RU": "Подать вместе?",
};
const DIFFER: Record<SupportedLocale, string> = {
  "zh-CN": "定义不同",
  "en-US": "Definitions differ",
  "ru-RU": "Определения разные",
};

export type FamilyLines = {
  title: string;
  core: string;
  household: string;
  parents: string;
};

type Kind = "adultA" | "adultB" | "child" | "youth" | "elderA" | "elderB";
export type Box = { left: number; top: number; width: number; height: number };

const RATIO: Record<Kind, number> = {
  adultA: 329 / 1082,
  adultB: 308 / 1102,
  child: 397 / 1018,
  youth: 306 / 1070,
  elderA: 328 / 1094,
  elderB: 345 / 1122,
};

const FILE: Record<Kind, string> = {
  adultA: "adult-a.png",
  adultB: "adult-b.png",
  child: "child.png",
  youth: "youth.png",
  elderA: "elder-a.png",
  elderB: "elder-b.png",
};

export const SPEAKER_OPEN = { left: 36, top: 180, width: 700, height: 1180 };
export const SPEAKER_DOCK = { left: 28, top: 36, width: 300, height: 456 };
export const SPEAKER_EMPHASIS = { left: 36, top: 48, width: 390, height: 600 };

const CORE_H = { adultA: 880, adultB: 860, child: 590 };
const EXT_H = { youth: 620, elderA: 720, elderB: 740 };

function rise(frame: number, at: number, frames: number): number {
  return easeOut((frame - at) / frames);
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function boxOf(kind: Kind, left: number, height: number, feet: number): Box {
  const width = height * RATIO[kind];
  return { left, top: feet - height, width, height };
}

export function familyHandoff(_frame: number): number {
  return 0;
}

export function familyStageActive(frame: number): boolean {
  return frame >= START && frame < COST + HANDOFF;
}

export function familySpeakerRect(frame: number, fallback: Box): Box {
  const openIn = START + 14;
  const dockIn = CORE + 16;
  const emphasisIn = DEFINITION + 10;
  const dockBack = HOUSEHOLD + 12;
  if (frame < START) return fallback;
  if (frame < openIn) return lerpBox(SPEAKER_SCENE, SPEAKER_OPEN, rise(frame, START, 14));
  if (frame < CORE) return SPEAKER_OPEN;
  if (frame < dockIn) return lerpBox(SPEAKER_OPEN, SPEAKER_DOCK, rise(frame, CORE, 16));
  if (frame < DEFINITION) return SPEAKER_DOCK;
  if (frame < emphasisIn) return lerpBox(SPEAKER_DOCK, SPEAKER_EMPHASIS, rise(frame, DEFINITION, 10));
  if (frame < HOUSEHOLD) return SPEAKER_EMPHASIS;
  if (frame < dockBack) return lerpBox(SPEAKER_EMPHASIS, SPEAKER_DOCK, rise(frame, HOUSEHOLD, 12));
  if (frame < COST) return SPEAKER_DOCK;
  if (frame < COST + HANDOFF) return lerpBox(SPEAKER_DOCK, SPEAKER_COST, rise(frame, COST, HANDOFF));
  return fallback;
}

function lerpBox(a: Box, b: Box, t: number): Box {
  return {
    left: lerp(a.left, b.left, t),
    top: lerp(a.top, b.top, t),
    width: lerp(a.width, b.width, t),
    height: lerp(a.height, b.height, t),
  };
}

export type FamilyPose = {
  people: { kind: Kind; box: Box; opacity: number }[];
  title: Box;
  labelTop: number;
  connector: { x1: number; x2: number; y: number; opacity: number } | null;
};

export function familyPose(frame: number): FamilyPose {
  const spread = rise(frame, EXTENDED, 18);
  const core = rise(frame, CORE, 12);
  const childIn = rise(frame, CORE + 5, 12);
  const spouseIn = rise(frame, CORE + 9, 12);
  const kin = rise(frame, EXTENDED + 5, 14);
  const elders = rise(frame, EXTENDED + 8, 14);
  const defined = frame >= DEFINITION && frame < HOUSEHOLD;
  const household = frame >= HOUSEHOLD && frame < PARENTS;
  const parents = frame >= PARENTS;
  const coreDim = parents ? 0.4 : 1;
  const kinDim = household ? 0.36 : 1;
  const coreWidth = CORE_H.adultA * RATIO.adultA + 52 + CORE_H.adultB * RATIO.adultB;
  const extWidth = EXT_H.elderA * RATIO.elderA + 24 + EXT_H.elderB * RATIO.elderB;
  const coreLeft = lerp((1080 - coreWidth) / 2, 12, spread);
  const extLeft = lerp(1120, coreLeft + coreWidth + 28, spread);
  const adultA = boxOf("adultA", coreLeft, CORE_H.adultA, FEET);
  const adultB = boxOf("adultB", coreLeft + CORE_H.adultA * RATIO.adultA + 52, CORE_H.adultB, FEET);
  const childW = CORE_H.child * RATIO.child;
  const child = boxOf("child", coreLeft + (coreWidth - childW) / 2, CORE_H.child, FEET);
  const elderA = boxOf("elderA", extLeft, EXT_H.elderA, FEET);
  const elderB = boxOf("elderB", extLeft + EXT_H.elderA * RATIO.elderA + 24, EXT_H.elderB, FEET);
  const youthW = EXT_H.youth * RATIO.youth;
  const youth = boxOf("youth", extLeft + (extWidth - youthW) / 2, EXT_H.youth, FEET);
  const titleT = frame < CORE ? 0 : frame < CORE + 16 ? rise(frame, CORE, 16) : 1;
  const title = lerpBox(
    { left: 760, top: 240, width: 280, height: 140 },
    { left: 448, top: 48, width: 590, height: 110 },
    titleT,
  );
  return {
    people: [
      { kind: "adultA", box: adultA, opacity: core * coreDim },
      { kind: "adultB", box: adultB, opacity: spouseIn * coreDim },
      { kind: "child", box: child, opacity: childIn * coreDim },
      { kind: "elderA", box: elderA, opacity: elders * kinDim },
      { kind: "elderB", box: elderB, opacity: elders * kinDim },
      { kind: "youth", box: youth, opacity: kin * kinDim },
    ],
    title,
    labelTop: 1596,
    connector:
      spread > 0.35
        ? {
            x1: adultB.left + adultB.width - 8,
            x2: elderA.left + 8,
            y: FEET - 460,
            opacity: kin * (defined ? 1 : 0.65) * (household ? 0.25 : 1),
          }
        : null,
  };
}

export function familyLabel(frame: number, locale: SupportedLocale, lines: FamilyLines): string {
  const spread = rise(frame, EXTENDED, 18);
  const core = rise(frame, CORE, 12);
  if (frame >= PARENTS) return lines.parents;
  if (frame >= HOUSEHOLD) return lines.household;
  if (frame >= DEFINITION) return DIFFER[locale];
  if (spread > 0.02) return ASK[locale];
  if (core > 0.02) return lines.core;
  return "";
}

function Person({ kind, box, opacity }: { kind: Kind; box: Box; opacity: number }) {
  if (opacity <= 0.01) return null;
  return (
    <div style={{ position: "absolute", left: box.left, top: box.top, width: box.width, height: box.height, opacity }}>
      <Img src={staticFile(`gold/family-v4/${FILE[kind]}`)} style={{ width: "100%", height: "100%", objectFit: "fill" }} />
    </div>
  );
}

export function FamilyStage({ frame, locale, lines }: { frame: number; locale: SupportedLocale; lines: FamilyLines }) {
  const pose = familyPose(frame);
  const exit = frame < COST ? 1 : 1 - rise(frame, COST, HANDOFF);
  const label = familyLabel(frame, locale, lines);
  const defined = frame >= DEFINITION && frame < HOUSEHOLD;
  const corePeople = pose.people.filter((p) => p.kind === "adultA" || p.kind === "adultB" || p.kind === "child");
  const extPeople = pose.people.filter((p) => p.kind === "elderA" || p.kind === "elderB" || p.kind === "youth");
  const show = (group: typeof corePeople) => group.some((p) => p.opacity > 0.2);
  const span = (group: typeof corePeople) => {
    const left = Math.min(...group.map((p) => p.box.left));
    const right = Math.max(...group.map((p) => p.box.left + p.box.width));
    return { left, right };
  };
  return (
    <div style={{ position: "absolute", inset: 0, opacity: exit, pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: pose.title.left, top: pose.title.top, width: pose.title.width, opacity: frame >= COST ? 0 : 1 }}>
        <AutoFitText text={lines.title} maxWidth={pose.title.width} maxHeight={108} role={theme.type.title} color={PAPER} locale={locale} />
      </div>
      {show(corePeople) ? <Ground span={span(corePeople)} opacity={Math.max(...corePeople.map((p) => p.opacity))} /> : null}
      {show(extPeople) ? <Ground span={span(extPeople)} opacity={Math.max(...extPeople.map((p) => p.opacity))} /> : null}
      {pose.connector ? (
        <svg style={{ position: "absolute", inset: 0 }} width={1080} height={1920} aria-hidden>
          <path
            d={`M${pose.connector.x1} ${pose.connector.y} H${pose.connector.x2}`}
            stroke={defined ? ACCENT : PAPER}
            strokeWidth={4}
            strokeDasharray="2 10"
            strokeLinecap="round"
            fill="none"
            opacity={pose.connector.opacity}
          />
        </svg>
      ) : null}
      {pose.people.filter((p) => p.kind !== "child" && p.kind !== "youth").map((p) => (
        <Person key={p.kind} kind={p.kind} box={p.box} opacity={p.opacity} />
      ))}
      {pose.people.filter((p) => p.kind === "child" || p.kind === "youth").map((p) => (
        <Person key={p.kind} kind={p.kind} box={p.box} opacity={p.opacity} />
      ))}
      {label ? (
        <div style={{ position: "absolute", left: 48, top: pose.labelTop, width: 984 }}>
          <AutoFitText text={label} maxWidth={984} maxHeight={52} role={theme.type.title} color={defined ? ACCENT : PAPER} locale={locale} />
        </div>
      ) : null}
    </div>
  );
}

function Ground({ span, opacity }: { span: { left: number; right: number }; opacity: number }) {
  return (
    <div
      style={{
        position: "absolute",
        left: span.left + 16,
        top: FEET - 8,
        width: Math.max(40, span.right - span.left - 32),
        height: 10,
        borderRadius: 8,
        background: PAPER,
        opacity: 0.55 * opacity,
      }}
    />
  );
}
