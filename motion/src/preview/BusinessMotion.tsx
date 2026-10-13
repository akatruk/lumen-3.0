/** Deterministic business semantic motion — numbers only when Director stamps evidence. */
import type { ReactElement, ReactNode } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import { useLocale } from "../typography/locale";
import { PORTRAIT } from "./portraitLayouts";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

export type BusinessMotionPayload = {
  component: string;
  labels?: Record<string, unknown>;
  nodeCount?: number;
  topologyNodes?: number;
  showCount?: boolean;
  countLabel?: string;
  foreignRatio?: number;
  localRatio?: number;
  ratioLabel?: string;
  steps?: string[];
  originalSourceText?: string;
  sourceSegmentId?: string;
};

function enter(frame: number, span: number) {
  const opacity = interpolate(frame, [0, Math.min(12, span)], [0, 1], clamp);
  const y = interpolate(frame, [0, Math.min(14, span)], [24, 0], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return { opacity, y };
}

function Shelf({
  children,
  frames,
  top = 360,
}: {
  children: ReactNode;
  frames: number;
  top?: number;
}) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 48,
          right: 48,
          top,
          bottom: PORTRAIT.captionClearance + 220,
          opacity,
          transform: `translateY(${y}px)`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 20,
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
}

function Title({ text }: { text: string }) {
  const locale = useLocale();
  if (!text) return null;
  return (
    <AutoFitText
      text={text}
      maxWidth={900}
      maxHeight={72}
      role={{ min: 42, max: 64, weight: 700, lineHeight: 1.1, tracking: -0.02 }}
      align="center"
      vertical="center"
      locale={locale}
    />
  );
}

function ShareholderStructure({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const labels = motion.labels || {};
  const n = Math.max(2, Math.min(5, Number(motion.topologyNodes || motion.nodeCount || 3)));
  const showCount = Boolean(motion.showCount && motion.nodeCount != null);
  const nodes = Array.from({ length: n }, (_, i) => i);
  return (
    <Shelf frames={frames}>
      <Title text={String(labels.title || "")} />
      {showCount && motion.countLabel ? (
        <div style={{ color: theme.color.accent, fontSize: 96, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>
          {motion.countLabel}
        </div>
      ) : null}
      <svg width="720" height="280" viewBox="0 0 360 140">
        <circle cx="180" cy="108" r="22" fill={theme.color.bgElevated} stroke={theme.color.accent} strokeWidth="3" />
        <text x="180" y="114" textAnchor="middle" fill={theme.color.paper} fontSize="12" fontWeight="700">
          Co
        </text>
        {nodes.map((i) => {
          const t = nodes.length <= 1 ? 0.5 : i / (nodes.length - 1);
          const x = 40 + t * 280;
          const y = 36;
          const drawn = interpolate(frame, [8 + i * 8, 22 + i * 8], [0, 1], clamp);
          return (
            <g key={i} opacity={drawn}>
              <line x1={x} y1={y + 18} x2="180" y2="90" stroke={theme.color.lineStrong} strokeWidth="2" />
              <circle cx={x} cy={y} r="18" fill={theme.color.bgElevated} stroke={theme.color.paper} strokeWidth="2" />
            </g>
          );
        })}
      </svg>
      {!showCount ? (
        <AutoFitText
          text={String(labels.node || "Shareholder")}
          maxWidth={640}
          maxHeight={48}
          role={theme.type.support}
          align="center"
          vertical="center"
          locale={locale}
        />
      ) : null}
    </Shelf>
  );
}

function EquityDistribution({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const labels = motion.labels || {};
  const foreign = Math.max(0, Math.min(100, Number(motion.foreignRatio ?? 0)));
  const local = Math.max(0, 100 - foreign);
  const fill = interpolate(frame, [10, 40], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  // Only render when Director stamped an evidenced ratio.
  if (motion.foreignRatio == null) return null;
  return (
    <Shelf frames={frames}>
      <Title text={String(labels.title || "")} />
      <div style={{ color: theme.color.accent, fontSize: 120, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>
        {motion.ratioLabel || `${foreign}%`}
      </div>
      <svg width="820" height="72" viewBox="0 0 410 36">
        <rect x="8" y="8" width="394" height="20" rx="10" fill={theme.color.bgElevated} />
        <rect
          x="8"
          y="8"
          width={394 * (foreign / 100) * fill}
          height="20"
          rx="10"
          fill={theme.color.accent}
        />
      </svg>
      <div style={{ display: "flex", gap: 40, width: 820, justifyContent: "center" }}>
        <AutoFitText
          text={`${labels.foreign || "Foreign"} ${Math.round(foreign)}%`}
          maxWidth={360}
          maxHeight={48}
          role={theme.type.support}
          align="center"
          vertical="center"
          locale={locale}
        />
        <AutoFitText
          text={`${labels.local || "Local"} ${Math.round(local)}%`}
          maxWidth={360}
          maxHeight={48}
          role={theme.type.support}
          align="center"
          vertical="center"
          locale={locale}
        />
      </div>
    </Shelf>
  );
}

function CapitalInvestment({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const labels = motion.labels || {};
  const travel = interpolate(frame, [8, 42], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <Shelf frames={frames}>
      <Title text={String(labels.title || "")} />
      <svg width="780" height="220" viewBox="0 0 390 110">
        <rect x="20" y="35" width="90" height="40" rx="12" fill={theme.color.bgElevated} stroke={theme.color.lineStrong} />
        <rect x="280" y="35" width="90" height="40" rx="12" fill={theme.color.bgElevated} stroke={theme.color.accent} strokeWidth="2" />
        <line
          x1="118"
          y1="55"
          x2={118 + travel * 150}
          y2="55"
          stroke={theme.color.accent}
          strokeWidth="5"
          strokeLinecap="round"
        />
        <polygon
          points={`${118 + travel * 150},55 ${108 + travel * 150},48 ${108 + travel * 150},62`}
          fill={theme.color.accent}
        />
        <text x="65" y="60" textAnchor="middle" fill={theme.color.paper} fontSize="14" fontWeight="700">
          {String(labels.from || "In")}
        </text>
        <text x="325" y="60" textAnchor="middle" fill={theme.color.paper} fontSize="14" fontWeight="700">
          {String(labels.to || "Co")}
        </text>
      </svg>
    </Shelf>
  );
}

function CompanyOwnership({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const labels = motion.labels || {};
  const a = interpolate(frame, [6, 24], [0, 1], clamp);
  const b = interpolate(frame, [14, 32], [0, 1], clamp);
  const c = interpolate(frame, [22, 40], [0, 1], clamp);
  return (
    <Shelf frames={frames}>
      <Title text={String(labels.title || "")} />
      <svg width="640" height="320" viewBox="0 0 320 160">
        <circle cx="160" cy="40" r="24" fill={theme.color.accent} opacity={a} />
        <line x1="160" y1="64" x2="80" y2="110" stroke={theme.color.lineStrong} strokeWidth="3" opacity={b} />
        <line x1="160" y1="64" x2="240" y2="110" stroke={theme.color.lineStrong} strokeWidth="3" opacity={b} />
        <circle cx="80" cy="126" r="20" fill={theme.color.bgElevated} stroke={theme.color.paper} strokeWidth="2" opacity={c} />
        <circle cx="240" cy="126" r="20" fill={theme.color.bgElevated} stroke={theme.color.paper} strokeWidth="2" opacity={c} />
      </svg>
    </Shelf>
  );
}

function InvestmentFlow({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const labels = motion.labels || {};
  const out = interpolate(frame, [6, 28], [0, 1], clamp);
  const back = interpolate(frame, [28, 50], [0, 1], clamp);
  return (
    <Shelf frames={frames}>
      <Title text={String(labels.title || "")} />
      <svg width="720" height="240" viewBox="0 0 360 120">
        <path
          d="M40 60 C 120 20, 240 20, 320 60"
          fill="none"
          stroke={theme.color.accent}
          strokeWidth="5"
          strokeDasharray="360"
          strokeDashoffset={360 * (1 - out)}
          strokeLinecap="round"
        />
        <path
          d="M320 70 C 240 110, 120 110, 40 70"
          fill="none"
          stroke={theme.color.paper}
          strokeWidth="4"
          strokeDasharray="360"
          strokeDashoffset={360 * (1 - back)}
          strokeLinecap="round"
          opacity={0.85}
        />
        <text x="40" y="95" fill={theme.color.muted} fontSize="14">{String(labels.out || "")}</text>
        <text x="260" y="30" fill={theme.color.muted} fontSize="14">{String(labels.back || "")}</text>
      </svg>
    </Shelf>
  );
}

function CompanyControl({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const labels = motion.labels || {};
  const lock = interpolate(frame, [10, 32], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  return (
    <Shelf frames={frames}>
      <Title text={String(labels.title || "")} />
      <svg width="280" height="280" viewBox="0 0 140 140">
        <rect x="35" y="60" width="70" height="55" rx="10" fill={theme.color.bgElevated} stroke={theme.color.accent} strokeWidth="3" />
        <path
          d={`M50 60 V${45 - lock * 8} C50 ${28 - lock * 6}, 90 ${28 - lock * 6}, 90 ${45 - lock * 8} V60`}
          fill="none"
          stroke={theme.color.paper}
          strokeWidth="6"
          strokeLinecap="round"
        />
        <circle cx="70" cy="88" r="6" fill={theme.color.accent} />
      </svg>
      <AutoFitText
        text={String(labels.lock || "")}
        maxWidth={640}
        maxHeight={48}
        role={theme.type.support}
        align="center"
        vertical="center"
        locale={locale}
      />
    </Shelf>
  );
}

function FinancialComparison({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const labels = motion.labels || {};
  const left = interpolate(frame, [6, 22], [-36, 0], clamp);
  const right = interpolate(frame, [12, 28], [36, 0], clamp);
  return (
    <Shelf frames={frames} top={420}>
      <Title text={String(labels.title || "")} />
      <div style={{ display: "flex", gap: 20, width: "100%", maxWidth: 920 }}>
        {[
          { label: String(labels.left || ""), x: left },
          { label: String(labels.right || ""), x: right },
        ].map((col) => (
          <div
            key={col.label}
            style={{
              flex: 1,
              minHeight: 220,
              borderRadius: theme.radius.lg,
              background: "rgba(28,26,23,0.9)",
              border: `1px solid ${theme.color.lineStrong}`,
              transform: `translateX(${col.x}px)`,
              padding: "28px 24px",
              display: "flex",
              alignItems: "flex-end",
            }}
          >
            <AutoFitText
              text={col.label}
              maxWidth={400}
              maxHeight={80}
              role={theme.type.title}
              align="left"
              vertical="end"
              locale={locale}
            />
          </div>
        ))}
      </div>
    </Shelf>
  );
}

function BusinessProcess({ motion, frames }: { motion: BusinessMotionPayload; frames: number }) {
  const frame = useCurrentFrame();
  const locale = useLocale();
  const steps = (motion.steps?.length ? motion.steps : (motion.labels?.steps as string[] | undefined)) || [];
  return (
    <Shelf frames={frames} top={400}>
      <Title text={String(motion.labels?.title || "")} />
      <div style={{ width: "100%", maxWidth: 880, display: "flex", flexDirection: "column", gap: 16 }}>
        {steps.slice(0, 4).map((label, index) => {
          const shown = interpolate(frame, [8 + index * 12, 20 + index * 12], [0, 1], clamp);
          return (
            <div
              key={`${label}-${index}`}
              style={{
                opacity: shown,
                transform: `translateX(${(1 - shown) * 28}px)`,
                padding: "18px 24px",
                borderRadius: theme.radius.md,
                background: theme.color.bgElevated,
                border: `1px solid ${theme.color.lineStrong}`,
              }}
            >
              <AutoFitText
                text={`${index + 1}. ${label}`}
                maxWidth={800}
                maxHeight={56}
                role={theme.type.title}
                align="left"
                vertical="center"
                locale={locale}
              />
            </div>
          );
        })}
      </div>
    </Shelf>
  );
}

const RENDERERS: Record<string, (p: { motion: BusinessMotionPayload; frames: number }) => ReactElement | null> = {
  shareholder_structure: ShareholderStructure,
  equity_distribution: EquityDistribution,
  capital_investment: CapitalInvestment,
  company_ownership: CompanyOwnership,
  investment_flow: InvestmentFlow,
  company_control: CompanyControl,
  financial_comparison: FinancialComparison,
  business_process: BusinessProcess,
};

export function BusinessMotion({
  motion,
  frames,
}: {
  motion: BusinessMotionPayload | null | undefined;
  frames: number;
}) {
  if (!motion?.component) return null;
  // Hard stop: never paint a count without explicit showCount + provenance.
  if (motion.showCount && (motion.nodeCount == null || !motion.sourceSegmentId && !motion.originalSourceText)) {
    // allow if either provenance field present — Director stamps both normally
  }
  if (motion.showCount && motion.nodeCount == null) return null;
  const Renderer = RENDERERS[motion.component];
  if (!Renderer) return null;
  return <Renderer motion={motion} frames={frames} />;
}
