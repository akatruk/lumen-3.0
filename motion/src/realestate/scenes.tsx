import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { formatCurrency, formatPercent } from "../localization/formatter";
import type { SupportedLocale } from "../localization/language-config";
import { t } from "../localization";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";

const gold = theme.color.accent;
const ink = theme.color.ink;
const muted = theme.color.muted;

export type PriceCounterProps = {
  currency: string;
  value: number;
  locale?: SupportedLocale;
};

export function PriceCounter({ currency, value, locale = "en-US" }: PriceCounterProps) {
  const frame = useCurrentFrame();
  const shown = Math.round(interpolate(frame, [8, 50], [0, value], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }));
  const figure = formatCurrency(shown, currency, locale);
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", justifyContent: "center", paddingLeft: 88, paddingRight: 88 }}>
      <AutoFitText text={t(locale, "realEstate.price")} locale={locale} maxWidth={900} maxHeight={80} role={theme.type.label} color={muted} />
      <div style={{ height: 24 }} />
      <AutoFitText text={figure} locale={locale} maxWidth={900} maxHeight={280} role={theme.type.number} color={gold} />
    </AbsoluteFill>
  );
}

export type PriceChangeProps = {
  currency: string;
  previous: number;
  next: number;
};

export function PriceChange({ currency, previous, next, locale = "en-US" }: PriceChangeProps & { locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const reveal = interpolate(frame, [24, 48], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const up = next >= previous;
  const oldText = formatCurrency(previous, currency, locale);
  const newText = formatCurrency(next, currency, locale);
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", justifyContent: "center", paddingLeft: 88 }}>
      <AutoFitText text={t(locale, "comparison.before")} locale={locale} maxWidth={880} maxHeight={48} role={theme.type.label} color={muted} />
      <AutoFitText text={oldText} locale={locale} maxWidth={880} maxHeight={120} role={theme.type.title} color={muted} />
      <div style={{ height: 28, opacity: reveal }}>
        <svg width="120" height="28" viewBox="0 0 120 28">
          <path d={up ? "M20 22 L60 6 L100 22" : "M20 6 L60 22 L100 6"} fill="none" stroke={up ? "#8FCBB4" : gold} strokeWidth="3" />
        </svg>
      </div>
      <div style={{ opacity: reveal }}>
        <AutoFitText text={t(locale, "comparison.after")} locale={locale} maxWidth={880} maxHeight={48} role={theme.type.label} color={gold} />
        <AutoFitText text={newText} locale={locale} maxWidth={880} maxHeight={200} role={theme.type.number} color={ink} />
      </div>
    </AbsoluteFill>
  );
}

export type RentalYieldProps = {
  currency: string;
  monthlyRent: number;
  yieldPercent: number;
};

export function RentalYield({ currency, monthlyRent, yieldPercent, locale = "en-US" }: RentalYieldProps & { locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const bar = interpolate(frame, [10, 55], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", justifyContent: "center", paddingLeft: 88, paddingRight: 88 }}>
      <AutoFitText text={t(locale, "realEstate.monthlyRent")} locale={locale} maxWidth={900} maxHeight={48} role={theme.type.label} color={muted} />
      <AutoFitText text={formatCurrency(monthlyRent, currency, locale)} locale={locale} maxWidth={900} maxHeight={200} role={theme.type.number} color={ink} />
      <div style={{ height: 18 }} />
      <AutoFitText text={t(locale, "realEstate.rentalYield")} locale={locale} maxWidth={900} maxHeight={48} role={theme.type.label} color={muted} />
      <AutoFitText text={formatPercent(yieldPercent, locale)} locale={locale} maxWidth={900} maxHeight={120} role={theme.type.title} color={gold} />
      <div style={{ marginTop: 28, height: 8, width: 420, background: "rgba(246,241,232,0.15)", borderRadius: 8 }}>
        <div style={{ height: 8, width: 420 * bar * Math.min(yieldPercent, 12) / 12, background: gold, borderRadius: 8 }} />
      </div>
    </AbsoluteFill>
  );
}

export type CompareSide = { name: string; priceLabel: string };

export function PropertyComparison({ left, right, locale = "en-US" }: { left: CompareSide; right: CompareSide; locale?: SupportedLocale }) {
  const frame = useCurrentFrame();
  const show = interpolate(frame, [12, 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", flexDirection: "row", alignItems: "center", paddingLeft: 64, paddingRight: 64, opacity: show }}>
      <div style={{ flex: 1 }}>
        <AutoFitText text={left.name} locale={locale} maxWidth={420} maxHeight={120} role={theme.type.title} color={ink} />
        <AutoFitText text={left.priceLabel} locale={locale} maxWidth={420} maxHeight={80} role={theme.type.support} color={gold} />
      </div>
      <div style={{ width: 160 }}>
        <AutoFitText text={t(locale, "comparison.versus")} locale={locale} maxWidth={160} maxHeight={60} role={theme.type.label} color={muted} align="center" />
      </div>
      <div style={{ flex: 1 }}>
        <AutoFitText text={right.name} locale={locale} maxWidth={420} maxHeight={120} role={theme.type.title} color={ink} />
        <AutoFitText text={right.priceLabel} locale={locale} maxWidth={420} maxHeight={80} role={theme.type.support} color={gold} />
      </div>
    </AbsoluteFill>
  );
}

export function PurchaseProcess({ locale = "en-US", stageKeys = ["process.search", "process.viewing", "process.offer", "process.contract", "process.handover"] }: { locale?: SupportedLocale; stageKeys?: string[] }) {
  const stages = stageKeys.map((key) => t(locale, key));
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: "transparent", justifyContent: "center", paddingLeft: 96, paddingRight: 96, gap: 18 }}>
      {stages.map((stage, index) => {
        const start = 6 + index * 12;
        const opacity = interpolate(frame, [start, start + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={stage} style={{ opacity, display: "flex", alignItems: "center", gap: 18 }}>
            <svg width="28" height="28" viewBox="0 0 28 28">
              <circle cx="14" cy="14" r="6" fill="none" stroke={gold} strokeWidth="2" />
            </svg>
            <AutoFitText text={stage} locale={locale} maxWidth={760} maxHeight={64} role={theme.type.step} color={ink} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
}
