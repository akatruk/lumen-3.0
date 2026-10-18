/**
 * Isolated 8s preview. Three presentations, one payload shape.
 * Not mounted by DirectorV3Preview.
 */
import { AbsoluteFill, Easing, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { CANVAS, theme } from "../themes/tokens";
import { AutoFitText } from "../typography/AutoFitText";
import { LocaleProvider } from "../typography/locale";
import type { SupportedLocale } from "../localization/language-config";
import { PORTRAIT } from "./portraitLayouts";
import { NumericRangeV2 } from "../semantic/numericRangeV2";
import { graphicRect, splitFrame, type RangePresentation } from "../semantic/numericRangeModel";
import type { SemanticMotionPayload } from "../semantic/types";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const ease = Easing.inOut(Easing.cubic);

export type NumericRangeV2Segment = {
  startFrame: number;
  endFrame: number;
  caption: string;
  payload?: SemanticMotionPayload | null;
};

export type NumericRangeV2Props = {
  variant: RangePresentation;
  speakerFile: string;
  durationSeconds: number;
  locale: SupportedLocale;
  segments: NumericRangeV2Segment[];
};

const SALARY: SemanticMotionPayload = {
  componentId: "motion.numeric_range.v1",
  version: "v18",
  visualIntent: "numeric_range",
  locale: "zh-CN",
  range: { lowText: "1.5万", highText: "2.5万", unit: "泰国", kind: "salary" },
  labels: { "zh-CN": "月薪", "en-US": "Monthly pay", "ru-RU": "Месячная оплата" },
};

const CNY: SemanticMotionPayload = {
  componentId: "motion.numeric_range.v1",
  version: "v18",
  visualIntent: "numeric_range",
  locale: "zh-CN",
  range: { lowText: "3千", highText: "4千", unit: "人民币", kind: "money" },
  labels: { "zh-CN": "金额", "en-US": "Amount", "ru-RU": "Сумма" },
};

export const NUMERIC_RANGE_V2_DEFAULTS: NumericRangeV2Props = {
  variant: "finance",
  speakerFile: "director-v3/excerpt.mp4",
  durationSeconds: 8,
  locale: "zh-CN",
  segments: [
    { startFrame: 0, endFrame: 8, caption: "但是学历一般" },
    { startFrame: 8, endFrame: 164, caption: "月薪差不多在1.5-2.5万泰国左右吧", payload: SALARY },
    { startFrame: 164, endFrame: 224, caption: "折合人民币三四千", payload: CNY },
    { startFrame: 224, endFrame: 240, caption: "如果说你想要那种专业背景" },
  ],
};

function Caption({ text, locale }: { text: string; locale: SupportedLocale }) {
  const frame = useCurrentFrame();
  const clean = text.trim();
  if (!clean) return null;
  const enter = interpolate(frame, [0, 6], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 96,
          width: 888,
          bottom: PORTRAIT.captionClearance,
          height: 200,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          opacity: enter,
        }}
      >
        <div
          style={{
            maxWidth: 820,
            padding: "12px 28px 14px",
            borderRadius: 18,
            background: "rgba(8, 7, 6, 0.55)",
          }}
        >
          <AutoFitText
            text={clean}
            maxWidth={760}
            maxHeight={152}
            role={{ min: 42, max: 56, weight: 700, lineHeight: 1.16, tracking: -0.02 }}
            align="center"
            vertical="center"
            wrapMode="auto"
            maxLines={2}
            locale={locale}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
}

export function NumericRangeV2Film({
  variant,
  speakerFile,
  locale,
  segments,
}: NumericRangeV2Props) {
  const frame = useCurrentFrame();
  const shift = variant === "split" ? interpolate(frame, [0, 18], [0, 1], { ...clamp, easing: ease }) : 0;
  const placed = splitFrame(shift);
  const rect = graphicRect(variant);
  return (
    <LocaleProvider locale={locale}>
      <AbsoluteFill style={{ background: theme.color.bg }}>
        <AbsoluteFill
          style={{
            transform: `translate(${placed.translateX}px, ${placed.translateY}px) scale(${placed.scale})`,
            transformOrigin: "center center",
          }}
        >
          <OffthreadVideo
            src={staticFile(speakerFile)}
            volume={1}
            style={{ width: CANVAS.width, height: CANVAS.height, objectFit: "cover" }}
          />
        </AbsoluteFill>
        {variant === "split" ? (
          <div
            style={{
              position: "absolute",
              left: rect.left - 8,
              top: rect.top,
              width: 2,
              height: 460,
              background: "rgba(246,241,232,0.55)",
              opacity: shift,
            }}
          />
        ) : null}
        {segments.map((segment) => {
          const duration = Math.max(1, segment.endFrame - segment.startFrame);
          return (
            <Sequence key={`${segment.startFrame}-${segment.caption}`} from={segment.startFrame} durationInFrames={duration}>
              {segment.payload ? (
                <div style={{ position: "absolute", left: rect.left, top: rect.top, width: rect.width, height: rect.height }}>
                  <NumericRangeV2 presentation={variant} payload={segment.payload} locale={locale} frames={duration} />
                </div>
              ) : null}
              <Caption text={segment.caption} locale={locale} />
            </Sequence>
          );
        })}
      </AbsoluteFill>
    </LocaleProvider>
  );
}
