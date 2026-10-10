import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, staticFile } from "remotion";
import { theme } from "../themes/tokens";
import { Zoom } from "../primitives/camera";
import { AutoFitText } from "../typography/AutoFitText";
import { normalizeScene } from "../registry/validateScene";
import { renderScene } from "../registry/motionRegistry";
import { useSafeBox } from "../layouts/SafeArea";
import beatFile from "./source-beats.json";

export type EditBeat = {
  id: string;
  from: number;
  durationInFrames: number;
  kind: "speaker" | "kinetic" | "steps" | "image" | "video";
  src?: string;
  caption?: string;
  emphasis?: string[];
  zoom?: number;
  title?: string;
  steps?: string[];
  circle?: boolean;
};

const file = (name: string) => staticFile(`source-edit/${name}`);

function Caption({ text, emphasis }: { text: string; emphasis?: string[] }) {
  const box = useSafeBox();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div style={{ position: "absolute", left: box.x, width: box.width, bottom: 80, height: 200 }}>
        <AutoFitText
          text={text}
          maxWidth={box.width}
          maxHeight={180}
          role={theme.type.caption}
          align="center"
          vertical="end"
          wrapMode="auto"
          emphasis={emphasis}
          animate="fade"
        />
      </div>
    </AbsoluteFill>
  );
}

function Speaker({ beat }: { beat: EditBeat }) {
  const box = useSafeBox();
  const video = (
    <OffthreadVideo
      src={file(beat.src || "")}
      volume={0}
      style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "center 28%" }}
    />
  );
  if (beat.circle) {
    const diameter = Math.min(box.width * 0.72, box.height * 0.42);
    return (
      <AbsoluteFill>
        <div style={{ position: "absolute", left: box.x, right: box.x, top: box.y + 40, display: "flex", justifyContent: "center" }}>
          <div
            style={{
              width: diameter,
              height: diameter,
              borderRadius: theme.radius.pill,
              overflow: "hidden",
              border: theme.border.strong,
              boxShadow: theme.shadow.ring,
            }}
          >
            {video}
          </div>
        </div>
        {beat.caption ? (
          <div style={{ position: "absolute", left: box.x, width: box.width, top: box.y + diameter + 80, height: 220 }}>
            <AutoFitText
              text={beat.caption}
              maxWidth={box.width}
              maxHeight={200}
              role={theme.type.title}
              align="center"
              vertical="start"
              wrapMode="auto"
              emphasis={beat.emphasis}
            />
          </div>
        ) : null}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill>
      <Zoom to={beat.zoom ?? 1.04} frames={beat.durationInFrames}>
        {video}
      </Zoom>
      <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      {beat.caption ? <Caption text={beat.caption} emphasis={beat.emphasis} /> : null}
    </AbsoluteFill>
  );
}

function LibraryStill({ beat }: { beat: EditBeat }) {
  const node = (
    <Zoom to={1.06} frames={beat.durationInFrames}>
      {beat.kind === "video" ? (
        <OffthreadVideo src={file(beat.src || "")} volume={0} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : (
        <Img src={file(beat.src || "")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      )}
    </Zoom>
  );
  return (
    <AbsoluteFill>
      {node}
      <AbsoluteFill style={{ background: theme.gradient.scrimBottom, pointerEvents: "none" }} />
      {beat.caption ? <Caption text={beat.caption} emphasis={beat.emphasis} /> : null}
    </AbsoluteFill>
  );
}

export function SourceEdit({ beats }: { beats: EditBeat[] }) {
  return (
    <AbsoluteFill style={{ background: theme.color.bg, fontFamily: theme.font.sans }}>
      <Audio src={file("narration.m4a")} />
      {beats.map((beat) => {
        let body = null;
        if (beat.kind === "speaker") body = <Speaker beat={beat} />;
        if (beat.kind === "kinetic") {
          body = renderScene(
            normalizeScene({
              id: beat.id,
              type: "kinetic_hook",
              variant: "scale_punch",
              durationInFrames: beat.durationInFrames,
              text: beat.caption,
              emphasis: beat.emphasis,
              transition: { type: "cut", durationInFrames: 0 },
            }),
          );
        }
        if (beat.kind === "steps") {
          body = renderScene(
            normalizeScene({
              id: beat.id,
              type: "progress_steps",
              variant: "vertical",
              durationInFrames: beat.durationInFrames,
              title: beat.title,
              steps: (beat.steps || []).map((label) => ({ label })),
              transition: { type: "cut", durationInFrames: 0 },
            }),
          );
        }
        if (beat.kind === "image" || beat.kind === "video") body = <LibraryStill beat={beat} />;
        return (
          <Sequence key={beat.id} from={beat.from} durationInFrames={beat.durationInFrames} name={beat.id}>
            {body}
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
}

export const SOURCE_EDIT_BEATS = beatFile.beats as EditBeat[];

export const SOURCE_EDIT_DURATION = beatFile.durationInFrames;
export const SOURCE_PREVIEW_FRAMES = 450;
