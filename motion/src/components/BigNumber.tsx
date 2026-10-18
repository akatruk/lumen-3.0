import { useMemo } from "react";
import { theme, type TypeRole } from "../themes/tokens";
import type { BigNumberScene } from "../types/scene";
import { measureForRender } from "../utils/measure";
import { fitPhrase } from "../typography/fitPhrase";
import { lockedText } from "../typography/lock";
import { AutoFitText } from "../typography/AutoFitText";
import { CountUp, DrawLine, Pulse } from "../primitives/marks";
import { ScaleIn } from "../primitives/entrances";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

export function BigNumber({ scene }: { scene: BigNumberScene }) {
  const box = useSafeBox();
  const quiet = scene.variant === "minimal";
  const role: TypeRole = quiet ? theme.type.title : theme.type.number;
  const figure = `${scene.prefix ?? ""}${Number.isInteger(scene.value) ? String(scene.value) : scene.value}${scene.suffix ?? ""}`;
  const layout = useMemo(
    () =>
      fitPhrase({
        text: figure,
        maxWidth: Math.max(1, box.width - theme.space.lg),
        maxHeight: quiet ? 160 : box.height * 0.58,
        role,
        measure: (value, size) => measureForRender(value, size, theme.font.sans, role.weight, role.tracking),
      }),
    [figure, box.width, box.height, quiet, role],
  );
  const numberStyle = {
    ...lockedText,
    fontFamily: theme.font.sans,
    fontSize: layout.fontSize,
    fontWeight: role.weight,
    letterSpacing: `${role.tracking}em`,
    lineHeight: role.lineHeight,
    fontVariantNumeric: theme.font.numeric,
    color: scene.variant === "scale_in" ? theme.color.paperInk : scene.variant === "count_up" ? theme.color.accent : theme.color.ink,
  };

  const number =
    scene.variant === "count_up" ? (
      <span style={numberStyle}>
        <CountUp value={scene.value} prefix={scene.prefix} suffix={scene.suffix} duration={42} />
      </span>
    ) : (
      <span style={numberStyle}>
        {scene.prefix}
        {Number.isInteger(scene.value) ? String(scene.value) : String(scene.value)}
        {scene.suffix}
      </span>
    );

  return (
    <SceneStage transition={scene.transition} background={scene.variant === "scale_in" ? theme.color.bg : theme.color.bg}>
      <SafeArea>
        {scene.variant === "scale_in" ? (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <ScaleIn from={0.97} duration={18}>
              <div
                style={{
                  background: theme.color.paper,
                  borderRadius: theme.radius.lg,
                  padding: `${theme.space.xl}px ${theme.space.xxl}px`,
                  boxShadow: theme.shadow.paper,
                  minWidth: box.width * 0.72,
                }}
              >
                {number}
                <Label text={scene.label} width={box.width * 0.62} color={theme.color.paperInk} />
              </div>
            </ScaleIn>
          </div>
        ) : scene.variant === "minimal" ? (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              {number}
              <div style={{ marginTop: theme.space.md }}>
                <DrawLine length={96} color={theme.color.lineStrong} delay={4} />
              </div>
            </div>
            <Label text={scene.label} width={box.width * 0.7} align="left" />
          </div>
        ) : scene.variant === "impact" ? (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            {number}
            <div style={{ marginTop: theme.space.lg, marginBottom: theme.space.lg }}>
              <DrawLine length={box.width} thickness={2} delay={6} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: theme.space.sm }}>
              <Pulse>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: theme.radius.pill,
                    background: theme.color.accent,
                    display: "inline-block",
                  }}
                />
              </Pulse>
              <Label text={scene.label} width={box.width - 32} />
            </div>
          </div>
        ) : (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            {number}
            <div style={{ height: theme.space.lg }} />
            <Label text={scene.label} width={box.width} align="center" />
          </div>
        )}
      </SafeArea>
    </SceneStage>
  );
}

function Label({
  text,
  width,
  align = "left",
  color = theme.color.muted,
}: {
  text: string;
  width: number;
  align?: "left" | "center";
  color?: string;
}) {
  return (
    <AutoFitText
      text={text}
      maxWidth={width}
      maxHeight={120}
      role={theme.type.support}
      color={color}
      align={align}
      vertical="start"
      animate="none"
    />
  );
}
