import type { CSSProperties, ReactNode } from "react";
import { useVideoConfig } from "remotion";
import { safeContentBox, type SafeBox } from "../utils/safeArea";

export function useSafeBox(): SafeBox {
  const { width, height } = useVideoConfig();
  return safeContentBox(width, height);
}

export function SafeArea({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  const box = useSafeBox();
  return (
    <div style={{ position: "absolute", left: box.x, top: box.y, width: box.width, height: box.height, ...style }}>
      {children}
    </div>
  );
}
