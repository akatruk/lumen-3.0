import type { ReactElement } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { CANVAS, theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import { useLocale } from "../typography/locale";
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

function BigFigure({ frames, value }: { frames: number; value?: number }) {
  const frame = useCurrentFrame();
  // Never invent a figure — Director / spokenNumber must supply evidence.
  if (value == null || !Number.isFinite(value)) return null;
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
  const locale = useLocale();
  const { opacity } = enter(frame, frames);
  const fallback =
    locale.startsWith("zh") ? ["咨询", "方案", "文件"] : locale.startsWith("en") ? ["Consult", "Program", "Documents"] : ["Консультация", "Программа", "Документы"];
  const items = labels?.length ? labels.slice(0, 4) : fallback;
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
              locale={locale}
            />
          </div>
        );
      })}
    </AbsoluteFill>
  );
}

function ComparisonColumns({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const { opacity, y } = enter(frame, frames);
  const left = interpolate(frame, [6, 22], [-40, 0], clamp);
  const right = interpolate(frame, [12, 28], [40, 0], clamp);
  const cols = locale.startsWith("zh")
    ? [
        { label: "目标", detail: "哪套方案合适", x: left },
        { label: "期限", detail: "何时可以启动", x: right },
      ]
    : locale.startsWith("en")
      ? [
          { label: "Goals", detail: "which program fits", x: left },
          { label: "Timing", detail: "when you can start", x: right },
        ]
      : [
          { label: "Цели", detail: "какая программа подходит", x: left },
          { label: "Срок", detail: "когда реально стартовать", x: right },
        ];
  return (
    <AbsoluteFill
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        padding: "520px 56px 0",
        flexDirection: "row",
        gap: 24,
        pointerEvents: "none",
      }}
    >
      {cols.map((col) => (
        <div
          key={col.label}
          style={{
            flex: 1,
            minHeight: 280,
            borderRadius: theme.radius.lg,
            background: "rgba(28,26,23,0.9)",
            border: `1px solid ${theme.color.lineStrong}`,
            transform: `translateX(${col.x}px)`,
            padding: "28px 26px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
          }}
        >
          <AutoFitText text={col.label} maxWidth={400} maxHeight={64} role={theme.type.title} align="left" vertical="end" locale={locale} />
          <div style={{ height: 10 }} />
          <AutoFitText
            text={col.detail}
            maxWidth={400}
            maxHeight={72}
            role={theme.type.support}
            align="left"
            vertical="end"
            wrapMode="auto"
            maxLines={2}
            locale={locale}
          />
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
  const locale = useLocale();
  const { opacity } = enter(frame, frames);
  const draw = interpolate(frame, [6, 42], [1, 0], clamp);
  const rise = interpolate(frame, [4, 20], [36, 0], { ...clamp, easing: Easing.out(Easing.cubic) });
  // Shelf strictly below the shared face band; above caption clear zone.
  const top = Math.round(CANVAS.height * 0.48);
  const routeCards = locale.startsWith("zh")
    ? [
        { title: "现在", detail: "您居住在哪里" },
        { title: "搬迁", detail: "计划去哪里" },
      ]
    : locale.startsWith("en")
      ? [
          { title: "now", detail: "where you live" },
          { title: "move", detail: "where you plan to go" },
        ]
      : [
          { title: "сейчас", detail: "где вы живёте" },
          { title: "переезд", detail: "куда планируете" },
        ];
  return (
    <AbsoluteFill
      style={{
        opacity,
        alignItems: "flex-start",
        justifyContent: "flex-start",
        padding: `${top}px 40px 0`,
        pointerEvents: "none",
      }}
    >
      <div style={{ width: 560, transform: `translateY(${rise}px)` }}>
        <div style={{ display: "flex", gap: 18, marginBottom: 18 }}>
          {routeCards.map((card) => (
            <div
              key={card.title}
              style={{
                flex: 1,
                padding: "22px 20px",
                borderRadius: theme.radius.md,
                background: "rgba(28,26,23,0.92)",
                border: `1px solid ${theme.color.lineStrong}`,
              }}
            >
              <AutoFitText text={card.title} maxWidth={240} maxHeight={52} role={theme.type.title} align="left" vertical="center" locale={locale} />
              <div style={{ height: 8 }} />
              <AutoFitText
                text={card.detail}
                maxWidth={240}
                maxHeight={64}
                role={theme.type.caption}
                align="left"
                vertical="center"
                wrapMode="auto"
                maxLines={2}
                locale={locale}
              />
            </div>
          ))}
        </div>
        <svg width="560" height="90" viewBox="0 0 360 90">
          <path
            d="M40 60 C120 20, 240 20, 320 60"
            fill="none"
            stroke={theme.color.accent}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray="320"
            strokeDashoffset={320 * draw}
          />
          <circle cx="40" cy="60" r="10" fill={theme.color.accent} />
          <circle cx="320" cy="60" r="10" fill={theme.color.accent} />
        </svg>
      </div>
    </AbsoluteFill>
  );
}

function DocumentStamp({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  const stamp = interpolate(frame, [10, 28], [1.25, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const ring = interpolate(frame, [24, 48], [0, 1], clamp);
  // Left mid shelf — never centered over the presenter's face.
  return (
    <AbsoluteFill
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        alignItems: "flex-start",
        justifyContent: "center",
        padding: "0 0 140px 56px",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: 220,
          height: 280,
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
            left: 28,
            top: 36,
            width: 160,
            height: 10,
            borderRadius: 4,
            background: theme.color.lineStrong,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 36,
            top: 88,
            width: 140,
            height: 140,
            borderRadius: "50%",
            border: `6px solid ${theme.color.accent}`,
            opacity: 0.35 + ring * 0.55,
            transform: `rotate(-12deg) scale(${0.85 + ring * 0.15})`,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 28,
            bottom: 36,
            width: 120,
            height: 8,
            borderRadius: 4,
            background: theme.color.line,
          }}
        />
      </div>
    </AbsoluteFill>
  );
}

function FamilyCluster({ frames }: { frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const { opacity } = enter(frame, frames);
  const cards = locale.startsWith("zh")
    ? [
        { title: "目标", explanation: "迁往哪里以及为何出发" },
        { title: "家庭", explanation: "同行家人与时间安排" },
        { title: "预算", explanation: "项目费用是否可承受" },
      ]
    : locale.startsWith("en")
      ? [
          { title: "Goals", explanation: "where you are going and why" },
          { title: "Family", explanation: "who travels with you and when" },
          { title: "Budget", explanation: "what the program can really cost" },
        ]
      : [
          { title: "Цели", explanation: "куда и зачем вы переезжаете" },
          { title: "Семья", explanation: "кто едет с вами и какие сроки" },
          { title: "Бюджет", explanation: "что реально потянуть по программе" },
        ];
  return (
    <AbsoluteFill style={{ opacity, padding: "420px 72px 0 72px", pointerEvents: "none" }}>
      {cards.map((card, index) => {
        const shown = interpolate(frame, [6 + index * 12, 20 + index * 12], [0, 1], clamp);
        return (
          <div
            key={card.title}
            style={{
              opacity: shown,
              transform: `translateY(${(1 - shown) * 20}px)`,
              marginBottom: 16,
              padding: "16px 22px",
              borderRadius: theme.radius.md,
              background: "rgba(28,26,23,0.88)",
              border: `1px solid ${theme.color.line}`,
              maxWidth: 520,
            }}
          >
            <AutoFitText text={card.title} maxWidth={460} maxHeight={40} role={theme.type.title} align="left" vertical="center" locale={locale} />
            <div style={{ height: 4 }} />
            <AutoFitText
              text={card.explanation}
              maxWidth={460}
              maxHeight={44}
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
  big_figure: ({ frames, hit }) => <BigFigure frames={frames} value={hit.value} />,
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
      {/* Soft side veil — keep face band readable; do not black out center. */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(90deg, rgba(18,17,15,0.16) 0%, rgba(18,17,15,0.02) 48%, rgba(18,17,15,0.04) 100%)",
        }}
      />
      <Renderer frames={frames} hit={hit} />
    </AbsoluteFill>
  );
}
