/**
 * Semantic motion V15 — ten more diagrams on the V14 layout and type.
 * Every number, cell, node, and step comes from the payload.
 */
import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import type { SupportedLocale } from "../localization/language-config";
import { ConnectorLine } from "../preview/ConnectorStroke";
import type { SceneTheme } from "../utils/adaptiveLineStyle";
import { motionDuration } from "./design";
import { formatMetric } from "./format";
import type { SemanticMotionPayload } from "./types";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

type Palette = {
  sceneTheme: SceneTheme;
  background: SemanticMotionPayload["connectorBackground"];
  stroke: string;
  outline: string | null;
  text: string;
  muted: string;
  plate: string;
};

function rise(frame: number, start: number) {
  const end = start + motionDuration.fadeIn;
  return {
    opacity: interpolate(frame, [start, end], [0, 1], clamp),
    y: interpolate(frame, [start, end], [14, 0], clamp),
  };
}

function Fit({
  text,
  width,
  height,
  locale,
  color,
}: {
  text: string;
  width: number;
  height: number;
  locale: SupportedLocale;
  color: string;
}) {
  if (!text) return null;
  return (
    <div style={{ width, maxWidth: "100%", color, textAlign: "center" }}>
      <AutoFitText text={text} maxWidth={width} maxHeight={height} role={theme.type.support} locale={locale} color={color} />
    </div>
  );
}

function DocIcon({ stroke }: { stroke: string }) {
  return (
    <svg width="34" height="42" viewBox="0 0 34 42" aria-hidden>
      <path d="M5 3h15l9 9v26H5z" fill="none" stroke={stroke} strokeWidth="1.6" />
      <path d="M20 3v9h9" fill="none" stroke={stroke} strokeWidth="1.6" />
    </svg>
  );
}

function RiskMatrix({ payload, palette, locale }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const cells = (payload.cells || []).filter((cell) => cell.label);
  if (cells.length < 2) return null;
  const rows = Math.min(3, Math.max(...cells.map((cell) => cell.row)) + 1);
  const cols = Math.min(3, Math.max(...cells.map((cell) => cell.col)) + 1);
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
      {payload.axisY ? <Fit text={payload.axisY} width={280} height={32} locale={locale} color={palette.muted} /> : null}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap: 10 }}>
        {Array.from({ length: rows * cols }, (_, index) => {
          const row = Math.floor(index / cols);
          const col = index % cols;
          const cell = cells.find((item) => item.row === row && item.col === col);
          const shown = rise(frame, 6 + index * 4);
          const emphasis = cell?.highlight ? interpolate(frame, [18, 32], [1, 1.04], clamp) : 1;
          return (
            <div
              key={`${row}-${col}`}
              style={{
                minHeight: 72,
                borderRadius: 16,
                border: `1px solid ${palette.stroke}`,
                background: cell ? palette.plate : "transparent",
                opacity: shown.opacity,
                transform: `scale(${emphasis})`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 8,
              }}
            >
              {cell ? <Fit text={cell.label} width={180} height={48} locale={locale} color={palette.text} /> : null}
            </div>
          );
        })}
      </div>
      {payload.axisX ? <Fit text={payload.axisX} width={280} height={32} locale={locale} color={palette.muted} /> : null}
    </div>
  );
}

function CapitalAllocation({ payload, palette, locale, compact }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale; compact: boolean }) {
  const frame = useCurrentFrame();
  const segments = (payload.segments || []).filter((segment) => segment.label && segment.value > 0);
  if (segments.length < 2) return null;
  const total = segments.reduce((sum, segment) => sum + segment.value, 0);
  const grow = interpolate(frame, [8, 28], [0, 1], clamp);
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 16 }}>
      {payload.totalLabel ? <Fit text={payload.totalLabel} width={compact ? 280 : 520} height={40} locale={locale} color={palette.text} /> : null}
      <div style={{ display: "flex", width: "100%", height: 22, borderRadius: 11, overflow: "hidden", background: palette.plate }}>
        {segments.map((segment, index) => (
          <div
            key={segment.label}
            style={{
              width: `${(segment.value / total) * 100 * grow}%`,
              height: "100%",
              background: palette.stroke,
              opacity: 1 - index * 0.18,
            }}
          />
        ))}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {segments.map((segment, index) => {
          const shown = rise(frame, 10 + index * motionDuration.stagger);
          const figure = formatMetric(segment.value, segment.unit === "%" ? "percent" : "number", locale, segment.unit === "%" ? undefined : segment.unit);
          return (
            <div key={segment.label} style={{ opacity: shown.opacity, transform: `translateY(${shown.y}px)` }}>
              <Fit text={`${segment.label}  ${figure}`} width={compact ? 340 : 520} height={52} locale={locale} color={palette.text} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CompanyEcosystem({ payload, palette, locale }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const nodes = (payload.nodes || []).filter((node) => node.label).slice(0, 6);
  const links = payload.connections || [];
  if (nodes.length < 2) return null;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 8 }}>
      {nodes.map((node, index) => {
        const shown = rise(frame, 4 + index * motionDuration.stagger);
        const linked = links.some((link) => link.from === node.id || link.to === node.id);
        return (
          <div key={node.id} style={{ display: "flex", alignItems: "center", gap: 12, opacity: shown.opacity, transform: `translateY(${shown.y}px)` }}>
            <svg width="22" height="36">
              <circle cx="11" cy="12" r="6" fill="none" stroke={palette.stroke} strokeWidth="1.6" />
              {linked && index < nodes.length - 1 ? (
                <ConnectorLine x1={11} y1={20} x2={11} y2={34} strokeWidth={1.4} preferredColor={theme.color.accent} background={palette.background} sceneTheme={palette.sceneTheme} />
              ) : null}
            </svg>
            <Fit text={node.label} width={360} height={36} locale={locale} color={palette.text} />
          </div>
        );
      })}
    </div>
  );
}

function DocumentWorkflow({ payload, palette, locale }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const steps = (payload.steps || []).map((step) => (typeof step === "string" ? step : step.label)).filter(Boolean).slice(0, 5);
  if (steps.length < 2) return null;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 8 }}>
      {steps.map((label, index) => {
        const shown = rise(frame, 4 + index * motionDuration.stagger);
        return (
          <div key={`${label}-${index}`} style={{ display: "flex", alignItems: "center", gap: 14, opacity: shown.opacity, transform: `translateY(${shown.y}px)` }}>
            <DocIcon stroke={palette.stroke} />
            <Fit text={label} width={420} height={42} locale={locale} color={palette.text} />
          </div>
        );
      })}
    </div>
  );
}

function FinancialMetrics({ payload, palette, locale, compact }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale; compact: boolean }) {
  const frame = useCurrentFrame();
  const metrics = (payload.metrics || []).filter((metric) => metric.label && Number.isFinite(metric.value)).slice(0, 4);
  if (!metrics.length) return null;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: compact ? "column" : "row", alignItems: "center", justifyContent: "center", gap: 16 }}>
      {metrics.map((metric, index) => {
        const shown = rise(frame, 6 + index * motionDuration.stagger);
        const current = interpolate(frame, [8, 34], [0, metric.value], clamp);
        const text = formatMetric(current, metric.format || "number", locale, metric.unit);
        return (
          <div key={metric.label} style={{ opacity: shown.opacity, transform: `translateY(${shown.y}px)`, background: palette.plate, borderRadius: 18, padding: "14px 16px", width: compact ? "100%" : 280 }}>
            <Fit text={text} width={compact ? 320 : 248} height={48} locale={locale} color={palette.text} />
            <Fit text={metric.label} width={compact ? 320 : 248} height={36} locale={locale} color={palette.muted} />
          </div>
        );
      })}
    </div>
  );
}

function BusinessDecision({ payload, palette, locale }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const branches = (payload.branches || []).filter(Boolean).slice(0, 4);
  if (branches.length < 2) return null;
  const root = rise(frame, 4);
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
      {payload.root ? (
        <div style={{ opacity: root.opacity }}>
          <Fit text={payload.root} width={420} height={40} locale={locale} color={palette.text} />
        </div>
      ) : null}
      <svg width="100%" height="28" viewBox="0 0 200 28">
        <ConnectorLine x1={100} y1={0} x2={100} y2={14} strokeWidth={1.5} preferredColor={theme.color.accent} background={palette.background} sceneTheme={palette.sceneTheme} />
        <ConnectorLine x1={30} y1={14} x2={170} y2={14} strokeWidth={1.5} preferredColor={theme.color.accent} background={palette.background} sceneTheme={palette.sceneTheme} />
      </svg>
      <div style={{ display: "flex", width: "100%", justifyContent: "space-around", gap: 8 }}>
        {branches.map((label, index) => {
          const shown = rise(frame, 16 + index * motionDuration.stagger);
          return (
            <div key={label} style={{ opacity: shown.opacity, flex: 1 }}>
              <Fit text={label} width={200} height={48} locale={locale} color={palette.text} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GeographicExpansion({ payload, palette, locale, compact }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale; compact: boolean }) {
  const frame = useCurrentFrame();
  const places = (payload.places || []).filter(Boolean).slice(0, 4);
  if (places.length < 2) return null;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: compact ? "column" : "row", alignItems: "center", justifyContent: "center", gap: compact ? 6 : 18 }}>
      {places.map((place, index) => {
        const shown = rise(frame, 6 + index * motionDuration.stagger);
        return (
          <div key={place} style={{ display: "flex", flexDirection: compact ? "column" : "row", alignItems: "center", gap: 8, opacity: shown.opacity }}>
            <svg width="18" height="18" viewBox="0 0 18 18">
              <circle cx="9" cy="9" r="5" fill="none" stroke={palette.stroke} strokeWidth="1.6" />
            </svg>
            <Fit text={place} width={220} height={40} locale={locale} color={palette.text} />
            {payload.directed && index < places.length - 1 ? (
              <Fit text="→" width={36} height={28} locale={locale} color={palette.stroke} />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

function InvestmentMilestones({ payload, palette, locale }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const milestones = (payload.milestones || []).filter(Boolean).slice(0, 5);
  if (milestones.length < 2) return null;
  const active = Math.min(milestones.length - 1, Math.floor(interpolate(frame, [8, 8 + milestones.length * 10], [0, milestones.length], clamp)));
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 10 }}>
      {milestones.map((label, index) => {
        const shown = rise(frame, 4 + index * motionDuration.stagger);
        return (
          <div key={`${label}-${index}`} style={{ display: "flex", gap: 12, alignItems: "center", opacity: shown.opacity }}>
            <svg width="16" height="16">
              <circle cx="8" cy="8" r="5" fill={index <= active ? palette.stroke : "none"} stroke={palette.stroke} strokeWidth="1.5" />
            </svg>
            <Fit text={label} width={420} height={40} locale={locale} color={index <= active ? palette.text : palette.muted} />
          </div>
        );
      })}
    </div>
  );
}

function ContractRelationship({ payload, palette, locale }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const parties = (payload.parties || []).filter((party) => party.label).slice(0, 4);
  if (parties.length < 2) return null;
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 8 }}>
      {parties.map((party, index) => {
        const shown = rise(frame, 4 + index * motionDuration.stagger);
        return (
          <div key={party.id} style={{ display: "flex", alignItems: "center", gap: 12, opacity: shown.opacity, transform: `translateY(${shown.y}px)` }}>
            {party.kind === "document" ? <DocIcon stroke={palette.stroke} /> : (
              <svg width="28" height="28"><circle cx="14" cy="14" r="8" fill="none" stroke={palette.stroke} strokeWidth="1.6" /></svg>
            )}
            <Fit text={party.label} width={380} height={40} locale={locale} color={palette.text} />
          </div>
        );
      })}
    </div>
  );
}

function BeforeAfter({ payload, palette, locale, compact }: { payload: SemanticMotionPayload; palette: Palette; locale: SupportedLocale; compact: boolean }) {
  const frame = useCurrentFrame();
  if (!payload.before || !payload.after) return null;
  const first = rise(frame, 4);
  const second = rise(frame, 18);
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: compact ? "column" : "row", alignItems: "center", justifyContent: "center", gap: 12 }}>
      <div style={{ flex: 1, opacity: first.opacity, background: palette.plate, borderRadius: 18, padding: 12 }}>
        <Fit text={payload.before} width={compact ? 300 : 240} height={72} locale={locale} color={palette.text} />
      </div>
      <Fit text="→" width={40} height={36} locale={locale} color={palette.stroke} />
      <div style={{ flex: 1, opacity: second.opacity, background: palette.plate, borderRadius: 18, padding: 12 }}>
        <Fit text={payload.after} width={compact ? 300 : 240} height={72} locale={locale} color={palette.text} />
      </div>
    </div>
  );
}

export function V15Body({
  payload,
  palette,
  locale,
  compact,
}: {
  payload: SemanticMotionPayload;
  palette: Palette;
  locale: SupportedLocale;
  compact: boolean;
}) {
  switch (payload.visualIntent) {
    case "risk_matrix":
      return <RiskMatrix payload={payload} palette={palette} locale={locale} />;
    case "capital_allocation":
      return <CapitalAllocation payload={payload} palette={palette} locale={locale} compact={compact} />;
    case "company_ecosystem":
      return <CompanyEcosystem payload={payload} palette={palette} locale={locale} />;
    case "document_workflow":
      return <DocumentWorkflow payload={payload} palette={palette} locale={locale} />;
    case "financial_metrics":
      return <FinancialMetrics payload={payload} palette={palette} locale={locale} compact={compact} />;
    case "business_decision":
      return <BusinessDecision payload={payload} palette={palette} locale={locale} />;
    case "geographic_expansion":
      return <GeographicExpansion payload={payload} palette={palette} locale={locale} compact={compact} />;
    case "investment_milestones":
      return <InvestmentMilestones payload={payload} palette={palette} locale={locale} />;
    case "contract_relationship":
      return <ContractRelationship payload={payload} palette={palette} locale={locale} />;
    case "before_after":
      return <BeforeAfter payload={payload} palette={palette} locale={locale} compact={compact} />;
    default:
      return null;
  }
}
