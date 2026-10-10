import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { theme } from "../themes/tokens";
import { normalizeScene } from "../registry/validateScene";
import { renderScene } from "../registry/motionRegistry";
import type { Scene } from "../types/scene";

const file = (name: string) => staticFile(`re-test/${name}`);

const fade = { type: "fade" as const, durationInFrames: 10 };
const cut = { type: "cut" as const, durationInFrames: 0 };

const inputs = [
  {
    id: "hook",
    type: "kinetic_hook",
    variant: "word_pop",
    durationInFrames: 75,
    transition: cut,
    text: "Planning a relocation?",
    emphasis: ["relocation"],
  },
  {
    id: "host",
    type: "speaker_focus",
    variant: "circle",
    durationInFrames: 120,
    transition: fade,
    caption: "Goals and budget",
    media: { kind: "video", src: staticFile("speaker.mp4"), role: "speaker" },
  },
  {
    id: "goals",
    type: "broll_caption",
    variant: "bottom_caption",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: fade,
    text: "Goals and budget",
    media: { kind: "image", src: file("re_buyer_plan.png"), role: "image" },
  },
  {
    id: "process",
    type: "progress_steps",
    variant: "path",
    durationInFrames: 135,
    transition: cut,
    title: "Consultation to filing",
    steps: [{ label: "Planning" }, { label: "Consultation" }, { label: "Filing" }],
  },
  {
    id: "place",
    type: "broll_caption",
    variant: "cinematic",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: fade,
    text: "Clear and transparent",
    media: { kind: "video", src: file("re_ext_condo_day.mp4"), role: "broll" },
  },
  {
    id: "paperwork",
    type: "broll_caption",
    variant: "cinematic",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: cut,
    text: "Paperwork and filing",
    media: { kind: "image", src: file("re_agent_docs.png"), role: "image" },
  },
  {
    id: "immigration",
    type: "broll_caption",
    variant: "bottom_caption",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: fade,
    text: "HK Immigration",
    media: { kind: "video", src: file("location_pins_001.webm"), role: "broll" },
  },
  {
    id: "investors",
    type: "broll_caption",
    variant: "bottom_caption",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: cut,
    text: "Investors and families",
    media: { kind: "video", src: file("i2v_consult_001.mp4"), role: "broll" },
  },
  {
    id: "opportunities",
    type: "broll_caption",
    variant: "bottom_caption",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: fade,
    text: "International opportunities",
    media: { kind: "video", src: file("re_view_balcony.mp4"), role: "broll" },
  },
  {
    id: "move",
    type: "broll_caption",
    variant: "cinematic",
    captionVariant: "clean",
    durationInFrames: 120,
    transition: cut,
    text: "Ready to make your move?",
    media: { kind: "video", src: file("i2v_door_001.mp4"), role: "broll" },
  },
  {
    id: "cta",
    type: "kinetic_hook",
    variant: "scale_punch",
    durationInFrames: 90,
    transition: fade,
    text: "Contact HK Immigration",
    emphasis: ["Immigration"],
  },
];

export const REAL_ESTATE_SCENES: Scene[] = inputs.map((input) => normalizeScene(input));

export const REAL_ESTATE_DURATION = REAL_ESTATE_SCENES.reduce((sum, scene) => sum + scene.durationInFrames, 0);

export const PREVIEW_FRAMES = 450;

export function RealEstateFilm() {
  const placed: { from: number; scene: Scene }[] = [];
  let from = 0;
  for (const scene of REAL_ESTATE_SCENES) {
    placed.push({ from, scene });
    from += scene.durationInFrames;
  }
  return (
    <AbsoluteFill style={{ background: theme.color.bg, fontFamily: theme.font.sans }}>
      {placed.map(({ scene, from: start }) => (
        <Sequence key={scene.id} from={start} durationInFrames={scene.durationInFrames} name={scene.id}>
          {renderScene(scene)}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
}
