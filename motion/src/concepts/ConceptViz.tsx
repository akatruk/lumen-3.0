import type { ReactElement } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import { CountUp } from "../primitives/marks";
import { presetById } from "./presets";
import type { ConceptPresetId, ConceptTriggerHit } from "./schema";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

function enter(frame: number, span: number) {
  const opacity = interpolate(frame, [0, Math.min(12, span)], [0, 1], clamp);
  const y = interpolate(frame, [0, Math.min(14, span)], [28, 0], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return { opacity, y };
}

function GrowthArrow({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const travel = interpolate(frame, [8, Math.min(frames - 4, 48)], [80, 0], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y}px)`, alignItems: "center", justifyContent: "center" }}>
      <svg width="420" height="520" viewBox="0 0 200 260">
        <line x1="100" y1={200} x2="100" y2={40 + travel} stroke={theme.color.accent} strokeWidth="8" strokeLinecap="round" />
        <polyline
          points={`70,${70 + travel} 100,${36 + travel} 130,${70 + travel}`}
          fill="none"
          stroke={theme.color.accent}
          strokeWidth="8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <rect x="40" y="210" width="120" height="8" rx="4" fill={theme.color.lineStrong} />
      </svg>
    </AbsoluteFill>
  );
}

function RiskArrow({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const travel = interpolate(frame, [8, Math.min(frames - 4, 48)], [0, 80], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y}px)`, alignItems: "center", justifyContent: "center" }}>
      <svg width="420" height="520" viewBox="0 0 200 260">
        <line x1="100" y1={40} x2="100" y2={40 + travel} stroke="#C45B4A" strokeWidth="8" strokeLinecap="round" />
        <polyline
          points={`70,${10 + travel} 100,${44 + travel} 130,${10 + travel}`}
          fill="none"
          stroke="#C45B4A"
          strokeWidth="8"
          strokeLinecap="round"
          strokeLinejoin="round"
          transform={`translate(0 ${travel})`}
        />
        <rect x="40" y="210" width="120" height="8" rx="4" fill={theme.color.lineStrong} />
      </svg>
    </AbsoluteFill>
  );
}

function BigFigure({ frames, value = 2 }: { frames: number; value?: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const scale = interpolate(frame, [0, 16], [0.86, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y}px) scale(${scale})`, alignItems: "center", justifyContent: "center" }}>
      <div style={{ color: theme.color.accent, fontSize: 280, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
        <CountUp value={value} duration={36} />
      </div>
    </AbsoluteFill>
  );
}

function StepsReveal({ frames, labels }: { frames: number; labels?: string[] }) {
  const frame = useCurrentFrame();
  const { opacity } = enter(frame, frames);
  const items = labels?.length ? labels.slice(0, 4) : ["Консультация", "Программа", "Документы"];
  return (
    <AbsoluteFill style={{ opacity, padding: "420px 96px 0", gap: 28 }}>
      {items.map((label, index) => {
        const shown = interpolate(frame, [8 + index * 14, 22 + index * 14], [0, 1], clamp);
        return (
          <div
            key={`${label}-${index}`}
            style={{
              opacity: shown,
              transform: `translateX(${(1 - shown) * 36}px)`,
              marginBottom: 22,
              padding: "20px 28px",
              borderRadius: theme.radius.md,
              background: theme.color.bgElevated,
              border: `1px solid ${theme.color.lineStrong}`,
            }}
          >
            <AutoFitText
              text={label}
              maxWidth={820}
              maxHeight={64}
              role={theme.type.title}
              align="left"
              vertical="center"
              locale="ru-RU"
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
}

function ComparisonColumns({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const left = interpolate(frame, [6, 22], [-40, 0], clamp);
  const right = interpolate(frame, [12, 28], [40, 0], clamp);
  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y}px)`, padding: "480px 72px 0", flexDirection: "row", gap: 28 }}>
      {[
        { label: "Цели", x: left },
        { label: "Срок", x: right },
      ].map((col) => (
        <div
          key={col.label}
          style={{
            flex: 1,
            height: 420,
            borderRadius: theme.radius.lg,
            background: theme.color.bgElevated,
            border: `1px solid ${theme.color.line}`,
            transform: `translateX(${col.x}px)`,
            padding: 32,
            display: "flex",
            alignItems: "flex-end",
          }}
        >
          <AutoFitText text={col.label} maxWidth={360} maxHeight={80} role={theme.type.title} align="left" vertical="end" locale="ru-RU" />
        </div>
      ))}
    </AbsoluteFill>
  );
}

function DeadlineScale({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const mark = interpolate(frame, [10, 40], [0.18, 0.72], clamp);
  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y}px)`, alignItems: "center", justifyContent: "center" }}>
      <svg width="780" height="180" viewBox="0 0 390 90">
        <line x1="20" y1="50" x2="370" y2="50" stroke={theme.color.lineStrong} strokeWidth="6" strokeLinecap="round" />
        <circle cx={20 + mark * 350} cy="50" r="14" fill={theme.color.accent} />
        <rect x={20 + mark * 350 - 2} y="18" width="4" height="24" fill={theme.color.accent} />
      </svg>
    </AbsoluteFill>
  );
}

function RouteLink({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity } = enter(frame, frames);
  const draw = interpolate(frame, [6, 42], [1, 0], clamp);
  return (
    <AbsoluteFill style={{ opacity, alignItems: "center", justifyContent: "center" }}>
      <svg width="720" height="420" viewBox="0 0 360 210">
        <circle cx="50" cy="160" r="22" fill={theme.color.bgElevated} stroke={theme.color.accent} strokeWidth="4" />
        <circle cx="310" cy="50" r="22" fill={theme.color.bgElevated} stroke={theme.color.accent} strokeWidth="4" />
        <path
          d="M70 150 C140 140, 220 90, 290 60"
          fill="none"
          stroke={theme.color.accent}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray="320"
          strokeDashoffset={320 * draw}
        />
      </svg>
    </AbsoluteFill>
  );
}

function DocumentStamp({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity } = enter(frame, frames);
  const stamp = interpolate(frame, [10, 28], [1.25, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const ring = interpolate(frame, [24, 48], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ opacity, alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          width: 280,
          height: 360,
          borderRadius: 24,
          background: theme.color.paper,
          transform: `scale(${stamp})`,
          boxShadow: theme.shadow.paper,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 48,
            top: 120,
            width: 180,
            height: 180,
            borderRadius: "50%",
            border: `6px solid ${theme.color.accent}`,
            opacity: 0.35 + ring * 0.55,
            transform: `rotate(-12deg) scale(${0.85 + ring * 0.15})`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
}

function FamilyCluster({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity } = enter(frame, frames);
  const words = ["Цели", "Семья", "Бюджет"];
  return (
    <AbsoluteFill style={{ opacity, padding: "520px 96px 0" }}>
      {words.map((word, index) => {
        const shown = interpolate(frame, [6 + index * 12, 20 + index * 12], [0, 1], clamp);
        return (
          <div
            key={word}
            style={{
              opacity: shown,
              transform: `translateY(${(1 - shown) * 20}px)`,
              marginBottom: 20,
              padding: "18px 26px",
              borderRadius: theme.radius.md,
              background: theme.color.bgElevated,
              border: `1px solid ${theme.color.line}`,
            }}
          >
            <AutoFitText text={word} maxWidth={800} maxHeight={56} role={theme.type.title} align="left" vertical="center" locale="ru-RU" />
          </div>
        );
      })}
    </AbsoluteFill>
  );
}

function BudgetScale({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const tilt = interpolate(frame, [8, 40], [-8, 4], clamp);
  return (
    <AbsoluteFill style={{ opacity, transform: `translateY(${y}px)`, alignItems: "center", justifyContent: "center" }}>
      <svg width="640" height="360" viewBox="0 0 320 180">
        <line x1="160" y1="30" x2="160" y2="140" stroke={theme.color.lineStrong} strokeWidth="5" />
        <g transform={`rotate(${tilt} 160 60)`}>
          <line x1="40" y1="60" x2="280" y2="60" stroke={theme.color.accent} strokeWidth="6" strokeLinecap="round" />
          <rect x="30" y="70" width="60" height="40" rx="8" fill={theme.color.bgElevated} stroke={theme.color.line} />
          <rect x="230" y="70" width="60" height="40" rx="8" fill={theme.color.bgElevated} stroke={theme.color.line} />
        </g>
      </svg>
    </AbsoluteFill>
  );
}

const RENDERERS: Record<ConceptPresetId, (props: { frames: number; hit: ConceptTriggerHit }) => ReactElement> = {
  growth_arrow: ({ frames }) => <GrowthArrow frames={frames} />,
  risk_arrow: ({ frames }) => <RiskArrow frames={frames} />,
  big_figure: ({ frames, hit }) => <BigFigure frames={frames} value={hit.value ?? 2} />,
  steps_reveal: ({ frames, hit }) => <StepsReveal frames={frames} labels={hit.labels} />,
  comparison_columns: ({ frames }) => <ComparisonColumns frames={frames} />,
  deadline_scale: ({ frames }) => <DeadlineScale frames={frames} />,
  route_link: ({ frames }) => <RouteLink frames={frames} />,
  document_stamp: ({ frames }) => <DocumentStamp frames={frames} />,
  family_cluster: ({ frames }) => <FamilyCluster frames={frames} />,
  budget_scale: ({ frames }) => <BudgetScale frames={frames} />,
};

export function ConceptViz({
  hit,
  frames,
}: {
  hit: ConceptTriggerHit;
  frames: number;
}) {
  const preset = presetById(hit.presetId);
  if (!preset) return null;
  const Renderer = RENDERERS[hit.presetId];
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 50% 42%, rgba(18,17,15,0.15) 0%, rgba(18,17,15,0.55) 70%, rgba(18,17,15,0.78) 100%)",
        }}
      />
      <Renderer frames={frames} hit={hit} />
    </AbsoluteFill>
  );
}
