import type { ComponentType } from "react";
import { Composition } from "remotion";
import { AbstractDrift } from "./AbstractDrift";
import { DocumentApproval } from "./DocumentApproval";
import { GlobalRoute } from "./GlobalRoute";
import { LocationPins } from "./LocationPins";
import { TargetHit } from "./TargetHit";
import {
  ApprovalDesk,
  CheckStamp,
  ChoiceFork,
  CompareColumns,
  DeadlineScale,
  DiagonalMask,
  FolderReveal,
  GoldDust,
  GrowthArrow,
  MobilityPins,
  NavyBreathe,
  PathDraw,
  RingReveal,
  RiskFall,
  ShieldPulse,
  SoftGrid,
  StepCascade,
  WipeArc,
} from "./premium";

const fps = 30;
const width = 1080;
const height = 1920;
const durationInFrames = 120;

function clip(id: string, component: ComponentType) {
  return (
    <Composition
      id={id}
      component={component}
      durationInFrames={durationInFrames}
      fps={fps}
      width={width}
      height={height}
    />
  );
}

export function ClipRoot() {
  return (
    <>
      {clip("TargetHit", TargetHit)}
      {clip("GlobalRoute", GlobalRoute)}
      {clip("LocationPins", LocationPins)}
      {clip("DocumentApproval", DocumentApproval)}
      {clip("AbstractDrift", AbstractDrift)}
      {clip("GrowthArrow", GrowthArrow)}
      {clip("RiskFall", RiskFall)}
      {clip("DeadlineScale", DeadlineScale)}
      {clip("StepCascade", StepCascade)}
      {clip("CompareColumns", CompareColumns)}
      {clip("ShieldPulse", ShieldPulse)}
      {clip("FolderReveal", FolderReveal)}
      {clip("PathDraw", PathDraw)}
      {clip("CheckStamp", CheckStamp)}
      {clip("WipeArc", WipeArc)}
      {clip("RingReveal", RingReveal)}
      {clip("DiagonalMask", DiagonalMask)}
      {clip("NavyBreathe", NavyBreathe)}
      {clip("SoftGrid", SoftGrid)}
      {clip("GoldDust", GoldDust)}
      {clip("ApprovalDesk", ApprovalDesk)}
      {clip("MobilityPins", MobilityPins)}
      {clip("ChoiceFork", ChoiceFork)}
    </>
  );
}
