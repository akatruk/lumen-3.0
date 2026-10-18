/** SVG connector that applies adaptiveLineStyle (full-path contrast). */
import type { CSSProperties } from "react";
import {
  adaptiveLineStyle,
  pathFromSvgCommands,
  type BackgroundProbe,
  type PathPoint,
  type SceneTheme,
} from "../utils/adaptiveLineStyle";
import { theme } from "../themes/tokens";

export type ConnectorStrokeProps = {
  /** Straight segment */
  x1?: number;
  y1?: number;
  x2?: number;
  y2?: number;
  /** Or SVG path `d` */
  d?: string;
  pathPoints?: PathPoint[];
  preferredColor?: string;
  strokeWidth?: number;
  background?: BackgroundProbe;
  sceneTheme?: SceneTheme;
  opacity?: number;
  strokeDasharray?: string | number;
  strokeDashoffset?: string | number;
  strokeLinecap?: "butt" | "round" | "square";
  fill?: string;
  style?: CSSProperties;
};

function resolvePath(props: ConnectorStrokeProps): PathPoint[] {
  if (props.pathPoints?.length) return props.pathPoints;
  if (props.d) return pathFromSvgCommands(props.d);
  if (props.x1 != null && props.y1 != null && props.x2 != null && props.y2 != null) {
    return [
      { x: props.x1, y: props.y1 },
      { x: (props.x1 + props.x2) / 2, y: (props.y1 + props.y2) / 2 },
      { x: props.x2, y: props.y2 },
    ];
  }
  return [
    { x: 0, y: 0 },
    { x: 100, y: 0 },
  ];
}

export function resolveConnectorStyle(props: ConnectorStrokeProps) {
  return adaptiveLineStyle({
    background: props.background ?? theme.color.bg,
    path: resolvePath(props),
    preferredColor: props.preferredColor ?? theme.color.accent,
    strokeWidth: props.strokeWidth ?? 3,
    sceneTheme: props.sceneTheme ?? "auto",
  });
}

export function ConnectorLine(props: ConnectorStrokeProps) {
  const style = resolveConnectorStyle(props);
  const common = {
    opacity: props.opacity,
    strokeDasharray: props.strokeDasharray,
    strokeDashoffset: props.strokeDashoffset,
    strokeLinecap: props.strokeLinecap ?? ("round" as const),
    fill: props.fill ?? "none",
    style: props.style,
  };
  if (props.d) {
    return (
      <g>
        {style.outlineColor && style.outlineWidth > 0 ? (
          <path
            d={props.d}
            stroke={style.outlineColor}
            strokeWidth={(props.strokeWidth ?? 3) + style.outlineWidth * 2}
            {...common}
          />
        ) : null}
        <path d={props.d} stroke={style.strokeColor} strokeWidth={props.strokeWidth ?? 3} {...common} />
      </g>
    );
  }
  return (
    <g>
      {style.outlineColor && style.outlineWidth > 0 ? (
        <line
          x1={props.x1}
          y1={props.y1}
          x2={props.x2}
          y2={props.y2}
          stroke={style.outlineColor}
          strokeWidth={(props.strokeWidth ?? 3) + style.outlineWidth * 2}
          {...common}
        />
      ) : null}
      <line
        x1={props.x1}
        y1={props.y1}
        x2={props.x2}
        y2={props.y2}
        stroke={style.strokeColor}
        strokeWidth={props.strokeWidth ?? 3}
        {...common}
      />
    </g>
  );
}

export function ConnectorPolygon(props: ConnectorStrokeProps & { points: string }) {
  const style = resolveConnectorStyle(props);
  return (
    <g>
      {style.outlineColor && style.outlineWidth > 0 ? (
        <polygon
          points={props.points}
          fill={style.outlineColor}
          opacity={(props.opacity ?? 1) * 0.9}
        />
      ) : null}
      <polygon points={props.points} fill={style.strokeColor} opacity={props.opacity} />
    </g>
  );
}
