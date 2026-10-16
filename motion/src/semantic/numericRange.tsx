/**
 * Spoken min–max band. Endpoints are payload strings.
 * The bar draws across; the figures do not count through unstated values.
 */
import { useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import type { SupportedLocale } from "../localization/language-config";
import { rangeMotionAt } from "./motionDesign";
import type { SemanticMotionPayload } from "./types";

const KIND_LABEL: Record<string, Record<SupportedLocale, string>> = {
  salary: { "zh-CN": "月薪", "en-US": "Monthly pay", "ru-RU": "Месячная оплата" },
  day_rate: { "zh-CN": "每天", "en-US": "Per day", "ru-RU": "В день" },
  money: { "zh-CN": "金额", "en-US": "Amount", "ru-RU": "Сумма" },
};

export function rangeKindLabel(kind: string | undefined, locale: SupportedLocale): string {
  const table = KIND_LABEL[kind || ""] || KIND_LABEL.money;
  return table[locale] || table["en-US"];
}

function EndpointScale({ progress, stroke, width }: { progress: number; stroke: string; width: number }) {
  const right = Math.min(1, progress * 1.35);
  return (
    <div style={{ width, height: 28, position: "relative", flex: "0 0 auto" }}>
      <div
        style={{
          position: "absolute",
          left: 10,
          right: 10,
          top: 13,
          height: 2,
          background: stroke,
          transformOrigin: "left center",
          transform: `scaleX(${progress})`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 5,
          width: 16,
          height: 16,
          borderRadius: 8,
          background: stroke,
        }}
      />
      <div
        style={{
          position: "absolute",
          right: 0,
          top: 5,
          width: 16,
          height: 16,
          borderRadius: 8,
          boxSizing: "border-box",
          border: `2px solid ${stroke}`,
          background: progress > 0.92 ? stroke : "transparent",
          opacity: right,
        }}
      />
    </div>
  );
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
  const wide = boxWidth >= 700;
  const motion = rangeMotionAt(frame);
  const figureRole = wide ? theme.type.number : theme.type.title;
  const figureHeight = wide ? 132 : 112;
  const figureWidth = wide ? Math.max(240, Math.min(340, Math.floor((boxWidth - 220) / 2))) : Math.max(280, Math.min(460, boxWidth - 48));
  const scaleWidth = wide ? Math.max(160, Math.min(240, boxWidth - figureWidth * 2 - 48)) : figureWidth;
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: wide ? 18 : 12,
        alignItems: "center",
        background: "transparent",
      }}
    >
      <Fit text={label} width={Math.min(boxWidth - 32, wide ? 520 : figureWidth)} height={40} locale={locale} color={palette.muted} role={theme.type.label} />
      {wide ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, width: "100%" }}>
          <div style={{ width: figureWidth, opacity: motion.low }}>
            <Fit text={low} width={figureWidth} height={figureHeight} locale={locale} color={palette.text} role={figureRole} />
          </div>
          <EndpointScale progress={motion.span} stroke={palette.stroke} width={scaleWidth} />
          <div style={{ width: figureWidth, opacity: motion.high }}>
            <Fit text={high} width={figureWidth} height={figureHeight} locale={locale} color={palette.text} role={figureRole} />
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <div style={{ opacity: motion.low }}>
            <Fit text={low} width={figureWidth} height={figureHeight} locale={locale} color={palette.text} role={figureRole} />
          </div>
          <EndpointScale progress={motion.span} stroke={palette.stroke} width={scaleWidth} />
          <div style={{ opacity: motion.high }}>
            <Fit text={high} width={figureWidth} height={figureHeight} locale={locale} color={palette.text} role={figureRole} />
          </div>
        </div>
      )}
      {unit ? <Fit text={unit} width={figureWidth} height={48} locale={locale} color={palette.text} role={theme.type.support} /> : null}
    </div>
  );
}
