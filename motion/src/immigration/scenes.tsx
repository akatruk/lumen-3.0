import type { ReactNode } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { t } from "../localization";
import type { SupportedLocale } from "../localization/language-config";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";

const gold = theme.color.accent;
const blue = "#7EB6C9";
const ink = theme.color.ink;
const muted = theme.color.muted;
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

function reveal(frame: number, index: number, step = 12) {
  const start = 8 + index * step;
  return interpolate(frame, [start, start + 12], [0, 1], clamp);
}

function Stage({ children }: { children: ReactNode }) {
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", justifyContent: "center", paddingLeft: 88, paddingRight: 88, paddingTop: 180, paddingBottom: 320 }}>
      {children}
    </AbsoluteFill>
  );
}

function Lines({ labels, locale }: { labels: string[]; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
      {labels.map((label, index) => (
        <div key={`${label}-${index}`} style={{ opacity: reveal(frame, index), display: "flex", alignItems: "center", gap: 18 }}>
          <svg width="28" height="28" viewBox="0 0 28 28">
            <circle cx="14" cy="14" r="5" fill="none" stroke={gold} strokeWidth="2" />
          </svg>
          <AutoFitText text={label} locale={locale} maxWidth={760} maxHeight={64} role={theme.type.step} color={ink} />
        </div>
      ))}
    </div>
  );
}

function RouteSvg({ progress }: { progress: number }) {
  const dash = 220 * (1 - progress);
  return (
    <svg width="640" height="360" viewBox="0 0 200 110">
      <g fill="none" stroke={blue} strokeWidth="1.4">
        <circle cx="100" cy="58" r="42" />
        <ellipse cx="100" cy="58" rx="18" ry="42" />
      </g>
      <path d="M36 78 C 70 30, 130 28, 168 64" fill="none" stroke={gold} strokeWidth="2.4" strokeLinecap="round" strokeDasharray="220" strokeDashoffset={dash} />
      <circle cx="36" cy="78" r="4" fill={gold} />
      <circle cx="168" cy="64" r="4" fill={gold} opacity={progress > 0.85 ? 1 : 0.25} />
    </svg>
  );
}

function Booklet({ shift = 0 }: { shift?: number }) {
  return (
    <svg width="180" height="240" viewBox="0 0 60 80" style={{ transform: `translateX(${shift}px)` }}>
      <rect x="8" y="6" width="40" height="64" rx="4" fill="none" stroke={gold} strokeWidth="2" />
      <circle cx="28" cy="36" r="8" fill="none" stroke={gold} strokeWidth="2" />
    </svg>
  );
}

export function GlobalRoute({ origin = "", destination = "", locale = "en-US" }: { origin?: string; destination?: string; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [8, 70], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
  return (
    <Stage>
      <RouteSvg progress={progress} />
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 28 }}>
        <AutoFitText text={origin} locale={locale} maxWidth={360} maxHeight={80} role={theme.type.title} color={ink} />
        <AutoFitText text={destination} locale={locale} maxWidth={360} maxHeight={80} role={theme.type.title} color={gold} align="right" />
      </div>
    </Stage>
  );
}

export function CountryOptions({ places = [], locale = "en-US" }: { places?: string[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  return (
    <Stage>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 28 }}>
        {places.map((place, index) => (
          <div key={`${place}-${index}`} style={{ opacity: reveal(frame, index, 10), width: 360 }}>
            <svg width="36" height="36" viewBox="0 0 24 24">
              <path d="M12 20s5-4.4 5-8.4a5 5 0 1 0-10 0C7 15.6 12 20 12 20z" fill="none" stroke={gold} strokeWidth="1.6" />
            </svg>
            <AutoFitText text={place} locale={locale} maxWidth={340} maxHeight={72} role={theme.type.title} color={ink} />
          </div>
        ))}
      </div>
    </Stage>
  );
}

export function CountryComparison({
  countries = [],
  rows = [],
  locale = "en-US",
}: {
  countries?: string[];
  rows?: { field: string; values: string[] }[];
  locale?: SupportedLocale;
}) {
  const frame = useCurrentFrame();
  return (
    <Stage>
      <div style={{ display: "flex", gap: 24, marginBottom: 28 }}>
        {countries.slice(0, 4).map((country, index) => (
          <div key={`${country}-${index}`} style={{ flex: 1, opacity: reveal(frame, index, 8) }}>
            <AutoFitText text={country} locale={locale} maxWidth={220} maxHeight={72} role={theme.type.title} color={gold} />
          </div>
        ))}
      </div>
      {rows.map((row, index) => (
        <div key={`${row.field}-${index}`} style={{ opacity: reveal(frame, index + 1), display: "flex", gap: 24, marginBottom: 16 }}>
          <div style={{ width: 220 }}>
            <AutoFitText text={row.field} locale={locale} maxWidth={210} maxHeight={48} role={theme.type.label} color={muted} />
          </div>
          {row.values.slice(0, 4).map((value, valueIndex) => (
            <div key={`${value}-${valueIndex}`} style={{ flex: 1 }}>
              <AutoFitText text={value} locale={locale} maxWidth={180} maxHeight={48} role={theme.type.support} color={ink} />
            </div>
          ))}
        </div>
      ))}
    </Stage>
  );
}

export function PassportReveal({ caption = "", locale = "en-US" }: { caption?: string; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const rise = interpolate(frame, [0, 24], [40, 0], clamp);
  const opacity = interpolate(frame, [0, 18], [0, 1], clamp);
  return (
    <Stage>
      <div style={{ opacity, transform: `translateY(${rise}px)`, alignSelf: "center" }}>
        <Booklet />
      </div>
      <div style={{ marginTop: 36 }}>
        <AutoFitText text={caption} locale={locale} maxWidth={860} maxHeight={100} role={theme.type.title} color={ink} align="center" />
      </div>
    </Stage>
  );
}

export function SecondPassport({ first = "", second = "", locale = "en-US" }: { first?: string; second?: string; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const secondOpacity = interpolate(frame, [28, 48], [0, 1], clamp);
  return (
    <Stage>
      <div style={{ display: "flex", gap: 48, alignItems: "center" }}>
        <div>
          <Booklet />
          <AutoFitText text={first} locale={locale} maxWidth={280} maxHeight={64} role={theme.type.support} color={muted} />
        </div>
        <svg width="80" height="24" viewBox="0 0 80 24" style={{ opacity: secondOpacity }}>
          <path d="M4 12h60M52 6l12 6-12 6" fill="none" stroke={gold} strokeWidth="2" />
        </svg>
        <div style={{ opacity: secondOpacity }}>
          <Booklet />
          <AutoFitText text={second} locale={locale} maxWidth={280} maxHeight={64} role={theme.type.support} color={gold} />
        </div>
      </div>
    </Stage>
  );
}

export function GlobalAccess({ center = "", places = [], locale = "en-US" }: { center?: string; places?: string[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  return (
    <Stage>
      <div style={{ alignSelf: "center", marginBottom: 36 }}>
        <Booklet />
        <AutoFitText text={center} locale={locale} maxWidth={420} maxHeight={64} role={theme.type.support} color={ink} align="center" />
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 20, justifyContent: "center" }}>
        {places.map((place, index) => (
          <div key={`${place}-${index}`} style={{ opacity: reveal(frame, index, 8) }}>
            <AutoFitText text={place} locale={locale} maxWidth={240} maxHeight={56} role={theme.type.step} color={gold} align="center" />
          </div>
        ))}
      </div>
    </Stage>
  );
}

export function ApplicationProcess({ stages = [], locale = "en-US" }: { stages?: string[]; locale?: SupportedLocale }) {
  return (
    <Stage>
      <Lines labels={stages} locale={locale} />
    </Stage>
  );
}

export function DocumentCheck({ items = [], locale = "en-US" }: { items?: string[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  return (
    <Stage>
      {items.map((item, index) => {
        const on = reveal(frame, index);
        return (
          <div key={`${item}-${index}`} style={{ opacity: on, display: "flex", gap: 16, marginBottom: 18, alignItems: "center" }}>
            <svg width="32" height="32" viewBox="0 0 32 32">
              <rect x="6" y="4" width="16" height="22" rx="2" fill="none" stroke={gold} strokeWidth="1.6" />
              <path d="M11 16l3 3 6-7" fill="none" stroke={gold} strokeWidth="1.8" opacity={on} />
            </svg>
            <AutoFitText text={item} locale={locale} maxWidth={760} maxHeight={56} role={theme.type.step} color={ink} />
          </div>
        );
      })}
    </Stage>
  );
}

export function Approval({ label = "", locale = "en-US" }: { label?: string; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [10, 28], [0.6, 1], clamp);
  return (
    <Stage>
      <svg width="160" height="160" viewBox="0 0 80 80" style={{ transform: `scale(${scale})` }}>
        <circle cx="40" cy="40" r="26" fill="none" stroke={gold} strokeWidth="2" />
        <path d="M28 41l8 8 16-18" fill="none" stroke={gold} strokeWidth="3" />
      </svg>
      <div style={{ marginTop: 28 }}>
        <AutoFitText text={label} locale={locale} maxWidth={860} maxHeight={120} role={theme.type.title} color={ink} align="center" />
      </div>
    </Stage>
  );
}

export function RelocationTimeline({ stages = [], locale = "en-US" }: { stages?: string[]; locale?: SupportedLocale }) {
  return (
    <Stage>
      <Lines labels={stages} locale={locale} />
    </Stage>
  );
}

export function MovingJourney({ from = "", to = "", locale = "en-US" }: { from?: string; to?: string; locale?: SupportedLocale }) {
  return <GlobalRoute origin={from} destination={to} locale={locale} />;
}

export function FamilyRelocation({ from = "", to = "", locale = "en-US" }: { from?: string; to?: string; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [8, 70], [0, 1], clamp);
  return (
    <Stage>
      <svg width="120" height="48" viewBox="0 0 80 32">
        <circle cx="16" cy="10" r="4" fill="none" stroke={gold} strokeWidth="1.6" />
        <circle cx="32" cy="10" r="4" fill="none" stroke={gold} strokeWidth="1.6" />
        <circle cx="24" cy="20" r="3" fill="none" stroke={gold} strokeWidth="1.6" />
      </svg>
      <RouteSvg progress={progress} />
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <AutoFitText text={from} locale={locale} maxWidth={360} maxHeight={80} role={theme.type.title} color={ink} />
        <AutoFitText text={to} locale={locale} maxWidth={360} maxHeight={80} role={theme.type.title} color={gold} align="right" />
      </div>
    </Stage>
  );
}

export function BusinessRelocation({ from = "", market = "", locale = "en-US" }: { from?: string; market?: string; locale?: SupportedLocale }) {
  return <GlobalRoute origin={from} destination={market} locale={locale} />;
}

export function CostBreakdown({ rows = [], locale = "en-US" }: { rows?: { label: string; value?: string }[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  return (
    <Stage>
      {rows.map((row, index) => (
        <div key={`${row.label}-${index}`} style={{ opacity: reveal(frame, index), display: "flex", justifyContent: "space-between", marginBottom: 20, gap: 24 }}>
          <AutoFitText text={row.label} locale={locale} maxWidth={520} maxHeight={56} role={theme.type.step} color={ink} />
          <AutoFitText text={row.value ?? ""} locale={locale} maxWidth={280} maxHeight={56} role={theme.type.support} color={gold} align="right" />
        </div>
      ))}
    </Stage>
  );
}

export function Eligibility({ criteria = [], locale = "en-US" }: { criteria?: string[]; locale?: SupportedLocale }) {
  return (
    <Stage>
      <Lines labels={criteria} locale={locale} />
    </Stage>
  );
}

/** Stages come from the Director. Do not treat any default order as a legal path. */
export function ResidencyProgress({ stages = [], locale = "en-US" }: { stages?: string[]; locale?: SupportedLocale }) {
  return (
    <Stage>
      <Lines labels={stages} locale={locale} />
    </Stage>
  );
}

export function DecisionPath({ left = "", right = "", locale = "en-US" }: { left?: string; right?: string; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [12, 28], [0, 1], clamp);
  return (
    <Stage>
      <div style={{ display: "flex", gap: 32, opacity: show, alignItems: "center" }}>
        <div style={{ flex: 1 }}>
          <AutoFitText text={left} locale={locale} maxWidth={380} maxHeight={160} role={theme.type.title} color={ink} />
        </div>
        <AutoFitText text={t(locale, "comparison.versus")} locale={locale} maxWidth={120} maxHeight={60} role={theme.type.label} color={gold} align="center" />
        <div style={{ flex: 1 }}>
          <AutoFitText text={right} locale={locale} maxWidth={380} maxHeight={160} role={theme.type.title} color={ink} />
        </div>
      </div>
    </Stage>
  );
}

export function QualityOfLife({ categories = [], locale = "en-US" }: { categories?: { label: string; note?: string }[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  return (
    <Stage>
      {categories.map((category, index) => (
        <div key={`${category.label}-${index}`} style={{ opacity: reveal(frame, index), marginBottom: 18 }}>
          <AutoFitText text={category.label} locale={locale} maxWidth={820} maxHeight={52} role={theme.type.step} color={ink} />
          <AutoFitText text={category.note ?? ""} locale={locale} maxWidth={820} maxHeight={40} role={theme.type.label} color={muted} />
        </div>
      ))}
    </Stage>
  );
}

export function RelocationChecklist({ items = [], locale = "en-US" }: { items?: string[]; locale?: SupportedLocale }) {
  return <DocumentCheck items={items} locale={locale} />;
}

export function NewLife({ places = [], locale = "en-US" }: { places?: string[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [0, 40], [0, 1], clamp);
  return (
    <Stage>
      <RouteSvg progress={progress} />
      <div style={{ display: "flex", gap: 20, marginTop: 24, flexWrap: "wrap" }}>
        {places.map((place, index) => (
          <div key={`${place}-${index}`} style={{ opacity: reveal(frame, index, 14) }}>
            <AutoFitText text={place} locale={locale} maxWidth={240} maxHeight={64} role={theme.type.step} color={gold} />
          </div>
        ))}
      </div>
    </Stage>
  );
}

export function PassportProperty({ caption = "", locale = "en-US" }: { caption?: string; locale?: SupportedLocale }) {
  return (
    <Stage>
      <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
        <Booklet />
        <svg width="160" height="140" viewBox="0 0 80 70">
          <path d="M8 36 L40 12 L72 36" fill="none" stroke={gold} strokeWidth="2" />
          <path d="M18 36 V62 H62 V36" fill="none" stroke={gold} strokeWidth="2" />
        </svg>
      </div>
      <div style={{ marginTop: 28 }}>
        <AutoFitText text={caption} locale={locale} maxWidth={860} maxHeight={100} role={theme.type.title} color={ink} />
      </div>
    </Stage>
  );
}

export function PassportBusiness({ caption = "", locale = "en-US" }: { caption?: string; locale?: SupportedLocale }) {
  return (
    <Stage>
      <div style={{ display: "flex", gap: 40, alignItems: "center" }}>
        <Booklet />
        <svg width="160" height="120" viewBox="0 0 80 60">
          <rect x="10" y="16" width="60" height="36" rx="4" fill="none" stroke={gold} strokeWidth="2" />
          <path d="M30 16 V10 H50 V16" fill="none" stroke={gold} strokeWidth="2" />
        </svg>
      </div>
      <div style={{ marginTop: 28 }}>
        <AutoFitText text={caption} locale={locale} maxWidth={860} maxHeight={100} role={theme.type.title} color={ink} />
      </div>
    </Stage>
  );
}

export function TimeToMove({ marks = [], locale = "en-US" }: { marks?: string[]; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const width = interpolate(frame, [8, 70], [0, 1], clamp);
  return (
    <Stage>
      <div style={{ height: 4, width: 860 * width, background: gold, borderRadius: 4, marginBottom: 36 }} />
      <Lines labels={marks} locale={locale} />
    </Stage>
  );
}

export function BeforeAfterRelocation({ before = "", after = "", locale = "en-US" }: { before?: string; after?: string; locale?: SupportedLocale }) {
  return <DecisionPath left={before} right={after} locale={locale} />;
}

export function GlobalMobility({ center = "", nodes = [], locale = "en-US" }: { center?: string; nodes?: string[]; locale?: SupportedLocale }) {
  return <GlobalAccess center={center} places={nodes} locale={locale} />;
}

export const IMMIGRATION_PRESETS = [
  "GlobalRoute",
  "CountryOptions",
  "CountryComparison",
  "PassportReveal",
  "SecondPassport",
  "GlobalAccess",
  "ApplicationProcess",
  "DocumentCheck",
  "Approval",
  "RelocationTimeline",
  "MovingJourney",
  "FamilyRelocation",
  "BusinessRelocation",
  "CostBreakdown",
  "Eligibility",
  "ResidencyProgress",
  "DecisionPath",
  "QualityOfLife",
  "RelocationChecklist",
  "NewLife",
  "PassportProperty",
  "PassportBusiness",
  "TimeToMove",
  "BeforeAfterRelocation",
  "GlobalMobility",
] as const;

export function ImmigrationMotion({ preset = "GlobalRoute" }: { preset?: (typeof IMMIGRATION_PRESETS)[number] }) {
  if (preset === "CountryOptions") return <CountryOptions places={["", "", ""]} />;
  if (preset === "CountryComparison") {
    return <CountryComparison countries={["", ""]} rows={[{ field: "", values: ["", ""] }]} />;
  }
  if (preset === "PassportReveal") return <PassportReveal />;
  if (preset === "SecondPassport") return <SecondPassport />;
  if (preset === "GlobalAccess") return <GlobalAccess places={["", "", ""]} />;
  if (preset === "ApplicationProcess") return <ApplicationProcess stages={["", "", "", ""]} />;
  if (preset === "DocumentCheck") return <DocumentCheck items={["", "", ""]} />;
  if (preset === "Approval") return <Approval />;
  if (preset === "RelocationTimeline") return <RelocationTimeline stages={["", "", "", ""]} />;
  if (preset === "MovingJourney") return <MovingJourney />;
  if (preset === "FamilyRelocation") return <FamilyRelocation />;
  if (preset === "BusinessRelocation") return <BusinessRelocation />;
  if (preset === "CostBreakdown") return <CostBreakdown rows={[{ label: "" }, { label: "" }, { label: "" }]} />;
  if (preset === "Eligibility") return <Eligibility criteria={["", "", ""]} />;
  if (preset === "ResidencyProgress") return <ResidencyProgress stages={[]} />;
  if (preset === "DecisionPath") return <DecisionPath />;
  if (preset === "QualityOfLife") return <QualityOfLife categories={[{ label: "" }, { label: "" }]} />;
  if (preset === "RelocationChecklist") return <RelocationChecklist items={["", "", ""]} />;
  if (preset === "NewLife") return <NewLife places={["", ""]} />;
  if (preset === "PassportProperty") return <PassportProperty />;
  if (preset === "PassportBusiness") return <PassportBusiness />;
  if (preset === "TimeToMove") return <TimeToMove marks={["", ""]} />;
  if (preset === "BeforeAfterRelocation") return <BeforeAfterRelocation />;
  if (preset === "GlobalMobility") return <GlobalMobility nodes={["", "", ""]} />;
  return <GlobalRoute />;
}
