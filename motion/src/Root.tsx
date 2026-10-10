import { Composition } from "remotion";
import { CANVAS } from "./themes/tokens";
import { MotionLibraryShowcase } from "./showcase/MotionLibraryShowcase";
import { SHOWCASE_DURATION } from "./showcase/script";
import { PREVIEW_FRAMES, REAL_ESTATE_DURATION, RealEstateFilm } from "./preview/RealEstateFilm";
import { SOURCE_EDIT_BEATS, SOURCE_EDIT_DURATION, SOURCE_PREVIEW_FRAMES, SourceEdit } from "./preview/SourceEdit";
import { MULTILINGUAL_DURATION, MultilingualCardShowcase } from "./cards/MultilingualCardShowcase";
import { ImmigrationMotion } from "./immigration/scenes";
import { DIRECTOR_V3_FRAMES, DirectorV3, framesForSeconds, type DirectorV3Props } from "./preview/DirectorV3";

export function RemotionRoot() {
  return (
    <>
      <Composition
        id="MotionLibraryShowcase"
        component={MotionLibraryShowcase}
        durationInFrames={SHOWCASE_DURATION}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="RealEstateFilm"
        component={RealEstateFilm}
        durationInFrames={REAL_ESTATE_DURATION}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="RealEstatePreview"
        component={RealEstateFilm}
        durationInFrames={PREVIEW_FRAMES}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="SourceEdit"
        component={SourceEdit}
        defaultProps={{ beats: SOURCE_EDIT_BEATS }}
        durationInFrames={SOURCE_EDIT_DURATION}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="MultilingualCardShowcase"
        component={MultilingualCardShowcase}
        durationInFrames={MULTILINGUAL_DURATION}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="ImmigrationMotion"
        component={ImmigrationMotion}
        defaultProps={{ preset: "GlobalRoute" }}
        durationInFrames={120}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="DirectorV3Preview"
        component={DirectorV3}
        defaultProps={{ durationSeconds: 20, speakerFile: "speaker.mp4" } satisfies DirectorV3Props}
        calculateMetadata={({ props }) => {
          const frames = framesForSeconds(Number(props.durationSeconds ?? 20));
          return { durationInFrames: frames, props };
        }}
        durationInFrames={DIRECTOR_V3_FRAMES}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition
        id="SourceEditPreview"
        component={SourceEdit}
        defaultProps={{ beats: SOURCE_EDIT_BEATS }}
        durationInFrames={SOURCE_PREVIEW_FRAMES}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
    </>
  );
}
