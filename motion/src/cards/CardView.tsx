import type { ReactNode } from "react";
import { AbsoluteFill } from "remotion";
import { formatArea, formatBathrooms, formatBedrooms, formatCompactCurrency, formatCurrency, formatDate, formatNumber, formatPercent } from "../localization/formatter";
import { fontFamilyFor } from "../localization/fonts";
import type { SupportedLocale } from "../localization/language-config";
import { hintFor } from "../localization/presets";
import { segmentTextForMotion } from "../localization/segment";
import { t } from "../localization";
import { theme, type TypeRole } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import type { CardId } from "./registry";

const SAMPLE = {
  currency: "THB",
  price: 8_500_000,
  previous: 9_200_000,
  value: 8_500_000,
  monthlyRent: 42_000,
  annualRent: 504_000,
  investment: 8_500_000,
  returnAmount: 504_000,
  income: 504_000,
  expenses: 86_000,
  fees: 120_000,
  area: 85,
  bedrooms: 2,
  bathrooms: 2,
  floor: 18,
  yieldPercent: 5.9,
  roiPercent: 5.9,
  occupancy: 94,
  distanceKm: 1.2,
  score: 8.6,
};

function scaleRole(role: TypeRole, factor: number): TypeRole {
  return {
    ...role,
    min: Math.max(18, Math.round(role.min * factor)),
    max: Math.max(22, Math.round(role.max * factor)),
  };
}

function Shell({ locale, kicker, children }: { locale: SupportedLocale; kicker?: string; children: ReactNode }) {
  return (
    <AbsoluteFill style={{ background: theme.color.bg, fontFamily: fontFamilyFor(locale) }}>
      <div style={{ position: "absolute", left: 72, right: 120, top: 200, bottom: 280 }}>
        {kicker ? (
          <AutoFitText text={kicker} locale={locale} maxWidth={860} maxHeight={48} role={theme.type.label} color={theme.color.accent} align="left" vertical="start" />
        ) : null}
        <div style={{ width: 72, height: 2, background: theme.color.accent, marginTop: 18, marginBottom: 28 }} />
        {children}
      </div>
    </AbsoluteFill>
  );
}

function Line({ locale, text, role, color = theme.color.ink, height = 88, maxLines }: { locale: SupportedLocale; text: string; role: TypeRole; color?: string; height?: number; maxLines?: number }) {
  return <AutoFitText text={text} locale={locale} maxWidth={860} maxHeight={height} role={role} color={color} align="left" vertical="start" maxLines={maxLines} />;
}

function Row({ locale, label, value }: { locale: SupportedLocale; label: string; value: string }) {
  return (
    <div style={{ display: "flex", gap: 24, marginBottom: 18 }}>
      <div style={{ width: 420 }}>
        <AutoFitText text={label} locale={locale} maxWidth={400} maxHeight={64} role={theme.type.support} color={theme.color.muted} align="left" vertical="start" />
      </div>
      <div style={{ width: 400 }}>
        <AutoFitText text={value} locale={locale} maxWidth={400} maxHeight={64} role={theme.type.support} color={theme.color.ink} align="right" vertical="start" />
      </div>
    </div>
  );
}

function Steps({ locale, labels }: { locale: SupportedLocale; labels: string[] }) {
  return (
    <div>
      {labels.map((label, index) => (
        <div key={label} style={{ display: "flex", gap: 18, alignItems: "center", marginBottom: 16 }}>
          <div style={{ width: 36, height: 36, borderRadius: 18, border: theme.border.strong, color: theme.color.accent, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: fontFamilyFor(locale) }}>{index + 1}</div>
          <div style={{ flex: 1 }}>
            <Line locale={locale} text={label} role={theme.type.step} height={48} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function CardView({ cardId, locale }: { cardId: CardId; locale: SupportedLocale }) {
  const money = (value: number) => formatCurrency(value, SAMPLE.currency, locale);
  if (cardId === "kinetic_hook") {
    const hint = hintFor(cardId, locale);
    const text = t(locale, "hook.buy");
    const emphasis = segmentTextForMotion(text, locale).slice(-1);
    return (
      <Shell locale={locale}>
        <AutoFitText text={text} locale={locale} maxWidth={860} maxHeight={640} role={scaleRole(theme.type.hook, hint.headlineScale)} align="left" vertical="start" maxLines={hint.headlineMaxLines} emphasis={emphasis} animate="fade" />
      </Shell>
    );
  }
  if (cardId === "big_number") {
    return (
      <Shell locale={locale} kicker={t(locale, "process.steps")}>
        <Line locale={locale} text="3" role={theme.type.number} color={theme.color.accent} height={280} />
      </Shell>
    );
  }
  if (cardId === "property_price") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.price")}>
        <Line locale={locale} text={money(SAMPLE.price)} role={theme.type.number} color={theme.color.accent} height={220} />
        <Row locale={locale} label={t(locale, "comparison.before")} value={money(SAMPLE.previous)} />
        <Row locale={locale} label={t(locale, "comparison.after")} value={money(SAMPLE.price)} />
      </Shell>
    );
  }
  if (cardId === "rental_yield") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.rentalYield")}>
        <Line locale={locale} text={formatPercent(SAMPLE.yieldPercent, locale)} role={theme.type.number} color={theme.color.accent} height={200} />
        <Row locale={locale} label={t(locale, "realEstate.propertyValue")} value={money(SAMPLE.value)} />
        <Row locale={locale} label={t(locale, "realEstate.monthlyRent")} value={money(SAMPLE.monthlyRent)} />
        <Row locale={locale} label={t(locale, "realEstate.annualRent")} value={money(SAMPLE.annualRent)} />
      </Shell>
    );
  }
  if (cardId === "roi") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.roi")}>
        <Line locale={locale} text={formatPercent(SAMPLE.roiPercent, locale)} role={theme.type.number} color={theme.color.accent} height={200} />
        <Row locale={locale} label={t(locale, "roi.investment")} value={money(SAMPLE.investment)} />
        <Row locale={locale} label={t(locale, "roi.return")} value={money(SAMPLE.returnAmount)} />
      </Shell>
    );
  }
  if (cardId === "cash_flow") {
    const net = SAMPLE.income - SAMPLE.expenses;
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.cashFlow")}>
        <Row locale={locale} label={t(locale, "cashFlow.income")} value={money(SAMPLE.income)} />
        <Row locale={locale} label={t(locale, "cashFlow.expenses")} value={money(SAMPLE.expenses)} />
        <Row locale={locale} label={t(locale, "cashFlow.net")} value={money(net)} />
      </Shell>
    );
  }
  if (cardId === "property_comparison") {
    return (
      <Shell locale={locale} kicker={t(locale, "comparison.versus")}>
        <Row locale={locale} label={t(locale, "comparison.propertyA")} value={t(locale, "comparison.propertyB")} />
        <Row locale={locale} label={t(locale, "realEstate.price")} value={money(SAMPLE.price)} />
        <Row locale={locale} label={t(locale, "realEstate.size")} value={formatArea(SAMPLE.area, locale)} />
        <Row locale={locale} label={t(locale, "realEstate.location")} value={t(locale, "places.bangkok")} />
        <Row locale={locale} label={t(locale, "realEstate.yield")} value={formatPercent(SAMPLE.yieldPercent, locale)} />
        <Row locale={locale} label={t(locale, "realEstate.fees")} value={money(SAMPLE.fees)} />
      </Shell>
    );
  }
  if (cardId === "buy_vs_rent") {
    return (
      <Shell locale={locale}>
        <Line locale={locale} text={t(locale, "comparison.buy")} role={theme.type.hook} height={180} />
        <Line locale={locale} text={t(locale, "comparison.versus")} role={theme.type.label} color={theme.color.accent} height={48} />
        <Line locale={locale} text={t(locale, "comparison.rent")} role={theme.type.hook} height={180} />
      </Shell>
    );
  }
  if (cardId === "progress_steps") {
    return (
      <Shell locale={locale} kicker={t(locale, "process.step")}>
        <Steps locale={locale} labels={["process.search", "process.viewing", "process.offer", "process.contract", "process.handover"].map((key) => t(locale, key))} />
      </Shell>
    );
  }
  if (cardId === "document_check") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.documents")}>
        <Row locale={locale} label={t(locale, "document.verified")} value={t(locale, "document.approved")} />
        <Row locale={locale} label={t(locale, "document.review")} value={t(locale, "realEstate.documents")} />
      </Shell>
    );
  }
  if (cardId === "property_features") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.property")}>
        <Row locale={locale} label={t(locale, "features.bedrooms")} value={formatBedrooms(SAMPLE.bedrooms, locale)} />
        <Row locale={locale} label={t(locale, "features.bathrooms")} value={formatBathrooms(SAMPLE.bathrooms, locale)} />
        <Row locale={locale} label={t(locale, "features.area")} value={formatArea(SAMPLE.area, locale)} />
        <Row locale={locale} label={t(locale, "features.floor")} value={String(SAMPLE.floor)} />
        <Row locale={locale} label={t(locale, "features.parking")} value={formatNumber(1, locale)} />
        <Row locale={locale} label={t(locale, "features.balcony")} value={formatNumber(1, locale)} />
      </Shell>
    );
  }
  if (cardId === "location") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.location")}>
        <Row locale={locale} label={t(locale, "location.distance")} value={`${formatNumber(SAMPLE.distanceKm, locale, 1)} km`} />
        <Row locale={locale} label={t(locale, "realEstate.transport")} value={t(locale, "location.school")} />
        <Row locale={locale} label={t(locale, "location.shopping")} value={t(locale, "location.park")} />
      </Shell>
    );
  }
  if (cardId === "amenities") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.amenities")}>
        <Steps locale={locale} labels={["features.pool", "features.gym", "features.parking", "features.balcony"].map((key) => t(locale, key))} />
      </Shell>
    );
  }
  if (cardId === "timeline") {
    const dates = [new Date(2026, 2, 1), new Date(2026, 5, 1), new Date(2026, 8, 1)];
    const labels = ["process.search", "process.contract", "process.handover"];
    return (
      <Shell locale={locale} kicker={t(locale, "process.step")}>
        {dates.map((date, index) => (
          <Row key={labels[index]} locale={locale} label={formatDate(date, locale)} value={t(locale, labels[index])} />
        ))}
      </Shell>
    );
  }
  if (cardId === "before_after") {
    return (
      <Shell locale={locale}>
        <Row locale={locale} label={t(locale, "comparison.before")} value={money(SAMPLE.previous)} />
        <Row locale={locale} label={t(locale, "comparison.after")} value={money(SAMPLE.price)} />
      </Shell>
    );
  }
  if (cardId === "checklist") {
    return (
      <Shell locale={locale} kicker={t(locale, "checklist.title")}>
        <Steps locale={locale} labels={["checklist.inspection", "checklist.documents", "checklist.approval"].map((key) => t(locale, key))} />
      </Shell>
    );
  }
  if (cardId === "stat_reveal") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.occupancy")}>
        <Line locale={locale} text={formatPercent(SAMPLE.occupancy, locale)} role={theme.type.number} color={theme.color.accent} height={220} />
        <Line locale={locale} text={t(locale, "stat.support")} role={theme.type.support} color={theme.color.muted} height={80} />
      </Shell>
    );
  }
  if (cardId === "quote") {
    return (
      <Shell locale={locale}>
        <Line locale={locale} text={t(locale, "quote.line")} role={theme.type.hook} height={320} maxLines={4} />
      </Shell>
    );
  }
  if (cardId === "cta") {
    return (
      <Shell locale={locale} kicker={t(locale, "cta.contactUs")}>
        <Steps locale={locale} labels={["cta.learnMore", "cta.bookConsultation", "cta.seeProperties", "cta.startSearch"].map((key) => t(locale, key))} />
      </Shell>
    );
  }
  if (cardId === "caption_card") {
    const hint = hintFor(cardId, locale);
    return (
      <Shell locale={locale}>
        <Line locale={locale} text={t(locale, "stress.management")} role={scaleRole(theme.type.title, hint.headlineScale)} height={280} maxLines={hint.headlineMaxLines} />
        <Line locale={locale} text={t(locale, "stress.mortgage")} role={theme.type.support} color={theme.color.muted} height={120} />
      </Shell>
    );
  }
  if (cardId === "property_listing") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.condominium")}>
        <Line locale={locale} text={t(locale, "places.bangkok")} role={theme.type.title} height={90} />
        <Line locale={locale} text={formatCompactCurrency(SAMPLE.price, SAMPLE.currency, locale)} role={theme.type.number} color={theme.color.accent} height={180} />
        <Row locale={locale} label={formatArea(SAMPLE.area, locale)} value={formatBedrooms(SAMPLE.bedrooms, locale)} />
        <Row locale={locale} label={t(locale, "realEstate.yield")} value={formatPercent(SAMPLE.yieldPercent, locale)} />
      </Shell>
    );
  }
  if (cardId === "investment_card") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.investment")}>
        <Row locale={locale} label={t(locale, "realEstate.purchasePrice")} value={money(SAMPLE.price)} />
        <Row locale={locale} label={t(locale, "realEstate.monthlyRent")} value={money(SAMPLE.monthlyRent)} />
        <Row locale={locale} label={t(locale, "realEstate.annualIncome")} value={money(SAMPLE.annualRent)} />
        <Row locale={locale} label={t(locale, "realEstate.yield")} value={formatPercent(SAMPLE.yieldPercent, locale)} />
        <Row locale={locale} label={t(locale, "realEstate.roi")} value={formatPercent(SAMPLE.roiPercent, locale)} />
      </Shell>
    );
  }
  if (cardId === "location_card") {
    return (
      <Shell locale={locale} kicker={t(locale, "places.bangkok")}>
        <Line locale={locale} text={String(SAMPLE.score)} role={theme.type.number} color={theme.color.accent} height={180} />
        <Row locale={locale} label={t(locale, "location.score")} value={t(locale, "realEstate.location")} />
        <Row locale={locale} label={t(locale, "realEstate.transport")} value={t(locale, "location.distance")} />
        <Row locale={locale} label={t(locale, "realEstate.amenities")} value={t(locale, "location.park")} />
      </Shell>
    );
  }
  if (cardId === "legal_card") {
    return (
      <Shell locale={locale} kicker={t(locale, "realEstate.documents")}>
        <Row locale={locale} label={t(locale, "document.status")} value={t(locale, "document.approved")} />
        <Row locale={locale} label={t(locale, "document.verification")} value={t(locale, "document.verified")} />
        <Row locale={locale} label={t(locale, "document.risk")} value={t(locale, "document.review")} />
        <Row locale={locale} label={t(locale, "realEstate.approval")} value={t(locale, "document.approved")} />
      </Shell>
    );
  }
  const hint = hintFor("key_takeaway", locale);
  return (
    <Shell locale={locale}>
      <Line locale={locale} text={t(locale, "stress.international")} role={scaleRole(theme.type.hook, hint.headlineScale)} height={420} maxLines={hint.headlineMaxLines} />
    </Shell>
  );
}
