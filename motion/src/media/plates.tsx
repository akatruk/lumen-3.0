import type { CSSProperties, ReactNode } from "react";
import { AbsoluteFill, Img, OffthreadVideo } from "remotion";
import { Pan, Zoom } from "../primitives/camera";
import { theme } from "../themes/tokens";
import type { MediaSpec } from "../types/scene";
import { Placeholder } from "./Placeholder";

type Mask = "none" | "rounded" | "circle";
type Fit = "cover" | "contain";

function footage(media: MediaSpec, fit: Fit, showLabel: boolean, objectPosition?: string): ReactNode {
  if (media.kind !== "placeholder" && media.src) {
    const style: CSSProperties = { width: "100%", height: "100%", objectFit: fit, objectPosition };
    if (media.kind === "video") return <OffthreadVideo src={media.src} style={style} />;
    return <Img src={media.src} style={style} />;
  }
  return <Placeholder role={media.role} showLabel={showLabel} />;
}

function Frame({
  media,
  mask,
  fit,
  showLabel,
  objectPosition,
}: {
  media: MediaSpec;
  mask: Mask;
  fit: Fit;
  showLabel: boolean;
  objectPosition?: string;
}) {
  const radius = mask === "circle" ? theme.radius.pill : mask === "rounded" ? theme.radius.lg : 0;
  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        borderRadius: radius,
        background: theme.color.bg,
        boxShadow: mask === "circle" ? theme.shadow.ring : undefined,
        border: mask === "circle" ? theme.border.strong : undefined,
      }}
    >
      {footage(media, fit, showLabel && mask !== "circle", objectPosition)}
    </AbsoluteFill>
  );
}

export function SpeakerVideo({
  media,
  mask = "none",
  fit = "cover",
  objectPosition,
}: {
  media: MediaSpec;
  mask?: Mask;
  fit?: Fit;
  objectPosition?: string;
}) {
  return <Frame media={{ ...media, role: "speaker" }} mask={mask} fit={fit} showLabel objectPosition={objectPosition} />;
}

export function BrollVideo({
  media,
  mask = "none",
  fit = "cover",
}: {
  media: MediaSpec;
  mask?: Mask;
  fit?: Fit;
}) {
  return <Frame media={media.role === "broll" ? media : { ...media, role: "broll" }} mask={mask} fit={fit} showLabel />;
}

export function BackgroundVideo({
  media,
  mask = "none",
  fit = "cover",
}: {
  media: MediaSpec;
  mask?: Mask;
  fit?: Fit;
}) {
  return <Frame media={{ ...media, role: "background" }} mask={mask} fit={fit} showLabel={false} />;
}

export function ImageMedia({
  media,
  mask = "rounded",
  fit = "cover",
}: {
  media: MediaSpec;
  mask?: Mask;
  fit?: Fit;
}) {
  return <Frame media={{ ...media, role: "image" }} mask={mask} fit={fit} showLabel />;
}

export function ScreenshotMedia({
  media,
  mask = "rounded",
  fit = "contain",
}: {
  media: MediaSpec;
  mask?: Mask;
  fit?: Fit;
}) {
  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        borderRadius: mask === "circle" ? theme.radius.pill : theme.radius.lg,
        background: theme.color.paper,
        boxShadow: theme.shadow.paper,
        border: theme.border.paper,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 44,
          background: theme.color.paperInk,
          display: "flex",
          alignItems: "center",
          gap: theme.space.xs,
          paddingLeft: theme.space.md,
        }}
      >
        {[theme.color.accent, theme.color.muted, theme.color.ink].map((color) => (
          <span
            key={color}
            style={{ width: 8, height: 8, borderRadius: theme.radius.pill, background: color, display: "inline-block" }}
          />
        ))}
      </div>
      <div style={{ position: "absolute", top: 44, left: 0, right: 0, bottom: 0 }}>
        {footage({ ...media, role: "screenshot" }, fit, false)}
      </div>
    </AbsoluteFill>
  );
}

export function MediaPlate({
  media,
  mask = "none",
  fit = "cover",
  motion = "none",
  frames,
  objectPosition,
}: {
  media: MediaSpec;
  mask?: Mask;
  fit?: Fit;
  motion?: "none" | "pan" | "zoom";
  frames?: number;
  objectPosition?: string;
}) {
  const node =
    media.role === "speaker" ? (
      <SpeakerVideo media={media} mask={mask} fit={fit} objectPosition={objectPosition} />
    ) : media.role === "background" ? (
      <BackgroundVideo media={media} mask={mask} fit={fit} />
    ) : media.role === "image" ? (
      <ImageMedia media={media} mask={mask} fit={fit} />
    ) : media.role === "screenshot" ? (
      <ScreenshotMedia media={media} mask={mask} fit={fit} />
    ) : (
      <BrollVideo media={media} mask={mask} fit={fit} />
    );
  return (
    <AbsoluteFill style={{ overflow: "hidden", borderRadius: mask === "circle" ? "50%" : undefined }}>
      {motion === "pan" ? <Pan frames={frames}>{node}</Pan> : null}
      {motion === "zoom" ? <Zoom frames={frames} to={1.03}>{node}</Zoom> : null}
      {motion === "none" ? node : null}
    </AbsoluteFill>
  );
}
