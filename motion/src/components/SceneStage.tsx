import type { ReactNode } from "react";
import { AbsoluteFill } from "remotion";
import { theme } from "../themes/tokens";
import type { SceneTransitionSpec } from "../types/scene";
import { SceneTransition } from "../transitions/SceneTransition";

export function SceneStage({
  transition,
  background = theme.color.bg,
  children,
}: {
  transition?: SceneTransitionSpec;
  background?: string;
  children: ReactNode;
}) {
  return (
    <SceneTransition transition={transition}>
      <AbsoluteFill
        style={{
          background,
          fontFamily: theme.font.sans,
          color: theme.color.ink,
          WebkitFontSmoothing: theme.font.smoothing,
        }}
      >
        {children}
      </AbsoluteFill>
    </SceneTransition>
  );
}
