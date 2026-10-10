import { normalizeScene } from "../registry/validateScene";
import type { Scene } from "../types/scene";
import { sumDurationFrames } from "../utils/duration";

const BEAT = 90;
const LOCAL = 72;

const speaker = { kind: "placeholder" as const, role: "speaker" as const };
const footage = { kind: "placeholder" as const, role: "broll" as const };
const image = { kind: "placeholder" as const, role: "image" as const };
const screen = { kind: "placeholder" as const, role: "screenshot" as const };
const background = { kind: "placeholder" as const, role: "background" as const };

const steps = [
  { label: "Consultation" },
  { label: "Document preparation" },
  { label: "Filing" },
];

const cycle = ["fade", "slide", "wipe", "cut"] as const;

function beat(index: number) {
  const type = cycle[index % cycle.length];
  return {
    durationInFrames: BEAT,
    transition: { type, durationInFrames: type === "cut" ? 0 : 12 },
  };
}

export const showcaseInputs: unknown[] = [
  { id: "hook-word-pop", type: "kinetic_hook", variant: "word_pop", text: "Planning a relocation?", emphasis: ["relocation"], ...beat(0) },
  { id: "hook-rapid-reveal", type: "kinetic_hook", variant: "rapid_reveal", text: "Consultation to filing", ...beat(1) },
  { id: "hook-scale-punch", type: "kinetic_hook", variant: "scale_punch", text: "Goal, family, and budget", emphasis: ["family"], ...beat(2) },
  { id: "hook-slide-stack", type: "kinetic_hook", variant: "slide_stack", text: "International relocation consultation", ...beat(3) },
  { id: "number-count-up", type: "big_number", variant: "count_up", value: 3, label: "steps to get started", ...beat(4) },
  { id: "number-scale-in", type: "big_number", variant: "scale_in", value: 3, label: "steps to get started", ...beat(5) },
  { id: "number-impact", type: "big_number", variant: "impact", value: 3, label: "steps to get started", ...beat(6) },
  { id: "number-minimal", type: "big_number", variant: "minimal", value: 3, label: "steps to get started", ...beat(7) },
  { id: "steps-horizontal", type: "progress_steps", variant: "horizontal", title: "3 steps to get started", steps, ...beat(8) },
  { id: "steps-vertical", type: "progress_steps", variant: "vertical", title: "Set your goals and budget", steps, ...beat(9) },
  { id: "steps-path", type: "progress_steps", variant: "path", title: "Consultation to filing", steps, ...beat(10) },
  { id: "steps-fill", type: "progress_steps", variant: "progress_fill", title: "Ready to make your move?", steps, ...beat(11) },
  { id: "speaker-fullscreen", type: "speaker_focus", variant: "fullscreen", media: speaker, caption: "Planning a relocation?", ...beat(12) },
  { id: "speaker-circle", type: "speaker_focus", variant: "circle", media: speaker, caption: "Set your goals and budget", ...beat(13) },
  { id: "speaker-portrait", type: "speaker_focus", variant: "portrait", media: speaker, caption: "Consultation to filing", ...beat(14) },
  { id: "speaker-side", type: "speaker_focus", variant: "side", media: speaker, caption: "Ready to make your move?", ...beat(15) },
  {
    id: "caption-bottom-clean",
    type: "broll_caption",
    variant: "bottom_caption",
    captionVariant: "clean",
    text: "Planning a relocation?",
    media: footage,
    ...beat(16),
  },
  {
    id: "caption-center-highlight",
    type: "broll_caption",
    variant: "center_statement",
    captionVariant: "word_highlight",
    text: "Ready to make your move?",
    media: image,
    ...beat(17),
  },
  {
    id: "caption-minimal",
    type: "broll_caption",
    variant: "minimal",
    captionVariant: "minimal",
    text: "Consultation to filing",
    media: screen,
    ...beat(18),
  },
  {
    id: "caption-cinematic-impact",
    type: "broll_caption",
    variant: "cinematic",
    captionVariant: "impact",
    text: "Goal, family, and budget",
    media: background,
    ...beat(19),
  },
  {
    id: "caption-karaoke",
    type: "broll_caption",
    variant: "bottom_caption",
    captionVariant: "karaoke",
    text: "Set your goals and budget",
    media: footage,
    ...beat(20),
  },
  {
    id: "timeline-vertical",
    type: "timeline",
    variant: "vertical",
    events: [
      { date: "Start", label: "Consultation" },
      { label: "Document preparation" },
      { label: "Filing" },
    ],
    ...beat(21),
  },
  {
    id: "timeline-horizontal",
    type: "timeline",
    variant: "horizontal",
    events: [
      { label: "Consultation" },
      { label: "Document preparation" },
      { label: "Filing" },
    ],
    ...beat(22),
  },
  {
    id: "timeline-center",
    type: "timeline",
    variant: "center_line",
    events: [
      { label: "Consultation" },
      { label: "Document preparation" },
      { label: "Filing" },
    ],
    ...beat(23),
  },
  {
    id: "timeline-scroll",
    type: "timeline",
    variant: "scroll",
    events: [
      { label: "Consultation" },
      { label: "Document preparation" },
      { label: "Filing" },
    ],
    ...beat(24),
  },
  {
    id: "comparison-split",
    type: "comparison",
    variant: "split",
    left: { label: "Consultation", detail: "Set your goals and budget" },
    right: { label: "Filing", detail: "Ready to make your move?" },
    ...beat(25),
  },
  {
    id: "comparison-versus",
    type: "comparison",
    variant: "versus",
    left: { label: "Before" },
    right: { label: "After" },
    ...beat(26),
  },
  {
    id: "comparison-before",
    type: "comparison",
    variant: "before_after",
    left: { label: "Consultation" },
    right: { label: "Filing" },
    ...beat(27),
  },
  {
    id: "comparison-swipe",
    type: "comparison",
    variant: "swipe",
    left: { label: "Planning a relocation?" },
    right: { label: "Ready to make your move?" },
    ...beat(28),
  },
  { id: "split-half", type: "split_screen", variant: "50_50", text: "Planning a relocation?", media: speaker, ...beat(29) },
  { id: "split-narrow", type: "split_screen", variant: "30_70", text: "Set your goals and budget", media: footage, ...beat(30) },
  { id: "split-flip", type: "split_screen", variant: "top_bottom", text: "Consultation to filing", media: speaker, ...beat(31) },
  { id: "split-dynamic", type: "split_screen", variant: "dynamic", text: "Ready to make your move?", media: footage, ...beat(32) },
  {
    id: "check-stack",
    type: "checklist",
    variant: "stack",
    items: [{ label: "Consultation" }, { label: "Document preparation" }, { label: "Filing" }],
    ...beat(33),
  },
  {
    id: "check-rapid",
    type: "checklist",
    variant: "rapid",
    items: [{ label: "Consultation" }, { label: "Document preparation" }, { label: "Filing" }],
    ...beat(34),
  },
  {
    id: "check-minimal",
    type: "checklist",
    variant: "minimal",
    items: [{ label: "Consultation" }, { label: "Filing" }],
    ...beat(35),
  },
  {
    id: "check-progress",
    type: "checklist",
    variant: "progressive",
    items: [{ label: "Consultation" }, { label: "Document preparation" }, { label: "Filing" }],
    ...beat(36),
  },
  { id: "stat-impact", type: "stat_reveal", variant: "impact", value: 3, headline: "steps to get started", ...beat(37) },
  { id: "stat-counter", type: "stat_reveal", variant: "counter", value: 3, headline: "steps to get started", ...beat(38) },
  {
    id: "stat-comparison",
    type: "stat_reveal",
    variant: "comparison",
    value: 3,
    headline: "steps to get started",
    context: "Consultation to filing",
    ...beat(39),
  },
  { id: "stat-scale", type: "stat_reveal", variant: "scale", value: 3, headline: "steps to get started", ...beat(40) },
  {
    id: "diagram-nodes",
    type: "animated_diagram",
    variant: "nodes",
    title: "Goal, family, and budget",
    labels: ["Consultation", "Document preparation", "Filing"],
    ...beat(41),
  },
  {
    id: "diagram-flow",
    type: "animated_diagram",
    variant: "flow",
    title: "Planning a relocation?",
    ...beat(42),
  },
  {
    id: "diagram-growth",
    type: "animated_diagram",
    variant: "growth",
    title: "Ready to make your move?",
    ...beat(43),
  },
  {
    id: "diagram-risk",
    type: "animated_diagram",
    variant: "risk",
    title: "Set your goals and budget",
    ...beat(44),
  },
  {
    id: "diagram-steps",
    type: "animated_diagram",
    variant: "steps",
    title: "Consultation to filing",
    labels: ["Consultation", "Document preparation", "Filing"],
    ...beat(45),
  },
  {
    id: "diagram-comparison",
    type: "animated_diagram",
    variant: "comparison",
    title: "Planning a relocation?",
    leftLabel: "Consultation",
    rightLabel: "Filing",
    ...beat(46),
  },
  {
    id: "diagram-deadline",
    type: "animated_diagram",
    variant: "deadline",
    title: "steps to get started",
    markAt: 0.7,
    ...beat(47),
  },
];

export const SHOWCASE_SCENES: Scene[] = showcaseInputs.map((input) => normalizeScene(input));

export const SHOWCASE_DURATION = sumDurationFrames(SHOWCASE_SCENES.map((scene) => scene.durationInFrames));

export function frameForScene(id: string, localFrame: number): number {
  let cursor = 0;
  for (const scene of SHOWCASE_SCENES) {
    if (scene.id === id) {
      if (localFrame < 0 || localFrame >= scene.durationInFrames) {
        throw new Error(`local frame ${localFrame} is outside ${id}`);
      }
      return cursor + localFrame;
    }
    cursor += scene.durationInFrames;
  }
  throw new Error(`Unknown showcase scene ${id}`);
}

export function sampleFrames() {
  return {
    kineticHook: { id: "hook-word-pop", frame: frameForScene("hook-word-pop", LOCAL), file: "kinetic-hook.png" },
    bigNumber: { id: "number-count-up", frame: frameForScene("number-count-up", LOCAL), file: "big-number.png" },
    caption: { id: "caption-bottom-clean", frame: frameForScene("caption-bottom-clean", LOCAL), file: "caption.png" },
    steps: { id: "steps-horizontal", frame: frameForScene("steps-horizontal", LOCAL), file: "progress-steps.png" },
  };
}
