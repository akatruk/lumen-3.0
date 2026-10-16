/**
 * Static studies for three art directions. Not a product composition.
 * Labels are the verified source strings. Geometry matches editorialFocusRects.
 */
import type { ReactNode } from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { CANVAS, theme } from "../themes/tokens";
import { editorialFocusRects, captionBand } from "./layouts";

export type ArtStudyProps = {
  concept: "a" | "b" | "c";
  kind: "timeline" | "range";
  state: "initial" | "active" | "complete";
  face: "face2" | "face3";
  caption: string;
};

const ink = theme.color.ink;
const muted = theme.color.muted;
const accent = theme.color.accent;
const bg = theme.color.bg;

const LEVELS = ["使用场景", "家庭结构", "代价"] as const;

function Stage({ face, caption, children }: { face: string; caption: string; children: ReactNode }) {
  const { graphic, speaker } = editorialFocusRects();
  const cap = captionBand();
  return (
    <AbsoluteFill style={{ background: bg, fontFamily: '"PingFang SC", "Hiragino Sans GB", Arial, sans-serif' }}>
      <div style={{ position: "absolute", left: graphic.left, top: graphic.top, width: graphic.width, height: graphic.height }}>{children}</div>
      <div style={{ position: "absolute", left: speaker.left, top: speaker.top, width: speaker.width, height: speaker.height, borderRadius: 28, overflow: "hidden" }}>
        <Img src={staticFile(`art-study/${face}.png`)} style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center 22%" }} />
      </div>
      <div style={{ position: "absolute", left: 120, width: 840, top: cap.top + 88, display: "flex", justifyContent: "center" }}>
        <div style={{ maxWidth: 760, padding: "12px 28px 14px", borderRadius: 18, background: "rgba(8,7,6,0.55)" }}>
          <div style={{ color: ink, fontSize: 42, fontWeight: 700, lineHeight: 1.15, textAlign: "center" }}>{caption}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
}

function TypeTimeline({ state }: { state: ArtStudyProps["state"] }) {
  const shown = state === "initial" ? 1 : state === "active" ? 2 : 3;
  const active = shown - 1;
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", paddingLeft: 8, gap: 28 }}>
      {LEVELS.slice(0, shown).map((label, index) => {
        const on = index === active;
        return (
          <div key={label} style={{ color: on ? ink : muted, fontWeight: 600, fontSize: on ? 92 : 40, lineHeight: 1.05, letterSpacing: on ? -1 : 0 }}>
            {label}
          </div>
        );
      })}
    </div>
  );
}

function TypeRange({ state }: { state: ArtStudyProps["state"] }) {
  const high = state !== "initial";
  const unit = state === "complete";
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 8px" }}>
      <div style={{ color: muted, fontSize: 28, fontWeight: 500, marginBottom: 18 }}>每天</div>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <div style={{ color: ink, fontSize: 108, fontWeight: 600, letterSpacing: -2, lineHeight: 0.9 }}>400</div>
        <div style={{ color: accent, fontSize: 72, fontWeight: 500, opacity: high ? 1 : 0.25, padding: "0 12px" }}>–</div>
        <div style={{ color: ink, fontSize: 108, fontWeight: 600, letterSpacing: -2, lineHeight: 0.9, opacity: high ? 1 : 0 }}>{high ? "1200" : ""}</div>
      </div>
      <div style={{ color: ink, fontSize: 36, fontWeight: 500, marginTop: 16, opacity: unit ? 1 : 0 }}>人民币</div>
    </div>
  );
}

function SpatialTimeline({ state }: { state: ArtStudyProps["state"] }) {
  const shown = state === "initial" ? 1 : state === "active" ? 2 : 3;
  const active = shown - 1;
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {LEVELS.map((label, index) => {
        const open = index < shown;
        const on = index === active;
        return (
          <div key={label} style={{ flex: 1, display: "flex", alignItems: "center", borderTop: index === 0 ? "none" : `1px solid rgba(246,241,232,0.16)`, paddingLeft: 8 }}>
            <div style={{ width: 6, alignSelf: "stretch", margin: "22px 0", background: on ? accent : "transparent", marginRight: 22 }} />
            <div style={{ color: on ? ink : muted, fontSize: on ? 64 : 36, fontWeight: 600, letterSpacing: -0.5, opacity: open ? 1 : 0 }}>{label}</div>
          </div>
        );
      })}
    </div>
  );
}

function SpatialRange({ state }: { state: ArtStudyProps["state"] }) {
  const span = state === "initial" ? 0.08 : state === "active" ? 0.55 : 1;
  const high = state === "complete";
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 4px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 18 }}>
        <div style={{ color: ink, fontSize: 84, fontWeight: 600, letterSpacing: -2, lineHeight: 0.9 }}>400</div>
        <div style={{ color: muted, fontSize: 26, paddingBottom: 10 }}>每天</div>
        <div style={{ color: ink, fontSize: 84, fontWeight: 600, letterSpacing: -2, lineHeight: 0.9, opacity: high ? 1 : 0.2 }}>{high ? "1200" : ""}</div>
      </div>
      <div style={{ position: "relative", height: 18 }}>
        <div style={{ position: "absolute", left: 8, top: 8, height: 2, width: `calc((100% - 16px) * ${span})`, background: accent }} />
        <div style={{ position: "absolute", left: 0, top: 1, width: 16, height: 16, borderRadius: 8, background: accent }} />
        <div style={{ position: "absolute", right: 0, top: 1, width: 16, height: 16, borderRadius: 8, border: `2px solid ${accent}`, background: high ? accent : "transparent", opacity: high ? 1 : 0.45 }} />
      </div>
      <div style={{ color: ink, fontSize: 32, fontWeight: 500, textAlign: "center", marginTop: 22, opacity: high ? 1 : 0 }}>人民币</div>
    </div>
  );
}

function CinemaTimeline({ state }: { state: ArtStudyProps["state"] }) {
  const shown = state === "initial" ? 1 : state === "active" ? 2 : 3;
  const active = shown - 1;
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", gap: 18, alignItems: "center", minHeight: 48 }}>
        {LEVELS.slice(0, shown).map((label, index) => (
          <div key={label} style={{ display: "flex", gap: 18, alignItems: "center" }}>
            {index > 0 ? <div style={{ width: 18, height: 1, background: muted }} /> : null}
            <div style={{ color: index === active ? accent : muted, fontSize: 26, fontWeight: 600 }}>{label}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center" }}>
        <div style={{ color: ink, fontSize: 120, fontWeight: 600, letterSpacing: -2, lineHeight: 0.95 }}>{LEVELS[active]}</div>
      </div>
    </div>
  );
}

function CinemaRange({ state }: { state: ArtStudyProps["state"] }) {
  const high = state !== "initial";
  const settled = state === "complete";
  return (
    <div style={{ height: "100%", position: "relative" }}>
      <div style={{ position: "absolute", left: settled || high ? 0 : 180, top: settled ? 36 : 150, color: ink, fontSize: settled ? 72 : 120, fontWeight: 600, letterSpacing: -2 }}>400</div>
      {high ? (
        <div style={{ position: "absolute", left: 120, right: 80, top: settled ? 250 : 300, height: 2, background: accent, transformOrigin: "left center", transform: `scaleX(${settled ? 1 : 0.45})` }} />
      ) : null}
      <div style={{ position: "absolute", right: 0, bottom: settled ? 48 : 80, color: ink, fontSize: settled ? 120 : 72, fontWeight: 600, letterSpacing: -2, opacity: high ? 1 : 0 }}>1200</div>
      <div style={{ position: "absolute", left: 0, bottom: 0, color: muted, fontSize: 28, opacity: settled ? 1 : 0 }}>每天 · 人民币</div>
    </div>
  );
}

export const ArtDirectionStudy: React.FC<ArtStudyProps> = ({ concept, kind, state, face, caption }) => {
  let body: ReactNode = null;
  if (concept === "a" && kind === "timeline") body = <TypeTimeline state={state} />;
  if (concept === "a" && kind === "range") body = <TypeRange state={state} />;
  if (concept === "b" && kind === "timeline") body = <SpatialTimeline state={state} />;
  if (concept === "b" && kind === "range") body = <SpatialRange state={state} />;
  if (concept === "c" && kind === "timeline") body = <CinemaTimeline state={state} />;
  if (concept === "c" && kind === "range") body = <CinemaRange state={state} />;
  return (
    <Stage face={face} caption={caption}>
      {body}
    </Stage>
  );
};

export const ART_STUDY_SIZE = { width: CANVAS.width, height: CANVAS.height, fps: CANVAS.fps };
