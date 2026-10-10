import { Composition } from "remotion";
import { AbstractDrift } from "./AbstractDrift";
import { DocumentApproval } from "./DocumentApproval";
import { GlobalRoute } from "./GlobalRoute";
import { LocationPins } from "./LocationPins";
import { TargetHit } from "./TargetHit";

const fps = 30;
const width = 1080;
const height = 1920;

export function ClipRoot() {
  return (
    <>
      <Composition id="TargetHit" component={TargetHit} durationInFrames={120} fps={fps} width={width} height={height} />
      <Composition id="GlobalRoute" component={GlobalRoute} durationInFrames={120} fps={fps} width={width} height={height} />
      <Composition id="LocationPins" component={LocationPins} durationInFrames={120} fps={fps} width={width} height={height} />
      <Composition id="DocumentApproval" component={DocumentApproval} durationInFrames={120} fps={fps} width={width} height={height} />
      <Composition id="AbstractDrift" component={AbstractDrift} durationInFrames={120} fps={fps} width={width} height={height} />
    </>
  );
}
