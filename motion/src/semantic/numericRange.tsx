/**
 * Spoken min–max band. Endpoints are payload strings.
 * The bar draws across; the figures do not count through unstated values.
 */
import { interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import type { SupportedLocale } from "../localization/language-config";
import type { SemanticMotionPayload } from "./types";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const KIND_LABEL: Record<string, Record<SupportedLocale, string>> = {
  salary: { "zh-CN": "月薪", "en-US": "Monthly pay", "ru-RU": "Месячная оплата" },
  day_rate: { "zh-CN": "每天", "en-US": "Per day", "ru-RU": "В день" },
  money: { "zh-CN": "金额", "en-US": "Amount", "ru-RU": "Сумма" },
};

export function rangeKindLabel(kind: string | undefined, locale: SupportedLocale): string {
  const table = KIND_LABEL[kind || ""] || KIND_LABEL.money;
  return table[locale] || table["en-US"];
}

function Fit({
  text,
  width,
  height,
  locale,
  color,
  role,
}: {
  text: string;
  width: number;
  height: number;
  locale: SupportedLocale;
  color: string;
  role: typeof theme.type.title | typeof theme.type.support | typeof theme.type.label | typeof theme.type.number;
}) {
  if (!text) return null;
  return (
    <div style={{ width, maxWidth: "100%", color, textAlign: "center" }}>
      <AutoFitText
        text={text}
        maxWidth={width}
        maxHeight={height}
        role={role}
        align="center"
        vertical="center"
        locale={locale}
        color={color}
      />
    </div>
  );
}

export function NumericRange({
  payload,
  palette,
  locale,
  boxWidth = 504,
}: {
  payload: SemanticMotionPayload;
  palette: { stroke: string; text: string; muted: string };
  locale: SupportedLocale;
  boxWidth?: number;
}) {
  const frame = useCurrentFrame();
  const range = payload.range;
  const low = String(range?.lowText || "").trim();
  const high = String(range?.highText || "").trim();
  if (!low || !high) return null;
  const stamped = payload.labels || {};
  const label =
    (locale.startsWith("zh") ? stamped["zh-CN"] : locale.startsWith("ru") ? stamped["ru-RU"] : stamped["en-US"]) ||
    rangeKindLabel(range?.kind, locale);
  const unit = String(range?.unit || "").trim();
  const figureWidth = Math.max(360, Math.min(760, boxWidth - 80));
  const wide = boxWidth >= 700;
  const figureRole = wide ? theme.type.number : theme.type.title;
  const figureHeight = wide ? 150 : 160;
  const grow = interpolate(frame, [8, 28], [0.08, 1], clamp);
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 10,
        alignItems: "center",
        background: "transparent",
        textShadow: "0 2px 10px rgba(12,11,10,0.72)",
      }}
    >
      <Fit text={label} width={figureWidth} height={56} locale={locale} color={palette.muted} role={theme.type.label} />
      <Fit text={low} width={figureWidth} height={figureHeight} locale={locale} color={palette.text} role={figureRole} />
      <div style={{ width: "100%", height: 18, borderRadius: 9, background: "rgba(246,241,232,0.28)", overflow: "hidden" }}>
        <div style={{ width: `${grow * 100}%`, height: "100%", background: palette.stroke }} />
      </div>
      <Fit text={high} width={figureWidth} height={figureHeight} locale={locale} color={palette.text} role={figureRole} />
      {unit ? <Fit text={unit} width={figureWidth} height={64} locale={locale} color={palette.text} role={theme.type.support} /> : null}
    </div>
  );
}
