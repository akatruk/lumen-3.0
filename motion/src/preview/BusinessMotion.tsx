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
  /** V11.2 face-safe placement hint from Director. */
  placement?: string;
  /** left | right — opposite the speaker for split / rail layouts. */
  mediaSide?: string;
  shelfTop?: number;
  faceSafe?: boolean;
  containerPolicy?: string;
};

function enter(frame: number, span: number) {
  const opacity = interpolate(frame, [0, Math.min(12, span)], [0, 1], clamp);
  const y = interpolate(frame, [0, Math.min(14, span)], [20, 0], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  // Soft overshoot check: never travel through face band on the way in.
  return { opacity, y };
}

function shelfGeometry(motion: BusinessMotionPayload) {
  const placement = motion.placement || "side_rail";
  const side = (motion.mediaSide || "left").toLowerCase() === "right" ? "right" : "left";
  const faceBottomPx = Math.round(PORTRAIT.height * PORTRAIT.faceBand.bottom);
  const top = motion.shelfTop ?? 180;
  if (placement === "media_column" || placement === "side_rail") {
    // Half-width rail opposite the speaker — validated for entrance→hold→exit.
    const widthPad = Math.round(PORTRAIT.width * 0.48);
    return side === "right"
      ? {
          left: widthPad,
          right: 32,
          top,
          bottom: PORTRAIT.captionClearance + 160,
          alignItems: "center" as const,
        }
      : {
          left: 32,
          right: widthPad,
          top,
          bottom: PORTRAIT.captionClearance + 160,
          alignItems: "center" as const,
        };
  }
  if (placement === "upper_band_cutaway") {
    return {
      left: 64,
      right: 64,
      top: Math.round(PORTRAIT.height * 0.04),
      bottom: PORTRAIT.height - Math.round(PORTRAIT.height * PORTRAIT.faceBand.top) - 8,
      alignItems: "center" as const,
    };
  }
  // below_face_band fallback
  return {
    left: 48,
    right: 48,
    top: Math.max(faceBottomPx + 24, top),
    bottom: PORTRAIT.captionClearance + 140,
    alignItems: "center" as const,
  };
}

function Shelf({
  children,
  frames,
  motion,
}: {
  children: ReactNode;
  frames: number;
  motion: BusinessMotionPayload;
}) {
  const frame = useCurrentFrame();
  const { opacity, y } = enter(frame, frames);
  // Exit without drifting into face: fade only.
  const exit = interpolate(frame, [Math.max(16, frames - 12), frames - 1], [1, 0], clamp);
  const geo = shelfGeometry(motion);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: geo.left,
          right: geo.right,
          top: geo.top,
          bottom: geo.bottom,
          opacity: opacity * exit,
          transform: `translateY(${y}px)`,
          display: "flex",
          flexDirection: "column",
          alignItems: geo.alignItems,
          justifyContent: "flex-start",
          gap: 16,
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
      maxHeight={64}
      role={{ min: 36, max: 56, weight: 700, lineHeight: 1.1, tracking: -0.02 }}
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
  // Never floor at 2 — that implied "2 shareholders" during staggered reveal.
  // Anonymous topology uses 3; evidenced counts use spoken nodeCount only.
  const evidenced = motion.showCount && motion.nodeCount != null ? Number(motion.nodeCount) : null;
  const n = Math.max(1, Math.min(5, evidenced ?? Number(motion.topologyNodes || 3)));
  const showCount = Boolean(motion.showCount && motion.nodeCount != null);
  const nodes = Array.from({ length: n }, (_, i) => i);
  // When a count is claimed, reveal all nodes together so we never flash "two circles".
  const stagger = showCount ? 0 : 8;
  return (
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      {showCount && motion.countLabel ? (
        <div style={{ color: theme.color.accent, fontSize: 84, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>
          {motion.countLabel}
        </div>
      ) : null}
      <svg width="640" height="240" viewBox="0 0 360 140">
        <circle cx="180" cy="108" r="20" fill="rgba(28,26,23,0.35)" stroke={theme.color.accent} strokeWidth="2.5" />
        <text x="180" y="113" textAnchor="middle" fill={theme.color.paper} fontSize="12" fontWeight="700">
          Co
        </text>
        {nodes.map((i) => {
          const t = nodes.length <= 1 ? 0.5 : i / (nodes.length - 1);
          const x = 48 + t * 264;
          const y = 36;
          const drawn = interpolate(frame, [6 + i * stagger, 18 + i * stagger], [0, 1], clamp);
          return (
            <g key={i} opacity={drawn}>
              <line x1={x} y1={y + 16} x2="180" y2="90" stroke={theme.color.lineStrong} strokeWidth="1.5" />
              <circle cx={x} cy={y} r="16" fill="rgba(28,26,23,0.25)" stroke={theme.color.paper} strokeWidth="2" />
            </g>
          );
        })}
      </svg>
      {!showCount ? (
        <AutoFitText
          text={String(labels.node || "Shareholder")}
          maxWidth={560}
          maxHeight={40}
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
  if (motion.foreignRatio == null) return null;
  return (
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      <div style={{ color: theme.color.accent, fontSize: 96, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>
        {motion.ratioLabel || `${foreign}%`}
      </div>
      <svg width="720" height="56" viewBox="0 0 410 36">
        <rect x="8" y="10" width="394" height="16" rx="8" fill="rgba(28,26,23,0.35)" stroke={theme.color.lineStrong} />
        <rect
          x="8"
          y="10"
          width={394 * (foreign / 100) * fill}
          height="16"
          rx="8"
          fill={theme.color.accent}
        />
      </svg>
      <div style={{ display: "flex", gap: 36, width: 720, justifyContent: "center" }}>
        <AutoFitText
          text={`${labels.foreign || "Foreign"} ${Math.round(foreign)}%`}
          maxWidth={320}
          maxHeight={40}
          role={theme.type.support}
          align="center"
          vertical="center"
          locale={locale}
        />
        <AutoFitText
          text={`${labels.local || "Local"} ${Math.round(local)}%`}
          maxWidth={320}
          maxHeight={40}
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
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      <svg width="720" height="180" viewBox="0 0 390 110">
        <rect x="20" y="35" width="90" height="40" rx="12" fill="rgba(28,26,23,0.3)" stroke={theme.color.lineStrong} />
        <rect x="280" y="35" width="90" height="40" rx="12" fill="rgba(28,26,23,0.3)" stroke={theme.color.accent} strokeWidth="2" />
        <line
          x1="118"
          y1="55"
          x2={118 + travel * 150}
          y2="55"
          stroke={theme.color.accent}
          strokeWidth="4"
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
  // Match evidenced / topology node count — default 3, never a binary "2 owners" diagram.
  const n = Math.max(1, Math.min(4, Number(motion.topologyNodes || motion.nodeCount || 3)));
  const a = interpolate(frame, [6, 24], [0, 1], clamp);
  const b = interpolate(frame, [14, 32], [0, 1], clamp);
  const c = interpolate(frame, [22, 40], [0, 1], clamp);
  const children = Array.from({ length: n }, (_, i) => i);
  return (
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      <svg width="640" height="280" viewBox="0 0 320 160">
        <circle cx="160" cy="36" r="22" fill={theme.color.accent} opacity={a} />
        {children.map((i) => {
          const t = children.length <= 1 ? 0.5 : i / (children.length - 1);
          const x = 60 + t * 200;
          return (
            <g key={i} opacity={c}>
              <line x1="160" y1="58" x2={x} y2="110" stroke={theme.color.lineStrong} strokeWidth="2.5" opacity={b} />
              <circle cx={x} cy="126" r="18" fill="rgba(28,26,23,0.3)" stroke={theme.color.paper} strokeWidth="2" />
            </g>
          );
        })}
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
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      <svg width="680" height="200" viewBox="0 0 360 120">
        <path
          d="M40 60 C 120 20, 240 20, 320 60"
          fill="none"
          stroke={theme.color.accent}
          strokeWidth="4"
          strokeDasharray="360"
          strokeDashoffset={360 * (1 - out)}
          strokeLinecap="round"
        />
        <path
          d="M320 70 C 240 110, 120 110, 40 70"
          fill="none"
          stroke={theme.color.paper}
          strokeWidth="3"
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
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      <svg width="220" height="220" viewBox="0 0 140 140">
        <rect x="35" y="60" width="70" height="55" rx="10" fill="rgba(28,26,23,0.35)" stroke={theme.color.accent} strokeWidth="2.5" />
        <path
          d={`M50 60 V${45 - lock * 8} C50 ${28 - lock * 6}, 90 ${28 - lock * 6}, 90 ${45 - lock * 8} V60`}
          fill="none"
          stroke={theme.color.paper}
          strokeWidth="5"
          strokeLinecap="round"
        />
        <circle cx="70" cy="88" r="6" fill={theme.color.accent} />
      </svg>
      <AutoFitText
        text={String(labels.lock || "")}
        maxWidth={560}
        maxHeight={40}
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
  const left = interpolate(frame, [6, 22], [-28, 0], clamp);
  const right = interpolate(frame, [12, 28], [28, 0], clamp);
  return (
    <Shelf frames={frames} motion={motion}>
      <Title text={String(labels.title || "")} />
      <div style={{ display: "flex", gap: 16, width: "100%", maxWidth: 860 }}>
        {[
          { label: String(labels.left || ""), x: left },
          { label: String(labels.right || ""), x: right },
        ].map((col) => (
          <div
            key={col.label}
            style={{
              flex: 1,
              minHeight: 140,
              borderRadius: theme.radius.lg,
              background: "rgba(28,26,23,0.42)",
              border: `1px solid ${theme.color.lineStrong}`,
              transform: `translateX(${col.x}px)`,
              padding: "22px 20px",
              display: "flex",
              alignItems: "flex-end",
            }}
          >
            <AutoFitText
              text={col.label}
              maxWidth={360}
              maxHeight={64}
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
    <Shelf frames={frames} motion={motion}>
      <Title text={String(motion.labels?.title || "")} />
      <div style={{ width: "100%", maxWidth: 820, display: "flex", flexDirection: "column", gap: 12 }}>
        {steps.slice(0, 4).map((label, index) => {
          const shown = interpolate(frame, [8 + index * 12, 20 + index * 12], [0, 1], clamp);
          // Avoid "2. Shareholders" reading — use bullet + label, index as muted meta.
          return (
            <div
              key={`${label}-${index}`}
              style={{
                opacity: shown,
                transform: `translateX(${(1 - shown) * 20}px)`,
                padding: "14px 20px",
                borderRadius: theme.radius.md,
                background: "rgba(28,26,23,0.38)",
                border: `1px solid ${theme.color.lineStrong}`,
                display: "flex",
                alignItems: "center",
                gap: 16,
              }}
            >
              <span style={{ color: theme.color.muted, fontSize: 22, fontWeight: 600, minWidth: 28 }}>{index + 1}</span>
              <AutoFitText
                text={String(label)}
                maxWidth={720}
                maxHeight={48}
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
  if (motion.showCount && motion.nodeCount == null) return null;
  const Renderer = RENDERERS[motion.component];
  if (!Renderer) return null;
  return <Renderer motion={motion} frames={frames} />;
}
