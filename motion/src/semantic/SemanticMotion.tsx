/**
 * Semantic motion V14 — five components, three layouts, one renderer.
 * Frame-driven. Labels are props (RU/EN/ZH). No invented amounts or counts.
 */
import { AbsoluteFill, Easing, interpolate, Sequence, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import type { SupportedLocale } from "../localization/language-config";
import { useLocale } from "../typography/locale";
import {
  adaptiveLineStyle,
  parseColor,
  relativeLuminance,
  type BackgroundProbe,
  type SceneTheme,
} from "../utils/adaptiveLineStyle";
import { ConnectorLine } from "../preview/ConnectorStroke";
import { motionDuration } from "./design";
import { compositionClears, resolveLayout, type LayoutVariant, type MediaSide } from "./layouts";
import { V15Body } from "./componentsV15";
import type { SemanticMotionPayload, SplitValue } from "./types";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const ease = Easing.out(Easing.cubic);

function localeOf(payload: SemanticMotionPayload, fallback: SupportedLocale): SupportedLocale {
  const raw = payload.locale || fallback;
  if (raw.startsWith("zh")) return "zh-CN";
  if (raw.startsWith("en")) return "en-US";
  if (raw.startsWith("ru")) return "ru-RU";
  return fallback;
}

function inkFor(payload: SemanticMotionPayload) {
  const sceneTheme: SceneTheme = payload.sceneTheme || "photo";
  const background =
    payload.connectorBackground ||
    (sceneTheme === "paper"
      ? theme.color.paper
      : sceneTheme === "navy"
        ? "#0F1720"
        : sceneTheme === "ink"
          ? theme.color.bg
          : { kind: "samples" as const, colors: ["#3A332C", "#E8DFD0", "#2A2520"] });
  const line = adaptiveLineStyle({
    background,
    path: [
      { x: 8, y: 8 },
      { x: 120, y: 80 },
      { x: 240, y: 40 },
    ],
    preferredColor: theme.color.accent,
    strokeWidth: 2.5,
    sceneTheme,
    minContrast: 3,
  });
  const onPaper = sceneTheme === "paper" || backgroundIsLight(background);
  return {
    sceneTheme,
    background,
    stroke: line.strokeColor,
    outline: line.outlineColor,
    text: onPaper ? theme.color.paperInk : theme.color.ink,
    muted: onPaper ? "rgba(26,23,20,0.62)" : theme.color.muted,
    plate: onPaper ? "rgba(244,239,230,0.78)" : "rgba(18,17,15,0.22)",
  };
}

function backgroundIsLight(background: BackgroundProbe | undefined): boolean {
  if (!background) return false;
  if (typeof background === "string") {
    const rgb = parseColor(background);
    return rgb ? relativeLuminance(rgb) > 0.45 : false;
  }
  if (background.kind === "solid") {
    const rgb = parseColor(background.color);
    return rgb ? relativeLuminance(rgb) > 0.45 : false;
  }
  if (background.kind === "samples") {
    const values = background.colors
      .map((color) => parseColor(color))
      .filter((rgb): rgb is NonNullable<typeof rgb> => Boolean(rgb))
      .map((rgb) => relativeLuminance(rgb));
    if (!values.length) return false;
    return values.reduce((sum, value) => sum + value, 0) / values.length > 0.45;
  }
  return false;
}

export function rise(frame: number, start: number) {
  const end = start + motionDuration.fadeIn;
  return {
    opacity: interpolate(frame, [start, end], [0, 1], { ...clamp, easing: ease }),
    y: interpolate(frame, [start, end], [16, 0], { ...clamp, easing: ease }),
  };
}

export function Label({
  text,
  width,
  height,
  locale,
  color,
  role = "label" as const,
}: {
  text: string;
  width: number;
  height: number;
  locale: SupportedLocale;
  color: string;
  role?: "label" | "title" | "support";
}) {
  if (!text) return null;
  const spec = role === "title" ? theme.type.title : role === "support" ? theme.type.support : theme.type.label;
  return (
    <div style={{ width, maxWidth: "100%", color, textAlign: "center" }}>
      <AutoFitText
        text={text}
        maxWidth={width}
        maxHeight={height}
        role={spec}
        align="center"
        vertical="center"
        locale={locale}
        color={color}
      />
    </div>
  );
}

function CapitalFlow({
  payload,
  palette,
  locale,
}: {
  payload: SemanticMotionPayload;
  palette: ReturnType<typeof inkFor>;
  locale: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  const entities = (payload.entities || []).filter((e) => e.label).slice(0, 4);
  if (entities.length < 2) return null;
  return (
    <div style={{ width: "100%", height: "100%", position: "relative", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "space-evenly" }}>
      {entities.map((entity, i) => {
        const shown = rise(frame, 4 + i * motionDuration.stagger);
        const next = entities[i + 1];
        const draw = next
          ? interpolate(frame, [10 + i * motionDuration.stagger, 10 + i * motionDuration.stagger + motionDuration.draw], [0, 1], { ...clamp, easing: ease })
          : 0;
        return (
          <div key={entity.id || entity.label} style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>
            <div style={{ opacity: shown.opacity, transform: `translateY(${shown.y}px)`, display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <svg width="72" height="72" viewBox="0 0 72 72">
                <circle cx="36" cy="36" r="26" fill={palette.plate} stroke={palette.stroke} strokeWidth="1.75" />
                <circle cx="36" cy="36" r="4" fill={palette.stroke} />
              </svg>
              <Label text={entity.label} width={280} height={48} locale={locale} color={palette.text} role="support" />
              {entity.amount ? (
                <Label text={entity.amount} width={220} height={36} locale={locale} color={palette.muted} />
              ) : null}
            </div>
            {next ? (
              <svg width="40" height="64" viewBox="0 0 40 64" style={{ marginTop: 4 }}>
                <ConnectorLine
                  x1={20}
                  y1={4}
                  x2={20}
                  y2={4 + draw * 44}
                  strokeWidth={2.25}
                  preferredColor={theme.color.accent}
                  background={palette.background}
                  sceneTheme={palette.sceneTheme}
                  strokeLinecap="round"
                />
                <polygon
                  points="12,44 20,58 28,44"
                  fill={palette.stroke}
                  opacity={draw}
                />
              </svg>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function ShareholderNetwork({
  payload,
  palette,
  locale,
}: {
  payload: SemanticMotionPayload;
  palette: ReturnType<typeof inkFor>;
  locale: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  const company = payload.company || payload.labels?.company || "";
  const named = (payload.shareholders || []).filter(Boolean);
  const counted = payload.showCount && payload.nodeCount ? Math.max(1, Math.min(6, payload.nodeCount)) : 0;
  const nodes = named.length
    ? named
    : counted
      ? Array.from({ length: counted }, (_, i) => payload.labels?.node || String(i + 1))
      : [payload.labels?.group || ""];
  const visible = nodes.filter(Boolean).slice(0, 6);
  if (!company || !visible.length) return null;
  const prefix = payload.showCount ? payload.countPrefix || "" : "";
  const countText = payload.showCount && payload.nodeCount ? `${prefix}${payload.nodeCount}` : "";
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      {countText ? (
        <div style={{ color: palette.text, fontSize: 42, fontWeight: 700, fontVariantNumeric: "tabular-nums", marginBottom: 8 }}>
          {countText}
        </div>
      ) : null}
      <div style={{ position: "relative", width: "100%", height: 260 }}>
      <svg width="100%" height="260" viewBox="0 0 640 260">
        {visible.map((label, i) => {
          const t = visible.length === 1 ? 0.5 : i / (visible.length - 1);
          const x = 70 + t * 500;
          const y = 78;
          const drawn = interpolate(frame, [6 + i * (payload.showCount ? 0 : motionDuration.stagger), 18 + i * (payload.showCount ? 0 : motionDuration.stagger)], [0, 1], clamp);
          return (
            <g key={`${label}-${i}`} opacity={drawn}>
              <ConnectorLine
                x1={x}
                y1={y + 28}
                x2={320}
                y2={200}
                strokeWidth={1.6}
                preferredColor={theme.color.accent}
                background={palette.background}
                sceneTheme={palette.sceneTheme}
                opacity={drawn}
              />
              <circle cx={x} cy={y} r="22" fill={palette.plate} stroke={palette.stroke} strokeWidth="1.6" />
            </g>
          );
        })}
        <circle cx="320" cy="230" r="28" fill={palette.plate} stroke={palette.stroke} strokeWidth="2" />
      </svg>
      <div style={{ position: "absolute", left: 0, right: 0, top: 8, display: "flex", justifyContent: "space-around" }}>
        {visible.map((label, i) => (
          <Label key={`${label}-t-${i}`} text={counted && !named.length ? "" : label} width={140} height={36} locale={locale} color={palette.text} />
        ))}
      </div>
      </div>
      <Label text={company} width={280} height={44} locale={locale} color={palette.text} role="support" />
    </div>
  );
}

function BusinessComparison({
  payload,
  palette,
  locale,
  compact,
}: {
  payload: SemanticMotionPayload;
  palette: ReturnType<typeof inkFor>;
  locale: SupportedLocale;
  compact: boolean;
}) {
  const frame = useCurrentFrame();
  const left = rise(frame, 4);
  const right = rise(frame, 4 + motionDuration.stagger);
  const op = interpolate(frame, [18, 32], [0, 1], { ...clamp, easing: ease });
  const operator = payload.operator || "→";
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: compact ? "column" : "row", alignItems: "center", justifyContent: "center", gap: 12, overflow: "hidden" }}>
      <Plate label={payload.left || ""} locale={locale} palette={palette} motion={left} compact={compact} />
      <div style={{ opacity: op, color: palette.text, fontSize: 48, fontWeight: 600, width: 56, textAlign: "center", flex: "0 0 56px" }}>{operator}</div>
      <Plate label={payload.right || ""} locale={locale} palette={palette} motion={right} compact={compact} />
    </div>
  );
}

function Plate({
  label,
  locale,
  palette,
  motion,
  compact,
}: {
  label: string;
  locale: SupportedLocale;
  palette: ReturnType<typeof inkFor>;
  motion: { opacity: number; y: number };
  compact: boolean;
}) {
  return (
    <div
      style={{
        flex: compact ? "0 0 auto" : "1 1 0",
        minWidth: 0,
        width: compact ? "100%" : undefined,
        maxWidth: compact ? 420 : "46%",
        minHeight: 120,
        overflow: "hidden",
        opacity: motion.opacity,
        transform: `translateY(${motion.y}px)`,
        borderRadius: theme.radius.lg,
        background: palette.plate,
        border: `1px solid ${palette.stroke}`,
        display: "flex",
        alignItems: "flex-end",
        padding: "28px 22px",
      }}
    >
      <Label text={label} width={220} height={72} locale={locale} color={palette.text} role="support" />
    </div>
  );
}

function formatValue(row: SplitValue) {
  const n = Number(row.value);
  const num = Number.isInteger(n) ? String(n) : String(n);
  const unit = row.unit || "%";
  if (row.qualifier === "at_most") return `≤${num}${unit}`;
  if (row.qualifier === "at_least") return `≥${num}${unit}`;
  return `${num}${unit}`;
}

function OwnershipSplit({
  payload,
  palette,
  locale,
}: {
  payload: SemanticMotionPayload;
  palette: ReturnType<typeof inkFor>;
  locale: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  const values = (payload.values || []).filter((v) => Number.isFinite(v.value) && v.value > 0 && v.value <= 100);
  if (!values.length) return null;
  const sum = values.reduce((s, v) => s + v.value, 0);
  const shownSum = Math.min(100, sum);
  const p = interpolate(frame, [6, 28], [0, 1], { ...clamp, easing: ease });
  const r = 78;
  const c = 2 * Math.PI * r;
  let angle = -Math.PI / 2;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 18 }}>
      <svg width="240" height="240" viewBox="0 0 240 240">
        <circle cx="120" cy="120" r={r} fill="none" stroke={palette.muted} strokeWidth="10" opacity={0.35} />
        {values.map((row, i) => {
          const frac = (row.value / 100) * p;
          const len = c * frac;
          const rot = (angle * 180) / Math.PI;
          angle += (row.value / 100) * Math.PI * 2 * p;
          return (
            <circle
              key={`${row.label}-${i}`}
              cx="120"
              cy="120"
              r={r}
              fill="none"
              stroke={i === 0 ? palette.stroke : palette.text}
              strokeWidth="10"
              strokeDasharray={`${len} ${c}`}
              strokeLinecap="butt"
              transform={`rotate(${rot} 120 120)`}
            />
          );
        })}
      </svg>
      <div style={{ display: "flex", gap: 28, justifyContent: "center", flexWrap: "wrap" }}>
        {values.map((row) => (
          <div key={row.label + row.value} style={{ textAlign: "center" }}>
            <div style={{ color: palette.text, fontSize: 40, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{formatValue(row)}</div>
            <Label text={row.label} width={180} height={36} locale={locale} color={palette.muted} />
          </div>
        ))}
      </div>
      {shownSum < 99.5 ? <Label text={payload.labels?.remainder || ""} width={280} height={28} locale={locale} color={palette.muted} /> : null}
    </div>
  );
}

function ProcessTimeline({
  payload,
  palette,
  locale,
}: {
  payload: SemanticMotionPayload;
  palette: ReturnType<typeof inkFor>;
  locale: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  const steps = (payload.steps || [])
    .map((step) => (typeof step === "string" ? step : step.label))
    .filter(Boolean)
    .slice(0, 5);
  if (steps.length < 2) return null;
  const active = Math.min(steps.length - 1, Math.floor(interpolate(frame, [8, Math.max(24, framesSafe(steps))], [0, steps.length], clamp)));
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 6, position: "relative" }}>
      {steps.map((label, i) => {
        const shown = rise(frame, 4 + i * motionDuration.stagger);
        const on = i <= active;
        return (
          <div key={`${label}-${i}`} style={{ display: "flex", gap: 16, alignItems: "center", opacity: shown.opacity, transform: `translateY(${shown.y}px)` }}>
            <svg width="28" height="72" viewBox="0 0 28 72">
              <circle cx="14" cy="20" r="7" fill={on ? palette.stroke : "none"} stroke={palette.stroke} strokeWidth="1.6" />
              {i < steps.length - 1 ? (
                <ConnectorLine
                  x1={14}
                  y1={30}
                  x2={14}
                  y2={30 + shown.opacity * 36}
                  strokeWidth={1.5}
                  preferredColor={theme.color.accent}
                  background={palette.background}
                  sceneTheme={palette.sceneTheme}
                />
              ) : null}
            </svg>
            <Label text={label} width={420} height={44} locale={locale} color={on ? palette.text : palette.muted} role="support" />
          </div>
        );
      })}
    </div>
  );
}

function framesSafe(steps: string[]) {
  return 12 + steps.length * motionDuration.stagger;
}

function Body({
  payload,
  palette,
  locale,
  compact,
}: {
  payload: SemanticMotionPayload;
  palette: ReturnType<typeof inkFor>;
  locale: SupportedLocale;
  compact: boolean;
}) {
  switch (payload.visualIntent) {
    case "capital_flow":
      return <CapitalFlow payload={payload} palette={palette} locale={locale} />;
    case "shareholder_network":
      return <ShareholderNetwork payload={payload} palette={palette} locale={locale} />;
    case "business_comparison":
      return <BusinessComparison payload={payload} palette={palette} locale={locale} compact={compact} />;
    case "ownership_split":
      return <OwnershipSplit payload={payload} palette={palette} locale={locale} />;
    case "process_timeline":
      return <ProcessTimeline payload={payload} palette={palette} locale={locale} />;
    default:
      return <V15Body payload={payload} palette={palette} locale={locale} compact={compact} />;
  }
}

export function SemanticMotion({
  payload,
  frames,
}: {
  payload: SemanticMotionPayload | null | undefined;
  frames: number;
}) {
  const fallback = useLocale();
  if (!payload?.componentId || !payload.visualIntent) return null;
  const locale = localeOf(payload, fallback);
  const mediaSide: MediaSide = payload.mediaSide === "right" ? "right" : "left";
  const requested = (payload.layout || "overlay") as LayoutVariant;
  const resolved = resolveLayout(requested, mediaSide);
  const composed = payload.motionRect && compositionClears(payload.motionRect, payload.faceRect, payload.captionRect)
    ? payload.motionRect
    : null;
  const rect = composed || resolved.rect;
  const scrim = Boolean(payload.columnScrim) || (!composed && resolved.layout === "overlay");
  const paint = scrim
    ? { ...payload, sceneTheme: "ink" as const, connectorBackground: "#12110F" }
    : payload;
  const palette = inkFor(paint);
  const frame = useCurrentFrame();
  const exit = interpolate(frame, [Math.max(16, frames - motionDuration.exit), frames - 1], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: rect.left,
          top: rect.top,
          width: rect.width,
          height: rect.height,
          opacity: exit,
          background: scrim ? "rgba(12,11,10,0.62)" : "transparent",
          borderRadius: scrim ? 28 : 0,
          padding: scrim ? 18 : 0,
          boxSizing: "border-box",
        }}
      >
        <Sequence from={Math.max(0, payload.enterFrame || 0)} durationInFrames={Math.max(1, frames - Math.max(0, payload.enterFrame || 0))}>
          <Body payload={paint} palette={palette} locale={locale} compact={rect.width < 780} />
        </Sequence>
      </div>
    </AbsoluteFill>
  );
}

