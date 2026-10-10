export const RENDERABLE_SCENE_IDS = [
  "kinetic_hook",
  "big_number",
  "progress_steps",
  "speaker_focus",
  "broll_caption",
  "timeline",
  "comparison",
  "split_screen",
  "checklist",
  "stat_reveal",
  "animated_diagram",
] as const;

export const DEFERRED_SCENE_IDS = [
  "quote",
  "process_flow",
  "image_focus",
  "final_cta",
] as const;

export const SCENE_IDS = [...RENDERABLE_SCENE_IDS, ...DEFERRED_SCENE_IDS] as const;

export const VARIANTS = {
  kinetic_hook: ["word_pop", "rapid_reveal", "scale_punch", "slide_stack"],
  big_number: ["count_up", "scale_in", "impact", "minimal"],
  progress_steps: ["horizontal", "vertical", "path", "progress_fill"],
  speaker_focus: ["fullscreen", "circle", "portrait", "side"],
  broll_caption: ["bottom_caption", "center_statement", "minimal", "cinematic"],
  timeline: ["vertical", "horizontal", "center_line", "scroll"],
  comparison: ["split", "versus", "before_after", "swipe"],
  split_screen: ["50_50", "30_70", "top_bottom", "dynamic"],
  animated_diagram: ["nodes", "flow", "growth", "risk", "steps", "comparison", "deadline"],
  checklist: ["stack", "rapid", "minimal", "progressive"],
  quote: ["editorial", "pull"],
  stat_reveal: ["impact", "counter", "comparison", "scale"],
  process_flow: ["stages", "arrows"],
  image_focus: ["full", "framed"],
  final_cta: ["statement", "prompt"],
} as const;

export const CAPTION_VARIANTS = ["clean", "word_highlight", "karaoke", "minimal", "impact"] as const;

export const MEDIA_ROLES = ["speaker", "broll", "background", "image", "screenshot"] as const;

export const TRANSITION_TYPES = ["cut", "fade", "slide", "wipe"] as const;

export const STEP_STATES = ["complete", "current", "upcoming"] as const;

export type SceneId = (typeof SCENE_IDS)[number];
export type RenderableSceneId = (typeof RENDERABLE_SCENE_IDS)[number];
export type CaptionVariant = (typeof CAPTION_VARIANTS)[number];
export type MediaRole = (typeof MEDIA_ROLES)[number];
export type TransitionType = (typeof TRANSITION_TYPES)[number];
export type StepState = (typeof STEP_STATES)[number];

export type KineticVariant = (typeof VARIANTS.kinetic_hook)[number];
export type BigNumberVariant = (typeof VARIANTS.big_number)[number];
export type ProgressVariant = (typeof VARIANTS.progress_steps)[number];
export type SpeakerVariant = (typeof VARIANTS.speaker_focus)[number];
export type BrollVariant = (typeof VARIANTS.broll_caption)[number];

export type TimedWord = {
  text: string;
  startFrame: number;
  endFrame: number;
};

export type MediaSpec =
  | { kind: "placeholder"; role: MediaRole }
  | { kind: "video" | "image" | "screenshot"; src: string; role: MediaRole };

export type SceneTransitionSpec = {
  type: TransitionType;
  durationInFrames: number;
};

export type SceneBase = {
  id: string;
  durationInFrames: number;
  transition?: SceneTransitionSpec;
};

export type ProgressStep = {
  label: string;
  state?: StepState;
};

export type KineticHookScene = SceneBase & {
  type: "kinetic_hook";
  variant: KineticVariant;
  text: string;
  emphasis?: string[];
};

export type BigNumberScene = SceneBase & {
  type: "big_number";
  variant: BigNumberVariant;
  value: number;
  label: string;
  prefix?: string;
  suffix?: string;
};

export type ProgressStepsScene = SceneBase & {
  type: "progress_steps";
  variant: ProgressVariant;
  title?: string;
  steps: ProgressStep[];
};

export type SpeakerFocusScene = SceneBase & {
  type: "speaker_focus";
  variant: SpeakerVariant;
  media: MediaSpec;
  caption?: string;
  captionVariant?: CaptionVariant;
  words?: TimedWord[];
};

export type BrollCaptionScene = SceneBase & {
  type: "broll_caption";
  variant: BrollVariant;
  text: string;
  media: MediaSpec;
  captionVariant: CaptionVariant;
  words: TimedWord[];
};

export type TimelineEvent = { label: string; date?: string };

export type TimelineScene = SceneBase & {
  type: "timeline";
  variant: (typeof VARIANTS.timeline)[number];
  events: TimelineEvent[];
};

export type ComparisonSide = { label: string; detail?: string };

export type ComparisonScene = SceneBase & {
  type: "comparison";
  variant: (typeof VARIANTS.comparison)[number];
  left: ComparisonSide;
  right: ComparisonSide;
};

export type SplitScreenScene = SceneBase & {
  type: "split_screen";
  variant: (typeof VARIANTS.split_screen)[number];
  text: string;
  media: MediaSpec;
};

export type ChecklistScene = SceneBase & {
  type: "checklist";
  variant: (typeof VARIANTS.checklist)[number];
  items: ProgressStep[];
};

export type StatRevealScene = SceneBase & {
  type: "stat_reveal";
  variant: (typeof VARIANTS.stat_reveal)[number];
  value: number;
  headline: string;
  context?: string;
};

export type DiagramNode = { label: string };

export type AnimatedDiagramScene = SceneBase & {
  type: "animated_diagram";
  variant: (typeof VARIANTS.animated_diagram)[number];
  title?: string;
  labels?: string[];
  nodes?: DiagramNode[];
  value?: number;
  leftLabel?: string;
  rightLabel?: string;
  markAt?: number;
};

export type Scene =
  | KineticHookScene
  | BigNumberScene
  | ProgressStepsScene
  | SpeakerFocusScene
  | BrollCaptionScene
  | TimelineScene
  | ComparisonScene
  | SplitScreenScene
  | ChecklistScene
  | StatRevealScene
  | AnimatedDiagramScene;
