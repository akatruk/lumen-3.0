import type { CSSProperties } from "react";
import { theme } from "../themes/tokens";
import type { MediaRole } from "../types/scene";
import { lockedText } from "../typography/lock";

const LABEL: Record<MediaRole, string> = {
  speaker: "Speaker",
  broll: "Footage",
  background: "Footage",
  image: "Image",
  screenshot: "Screen",
};

export function Placeholder({
  role,
  showLabel = true,
}: {
  role: MediaRole;
  showLabel?: boolean;
}) {
  const labelStyle: CSSProperties = {
    ...lockedText,
    position: "absolute",
    left: theme.space.md,
    top: theme.space.md,
    fontFamily: theme.font.sans,
    fontSize: theme.type.label.min,
    fontWeight: theme.type.label.weight,
    letterSpacing: "0.14em",
    textTransform: "uppercase",
    color: role === "screenshot" ? theme.color.paperInk : theme.color.muted,
  };
  return (
    <div style={{ position: "absolute", inset: 0, background: theme.gradient[role], overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: theme.gradient.vignette }} />
      {role === "speaker" ? <SpeakerMark /> : null}
      {role === "broll" || role === "background" || role === "image" ? <Horizon /> : null}
      {showLabel ? <span style={labelStyle}>{LABEL[role]}</span> : null}
    </div>
  );
}

function SpeakerMark() {
  return (
    <>
      <div
        style={{
          position: "absolute",
          top: "16%",
          left: "36%",
          width: "28%",
          aspectRatio: "1",
          borderRadius: theme.radius.pill,
          background: theme.color.inkSoft,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "15%",
          right: "15%",
          bottom: "-8%",
          height: "48%",
          borderTopLeftRadius: "50% 70%",
          borderTopRightRadius: "50% 70%",
          background: theme.color.inkFaint,
        }}
      />
    </>
  );
}

function Horizon() {
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: "62%",
        height: 1,
        background: theme.color.lineStrong,
      }}
    />
  );
}
