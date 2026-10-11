import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { theme } from "../themes/tokens";
import type { ProgressStepsScene, StepState } from "../types/scene";
import { AutoFitText } from "../typography/AutoFitText";
import { AnimatedArrow, DrawLine, ProgressFill } from "../primitives/marks";
import { Stagger } from "../primitives/reveal";
import { SafeArea, useSafeBox } from "../layouts/SafeArea";
import { SceneStage } from "./SceneStage";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

function resolveState(index: number, count: number, frame: number, duration: number, explicit?: StepState): StepState {
  if (explicit) return explicit;
  const progress = interpolate(frame, [0, Math.max(1, duration - 1)], [0, 1], clamp);
  const cursor = progress * count;
  if (index < Math.floor(cursor)) return "complete";
  if (index <= Math.floor(cursor)) return "current";
  return "upcoming";
}

export function ProgressSteps({ scene }: { scene: ProgressStepsScene }) {
  const frame = useCurrentFrame();
  const box = useSafeBox();
  const states = scene.steps.map((step, index) =>
    resolveState(index, scene.steps.length, frame, scene.durationInFrames, step.state),
  );
  // Fill the portrait stage — title + steps share vertical space; no tiny cluster on empty black.
  // Reserve space for Director caption pill overlay (shared, not clip-hardcoded).
  const captionReserve = Math.round(box.height * 0.14);
  const titleH = scene.title ? Math.min(180, Math.round(box.height * 0.12)) : 0;
  const bodyH = Math.max(320, box.height - titleH - captionReserve - theme.space.md);
  return (
    <SceneStage transition={scene.transition}>
      <AbsoluteFill style={{ background: theme.gradient.speaker }} />
      <SafeArea
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-start",
          paddingTop: theme.space.sm,
          paddingBottom: captionReserve,
        }}
      >
        {scene.title ? (
          <div style={{ marginBottom: theme.space.md, height: titleH, flex: "0 0 auto" }}>
            <AutoFitText
              text={scene.title}
              maxWidth={box.width}
              maxHeight={titleH}
              role={theme.type.hook}
              align="left"
              vertical="start"
              animate="fade"
              wrapMode="auto"
              maxLines={2}
            />
          </div>
        ) : null}
        <div style={{ flex: 1, minHeight: bodyH, display: "flex", flexDirection: "column", justifyContent: "flex-start" }}>
          {scene.variant === "horizontal" ? (
            <Horizontal steps={scene.steps.map((step) => step.label)} states={states} width={box.width} />
          ) : null}
          {scene.variant === "vertical" ? (
            <Vertical steps={scene.steps.map((step) => step.label)} states={states} width={box.width} bodyHeight={bodyH} />
          ) : null}
          {scene.variant === "path" ? (
            <Path steps={scene.steps.map((step) => step.label)} states={states} width={box.width} />
          ) : null}
          {scene.variant === "progress_fill" ? (
            <Fill steps={scene.steps.map((step) => step.label)} width={box.width} />
          ) : null}
        </div>
      </SafeArea>
    </SceneStage>
  );
}

function IndexMark({ index, state, size = 72 }: { index: number; state: StepState; size?: number }) {
  const background = state === "complete" ? theme.color.accent : theme.color.bgElevated;
  const color = state === "complete" ? theme.color.accentInk : state === "current" ? theme.color.ink : theme.color.muted;
  const border = state === "complete" ? "none" : state === "current" ? theme.border.strong : theme.border.hairline;
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: theme.radius.pill,
        background,
        color,
        border,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: theme.font.sans,
        fontWeight: 600,
        fontSize: Math.round(size * 0.38),
        flex: "0 0 auto",
        boxShadow: theme.shadow.soft,
      }}
    >
      {index + 1}
    </div>
  );
}

function Horizontal({ steps, states, width }: { steps: string[]; states: StepState[]; width: number }) {
  const gap = theme.space.md;
  const column = (width - gap * (steps.length - 1)) / steps.length;
  return (
    <div>
      <div style={{ position: "relative", height: 80, marginBottom: theme.space.xl }}>
        <div style={{ position: "absolute", left: 36, right: 36, top: 38 }}>
          <DrawLine length={Math.max(1, width - 72)} delay={2} duration={28} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", position: "relative" }}>
          {states.map((state, index) => (
            <IndexMark key={steps[index]} index={index} state={state} />
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap }}>
        {steps.map((label, index) => (
          <div
            key={label}
            style={{
              width: column,
              padding: "20px 16px",
              borderRadius: theme.radius.lg,
              background: theme.color.bgElevated,
              border: `1px solid ${theme.color.line}`,
              minHeight: 160,
            }}
          >
            <AutoFitText
              text={label}
              maxWidth={column - 32}
              maxHeight={120}
              role={theme.type.title}
              color={states[index] === "upcoming" ? theme.color.muted : theme.color.ink}
              align="center"
              vertical="center"
              animate="none"
              wrapMode="auto"
              maxLines={2}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function Vertical({
  steps,
  states,
  width,
  bodyHeight,
}: {
  steps: string[];
  states: StepState[];
  width: number;
  bodyHeight: number;
}) {
  const gap = theme.space.md;
  const rowH = Math.max(148, Math.floor((bodyHeight - gap * (steps.length - 1)) / Math.max(1, steps.length)));
  return (
    <Stagger interval={8}>
      {steps.map((label, index) => (
        <div
          key={label}
          style={{
            display: "flex",
            alignItems: "center",
            gap: theme.space.lg,
            marginBottom: index < steps.length - 1 ? gap : 0,
            height: rowH,
            padding: "28px 32px",
            borderRadius: theme.radius.lg,
            background: theme.color.bgElevated,
            border: `1px solid ${states[index] === "current" ? theme.color.lineStrong : theme.color.line}`,
            boxShadow: theme.shadow.soft,
          }}
        >
          <IndexMark index={index} state={states[index]} size={88} />
          <AutoFitText
            text={label}
            maxWidth={width - 160}
            maxHeight={Math.min(130, rowH - 36)}
            role={theme.type.hook}
            color={states[index] === "upcoming" ? theme.color.muted : theme.color.ink}
            align="left"
            vertical="center"
            animate="none"
            wrapMode="auto"
            maxLines={2}
          />
        </div>
      ))}
    </Stagger>
  );
}

function Path({ steps, states, width }: { steps: string[]; states: StepState[]; width: number }) {
  return (
    <div style={{ display: "flex", gap: theme.space.lg }}>
      <div style={{ width: 36, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <DrawLine direction="vertical" length={steps.length * 140} delay={0} duration={36} />
        <AnimatedArrow direction="down" length={40} delay={28} />
      </div>
      <div style={{ flex: 1 }}>
        {steps.map((label, index) => (
          <div
            key={label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: theme.space.md,
              minHeight: 140,
              marginBottom: theme.space.md,
              padding: "18px 22px",
              borderRadius: theme.radius.lg,
              background: theme.color.bgElevated,
              border: `1px solid ${theme.color.line}`,
            }}
          >
            <IndexMark index={index} state={states[index]} size={56} />
            <AutoFitText
              text={label}
              maxWidth={width - 160}
              maxHeight={96}
              role={theme.type.title}
              align="left"
              vertical="center"
              animate="none"
              wrapMode="auto"
              maxLines={2}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function Fill({ steps, width }: { steps: string[]; width: number }) {
  const column = width / steps.length;
  return (
    <div>
      <ProgressFill duration={70} height={14} />
      <div style={{ display: "flex", marginTop: theme.space.xl, gap: theme.space.sm }}>
        {steps.map((label) => (
          <div
            key={label}
            style={{
              width: column - theme.space.sm,
              padding: "18px 12px",
              borderRadius: theme.radius.md,
              background: theme.color.bgElevated,
              minHeight: 140,
            }}
          >
            <AutoFitText
              text={label}
              maxWidth={column - theme.space.lg}
              maxHeight={120}
              role={theme.type.title}
              align="center"
              vertical="center"
              animate="none"
              wrapMode="auto"
              maxLines={2}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
