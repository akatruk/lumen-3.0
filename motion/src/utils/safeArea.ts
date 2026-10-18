import { CANVAS, SAFE_INSET } from "../themes/tokens";

export type SafeBox = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export function safeContentBox(width: number = CANVAS.width, height: number = CANVAS.height): SafeBox {
  const scaleX = width / CANVAS.width;
  const scaleY = height / CANVAS.height;
  const left = SAFE_INSET.left * scaleX;
  const right = SAFE_INSET.right * scaleX;
  const top = SAFE_INSET.top * scaleY;
  const bottom = SAFE_INSET.bottom * scaleY;
  return {
    x: left,
    y: top,
    width: Math.max(0, width - left - right),
    height: Math.max(0, height - top - bottom),
  };
}
