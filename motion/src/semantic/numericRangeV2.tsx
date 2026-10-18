/**
 * Three presentations of one numeric-range model.
 * finance: translucent panel, stepped hierarchy.
 * editorial: type only, thick connector, no card.
 * split: the same stack in the graphic column.
 */
import { Easing, interpolate, useCurrentFrame } from "remotion";
import type { SupportedLocale } from "../localization/language-config";
import { theme, type TypeRole } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import type { SemanticMotionPayload } from "./types";
import {
  CONNECTOR_STROKE,
  buildRangeModel,
  graphicRect,
  rangeChoreography,
  type RangeModel,
  type RangePhase,
  type RangePresentation,
} from "./numericRangeModel";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const ease = Easing.out(Easing.cubic);

const HEADING: TypeRole = { min: 26, max: 32, weight: 600, lineHeight: 1.15, tracking: 0.02 };
const UNIT: TypeRole = { min: 26, max: 34, weight: 500, lineHeight: 1.15, tracking: 0.01 };
const LOW: Record<RangePresentation, TypeRole> = {
  finance: { min: 54, max: 64, weight: 560, lineHeight: 0.95, tracking: -0.03 },
  editorial: { min: 72, max: 88, weight: 600, lineHeight: 0.92, tracking: -0.04 },
  split: { min: 64, max: 80, weight: 600, lineHeight: 0.92, tracking: -0.04 },
};
const HIGH: Record<RangePresentation, TypeRole> = {
  finance: { min: 72, max: 86, weight: 640, lineHeight: 0.92, tracking: -0.04 },
  editorial: { min: 92, max: 112, weight: 640, lineHeight: 0.9, tracking: -0.045 },
  split: { min: 84, max: 104, weight: 640, lineHeight: 0.9, tracking: -0.045 },
};

function rise(frame: number, start: number, span = 8) {
  return interpolate(frame, [start, start + span], [0, 1], { ...clamp, easing: ease });
}

function Fit({
  text,
  width,
  height,
  role,
  color,
  locale,
  align = "left",
  maxLines = 3,
}: {
  text: string;
  width: number;
  height: number;
  role: TypeRole;
  color: string;
  locale: SupportedLocale;
  align?: "left" | "center";
  maxLines?: number;
}) {
  if (!text) return null;
  return (
    <div style={{ width, height }}>
      <AutoFitText
        text={text}
        maxWidth={width}
        maxHeight={height}
        role={role}
        align={align}
        vertical="center"
        locale={locale}
        color={color}
        wrapMode={locale === "zh-CN" ? "auto" : "word"}
        maxLines={maxLines}
      />
    </div>
  );
}

function Connector({
  width,
  stroke,
  grow,
  ink,
  outline,
}: {
  width: number;
  stroke: number;
  grow: number;
  ink: string;
  outline: string;
}) {
  const h = stroke + 10;
  const mid = h / 2;
  const cap = stroke;
  const x2 = cap + Math.max(0, width - cap * 2) * grow;
  return (
    <svg width={width} height={h} aria-hidden>
      <line x1={cap} y1={mid} x2={x2} y2={mid} stroke={outline} strokeWidth={stroke + 8} strokeLinecap="butt" />
      <line x1={cap} y1={mid} x2={x2} y2={mid} stroke={ink} strokeWidth={stroke} strokeLinecap="butt" />
      <rect x={0} y={mid - stroke / 2} width={stroke} height={stroke} fill={outline} />
      <rect x={2} y={mid - stroke / 2 + 2} width={stroke - 4} height={stroke - 4} fill={ink} />
      <rect x={width - stroke} y={mid - stroke / 2} width={stroke} height={stroke} fill={outline} opacity={grow} />
      <rect
        x={width - stroke + 2}
        y={mid - stroke / 2 + 2}
        width={stroke - 4}
        height={stroke - 4}
        fill={ink}
        opacity={grow}
      />
    </svg>
  );
}

function Stack({
  model,
  phase,
  presentation,
  ink,
  muted,
  accent,
  outline,
}: {
  model: RangeModel;
  phase: RangePhase;
  presentation: RangePresentation;
  ink: string;
  muted: string;
  accent: string;
  outline: string;
}) {
  const frame = useCurrentFrame();
  const rect = graphicRect(presentation);
  const pad = presentation === "finance" ? 22 : 0;
  const inner = rect.width - pad * 2;
  const titleIn = rise(frame, 0, phase.enter);
  const lowIn = rise(frame, phase.lowAt, 8);
  const highIn = rise(frame, phase.highAt, 8);
  const connect = rise(frame, phase.connectAt, Math.max(6, phase.connectEnd - phase.connectAt));
  const emphasis = rise(frame, phase.emphasisAt, 8);
  const exit = interpolate(frame, [phase.exitAt, Math.max(phase.exitAt + 1, phase.frames - 1)], [1, 0], clamp);
  const shadow = presentation === "finance" ? "none" : `0 2px 0 ${outline}, 0 10px 18px rgba(12,11,10,0.45)`;
  return (
    <div
      style={{
        width: rect.width,
        boxSizing: "border-box",
        padding: pad,
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-start",
        gap: presentation === "editorial" ? 14 : 12,
        opacity: exit,
        transform: `translateY(${(1 - titleIn) * 14}px)`,
        background: presentation === "finance" ? "rgba(18,17,15,0.46)" : "transparent",
        border: presentation === "finance" ? "1px solid rgba(246,241,232,0.28)" : "none",
        borderRadius: presentation === "finance" ? 22 : 0,
      }}
    >
      <div style={{ opacity: titleIn, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, textShadow: shadow }}>
        <Fit text={model.heading} width={inner * 0.48} height={78} role={HEADING} color={muted} locale={model.locale} maxLines={2} />
        <Fit text={model.unit} width={inner * 0.5} height={40} role={UNIT} color={ink} locale={model.locale} align="center" maxLines={1} />
      </div>
      <div style={{ opacity: lowIn, transform: `translateY(${(1 - lowIn) * 10}px)` }}>
        <div style={{ textShadow: shadow }}>
          <Fit text={model.lowDisplay} width={inner} height={LOW[presentation].max + 8} role={LOW[presentation]} color={ink} locale={model.locale} />
        </div>
      </div>
      <div style={{ opacity: Math.max(connect, 0.001) }}>
        <Connector width={inner} stroke={CONNECTOR_STROKE[presentation]} grow={connect} ink={ink} outline={outline} />
      </div>
      <div style={{ opacity: highIn, transform: `translateY(${(1 - highIn) * 10}px)` }}>
        <div style={{ textShadow: shadow }}>
          <Fit text={model.highDisplay} width={inner} height={HIGH[presentation].max + 12} role={HIGH[presentation]} color={ink} locale={model.locale} />
        </div>
        <div
          style={{
            marginTop: 8,
            height: 6,
            width: inner * emphasis,
            background: accent,
            boxShadow: presentation === "finance" ? "none" : `0 0 0 2px ${outline}`,
          }}
        />
      </div>
    </div>
  );
}

export function NumericRangeV2({
  presentation,
  payload,
  locale,
  frames,
}: {
  presentation: RangePresentation;
  payload: SemanticMotionPayload;
  locale: SupportedLocale;
  frames: number;
}) {
  const model = buildRangeModel(payload, locale);
  if (!model) return null;
  const phase = rangeChoreography(frames);
  const onPanel = presentation === "finance";
  return (
    <Stack
      model={model}
      phase={phase}
      presentation={presentation}
      ink={onPanel ? theme.color.ink : theme.color.ink}
      muted={onPanel ? "rgba(246,241,232,0.78)" : theme.color.ink}
      accent={onPanel ? theme.color.accent : theme.color.ink}
      outline="rgba(12,11,10,0.92)"
    />
  );
}
