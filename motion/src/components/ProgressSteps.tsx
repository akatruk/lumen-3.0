import { interpolate, useCurrentFrame } from "remotion";
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
  return (
    <SceneStage transition={scene.transition}>
      <SafeArea style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {scene.title ? (
          <div style={{ marginBottom: theme.space.xl }}>
            <AutoFitText
              text={scene.title}
              maxWidth={box.width}
              maxHeight={160}
              role={theme.type.title}
              align="left"
              vertical="start"
              animate="fade"
            />
          </div>
        ) : null}
        {scene.variant === "horizontal" ? (
          <Horizontal steps={scene.steps.map((step) => step.label)} states={states} width={box.width} />
        ) : null}
        {scene.variant === "vertical" ? (
          <Vertical steps={scene.steps.map((step) => step.label)} states={states} width={box.width} />
        ) : null}
        {scene.variant === "path" ? (
          <Path steps={scene.steps.map((step) => step.label)} states={states} width={box.width} />
        ) : null}
        {scene.variant === "progress_fill" ? (
          <Fill steps={scene.steps.map((step) => step.label)} width={box.width} />
        ) : null}
      </SafeArea>
    </SceneStage>
  );
}

function IndexMark({ index, state, size = 56 }: { index: number; state: StepState; size?: number }) {
  const background = state === "complete" ? theme.color.accent : "transparent";
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
        fontSize: 22,
        flex: "0 0 auto",
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
      <div style={{ position: "relative", height: 64, marginBottom: theme.space.lg }}>
        <div style={{ position: "absolute", left: 28, right: 28, top: 30 }}>
          <DrawLine length={Math.max(1, width - 56)} delay={2} duration={28} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", position: "relative" }}>
          {states.map((state, index) => (
            <IndexMark key={steps[index]} index={index} state={state} />
          ))}
        </div>
      </div>
      <div style={{ display: "flex", gap }}>
        {steps.map((label, index) => (
          <div key={label} style={{ width: column }}>
            <AutoFitText
              text={label}
              maxWidth={column}
              maxHeight={140}
              role={theme.type.step}
              color={states[index] === "upcoming" ? theme.color.muted : theme.color.ink}
              align="center"
              vertical="start"
              animate="none"
              wrapMode="auto"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function Vertical({ steps, states, width }: { steps: string[]; states: StepState[]; width: number }) {
  return (
    <Stagger interval={8}>
      {steps.map((label, index) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: theme.space.md, marginBottom: theme.space.lg }}>
          <IndexMark index={index} state={states[index]} />
          <AutoFitText
            text={label}
            maxWidth={width - 80}
            maxHeight={90}
            role={theme.type.step}
            color={states[index] === "upcoming" ? theme.color.muted : theme.color.ink}
            align="left"
            vertical="center"
            animate="none"
          />
        </div>
      ))}
    </Stagger>
  );
}

function Path({ steps, states, width }: { steps: string[]; states: StepState[]; width: number }) {
  return (
    <div style={{ display: "flex", gap: theme.space.md }}>
      <div style={{ width: 28, display: "flex", flexDirection: "column", alignItems: "center" }}>
        <DrawLine direction="vertical" length={steps.length * 120} delay={0} duration={36} />
        <AnimatedArrow direction="down" length={36} delay={28} />
      </div>
      <div style={{ flex: 1 }}>
        {steps.map((label, index) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: theme.space.md, minHeight: 120 }}>
            <IndexMark index={index} state={states[index]} size={44} />
            <AutoFitText
              text={label}
              maxWidth={width - 120}
              maxHeight={80}
              role={theme.type.step}
              align="left"
              vertical="center"
              animate="none"
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
      <ProgressFill duration={70} height={10} />
      <div style={{ display: "flex", marginTop: theme.space.lg }}>
        {steps.map((label) => (
          <div key={label} style={{ width: column }}>
            <AutoFitText
              text={label}
              maxWidth={column - theme.space.sm}
              maxHeight={140}
              role={theme.type.step}
              align="center"
              vertical="start"
              animate="none"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
