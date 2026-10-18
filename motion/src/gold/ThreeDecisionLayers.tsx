import { AbsoluteFill } from "remotion";
import type { SupportedLocale } from "../localization/language-config";
import { fontFamilyFor } from "../localization/fonts";
import { AutoFitText } from "../typography/AutoFitText";
import { LocaleProvider } from "../typography/locale";
import { theme } from "../themes/tokens";
import {
  GOLD_GRAPHIC,
  LAYER_COPY,
  LAYER_INDEX,
  layerMotion,
  visibleLayerCount,
  type LayerMotion,
} from "./threeLayersModel";

const INK = "#1c1917";
const BRONZE = "#8c5a32";
const PAPER = "rgba(252, 248, 242, 0.94)";

function stroke(draw: number) {
  return {
    fill: "none" as const,
    stroke: BRONZE,
    strokeWidth: 1.75,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    pathLength: 1,
    strokeDasharray: 1,
    strokeDashoffset: 1 - draw,
  };
}

function PlaceIcon({ draw }: { draw: number }) {
  const s = stroke(draw);
  return (
    <svg width={64} height={64} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M8 40 H56" {...s} />
      <path d="M18 40 V26 H30 V40" {...s} />
      <path d="M30 32 H46 V40" {...s} />
      <path d="M22 26 L24 18 H28 L30 26" {...s} />
      <path d="M36 32 V22 H42 V32" {...s} />
      <path d="M14 46 C24 42 40 50 52 44" {...s} />
    </svg>
  );
}

function FamilyIcon({ draw }: { draw: number }) {
  return (
    <svg width={64} height={64} viewBox="0 0 64 64" aria-hidden="true">
      <g fill={INK} opacity={draw}>
        <path d="M16 18c0-3.2 2.4-5.4 5.2-5.4S26.4 14.8 26.4 18 24 23.2 21.2 23.2 16 21.2 16 18z" />
        <path d="M10 46c0-8 4.2-13.2 11.2-13.2S32.4 38 32.4 46v4H10v-4z" />
        <path d="M30.5 21.5c0-4 3-6.6 6.5-6.6s6.5 2.6 6.5 6.6-3 6.8-6.5 6.8-6.5-2.8-6.5-6.8z" />
        <path d="M24 52c0-9.2 5-15.4 13-15.4S50 42.8 50 52v4H24v-4z" />
        <path d="M46.2 25.2c0-2.6 2-4.4 4.4-4.4s4.4 1.8 4.4 4.4-2 4.6-4.4 4.6-4.4-2-4.4-4.6z" />
        <path d="M41 52c0-6.4 3.2-10.6 9.2-10.6S59.4 45.6 59.4 52v4H41v-4z" />
      </g>
    </svg>
  );
}

function CostIcon({ draw }: { draw: number }) {
  const s = stroke(draw);
  return (
    <svg width={64} height={64} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 10 V22" {...s} />
      <path d="M18 22 H46" {...s} />
      <path d="M18 22 L10 40 H26 L18 22" {...s} />
      <path d="M46 22 L38 40 H54 L46 22" {...s} />
      <path d="M24 50 H40" {...s} />
      <path d="M28 50 V44 H36 V50" {...s} />
    </svg>
  );
}

const ICONS = [PlaceIcon, FamilyIcon, CostIcon];

function Row({
  index,
  locale,
  motion,
}: {
  index: number;
  locale: SupportedLocale;
  motion: LayerMotion;
}) {
  if (!motion.visible) return null;
  const Icon = ICONS[index];
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 18,
        height: motion.reduced ? 112 : 132,
        padding: "8px 16px",
        borderRadius: 22,
        background: PAPER,
        boxShadow: "0 10px 28px rgba(28, 25, 23, 0.16)",
        border: "1px solid rgba(140, 90, 50, 0.28)",
        opacity: motion.opacity,
        transform: `translateY(${motion.rise}px) scale(${motion.scale})`,
        transformOrigin: "left center",
      }}
    >
      <Icon draw={motion.draw} />
      <div style={{ display: "flex", flexDirection: "column", gap: 2, minWidth: 0, flex: 1 }}>
        <AutoFitText
          text={LAYER_INDEX[locale][index]}
          maxWidth={280}
          maxHeight={22}
          role={theme.type.label}
          color={BRONZE}
          locale={locale}
        />
        <AutoFitText
          text={LAYER_COPY[locale][index]}
          maxWidth={300}
          maxHeight={48}
          role={theme.type.step}
          color={INK}
          locale={locale}
        />
      </div>
    </div>
  );
}

export function ThreeDecisionLayers({
  frame,
  locale,
}: {
  frame: number;
  locale: SupportedLocale;
}) {
  const shown = visibleLayerCount(frame);
  const rail = shown === 0 ? 0 : Math.min(1, (shown - 1) / 2);
  const railOpacity = shown === 0 ? 0 : 0.7 * layerMotion(frame, shown - 1).opacity;
  return (
    <LocaleProvider locale={locale}>
      <AbsoluteFill style={{ pointerEvents: "none", fontFamily: fontFamilyFor(locale) }}>
        <div
          style={{
            position: "absolute",
            left: GOLD_GRAPHIC.left,
            top: GOLD_GRAPHIC.top,
            width: GOLD_GRAPHIC.width,
            height: GOLD_GRAPHIC.height,
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            gap: 10,
          }}
        >
          <div
            style={{
              position: "absolute",
              left: -14,
              top: 28,
              width: 2,
              height: rail * 340,
              background: BRONZE,
              opacity: railOpacity,
              borderRadius: 2,
            }}
          />
          {[0, 1, 2].map((index) => (
            <Row key={index} index={index} locale={locale} motion={layerMotion(frame, index)} />
          ))}
        </div>
      </AbsoluteFill>
    </LocaleProvider>
  );
}
