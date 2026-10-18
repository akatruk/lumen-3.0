import { lookupScene } from "./catalog";
import { MAX_SCENE_FRAMES, framesFromSeconds, tryFramesFromSeconds } from "../utils/duration";
import { timeWords, tokenizeWords, wordKey } from "../utils/words";
import {
  CAPTION_VARIANTS,
  MEDIA_ROLES,
  SCENE_IDS,
  STEP_STATES,
  TRANSITION_TYPES,
  VARIANTS,
  type AnimatedDiagramScene,
  type BigNumberScene,
  type BrollCaptionScene,
  type BrollVariant,
  type CaptionVariant,
  type ChecklistScene,
  type ComparisonScene,
  type ComparisonSide,
  type DiagramNode,
  type KineticHookScene,
  type KineticVariant,
  type MediaRole,
  type MediaSpec,
  type ProgressStep,
  type ProgressStepsScene,
  type ProgressVariant,
  type Scene,
  type SceneTransitionSpec,
  type SpeakerFocusScene,
  type SpeakerVariant,
  type SplitScreenScene,
  type StatRevealScene,
  type StepState,
  type TimedWord,
  type TimelineEvent,
  type TimelineScene,
  type TransitionType,
} from "../types/scene";

const FIELD_KEYS = {
  kinetic_hook: ["id", "type", "variant", "text", "emphasis", "durationInFrames", "durationSeconds", "transition"],
  big_number: [
    "id",
    "type",
    "variant",
    "value",
    "label",
    "prefix",
    "suffix",
    "durationInFrames",
    "durationSeconds",
    "transition",
  ],
  progress_steps: ["id", "type", "variant", "title", "steps", "durationInFrames", "durationSeconds", "transition"],
  speaker_focus: [
    "id",
    "type",
    "variant",
    "media",
    "caption",
    "captionVariant",
    "words",
    "durationInFrames",
    "durationSeconds",
    "transition",
  ],
  broll_caption: [
    "id",
    "type",
    "variant",
    "text",
    "media",
    "captionVariant",
    "words",
    "durationInFrames",
    "durationSeconds",
    "transition",
  ],
  timeline: ["id", "type", "variant", "events", "durationInFrames", "durationSeconds", "transition"],
  comparison: ["id", "type", "variant", "left", "right", "durationInFrames", "durationSeconds", "transition"],
  split_screen: ["id", "type", "variant", "text", "media", "durationInFrames", "durationSeconds", "transition"],
  checklist: ["id", "type", "variant", "items", "durationInFrames", "durationSeconds", "transition"],
  stat_reveal: ["id", "type", "variant", "value", "headline", "context", "durationInFrames", "durationSeconds", "transition"],
  animated_diagram: [
    "id",
    "type",
    "variant",
    "title",
    "labels",
    "nodes",
    "value",
    "leftLabel",
    "rightLabel",
    "markAt",
    "durationInFrames",
    "durationSeconds",
    "transition",
  ],
} as const;

export type ValidationResult =
  | { ok: true; scene: Scene; warnings: string[] }
  | { ok: false; errors: string[]; warnings: string[] };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function unknownKeys(record: Record<string, unknown>, allowed: readonly string[], path: string, errors: string[]) {
  const permitted = new Set<string>(allowed);
  for (const key of Object.keys(record)) {
    if (!permitted.has(key)) errors.push(`${path}.${key} is not a director field`);
  }
}

function listed(list: readonly string[], value: unknown): value is string {
  return typeof value === "string" && list.includes(value);
}

function readId(record: Record<string, unknown>, type: string, variant: string, errors: string[]): string {
  if (record.id == null) return `${type}-${variant}`.replaceAll("_", "-");
  if (typeof record.id !== "string" || !/^[a-z0-9][a-z0-9-]{0,78}$/.test(record.id)) {
    errors.push("scene.id must be a short lowercase slug");
    return `${type}-${variant}`.replaceAll("_", "-");
  }
  return record.id;
}

function readDuration(record: Record<string, unknown>, fallbackSeconds: number, errors: string[]): number {
  const fallback = framesFromSeconds(fallbackSeconds);
  if (record.durationInFrames != null) {
    const frames = record.durationInFrames;
    if (typeof frames !== "number" || !Number.isFinite(frames)) {
      errors.push("durationInFrames must be a finite number");
      return fallback;
    }
    const rounded = Math.round(frames);
    if (rounded < 1 || rounded > MAX_SCENE_FRAMES) {
      errors.push(`durationInFrames must be between 1 and ${MAX_SCENE_FRAMES}`);
      return fallback;
    }
    return rounded;
  }
  if (record.durationSeconds != null) {
    if (typeof record.durationSeconds !== "number") {
      errors.push("durationSeconds must be a number");
      return fallback;
    }
    const converted = tryFramesFromSeconds(record.durationSeconds);
    if (converted == null || converted > MAX_SCENE_FRAMES) {
      errors.push(`durationSeconds must be positive and within ${MAX_SCENE_FRAMES / 30} seconds`);
      return fallback;
    }
    return converted;
  }
  return fallback;
}

function readTransition(value: unknown, duration: number, errors: string[]): SceneTransitionSpec | undefined {
  if (value == null) return undefined;
  if (!isRecord(value)) {
    errors.push("transition must be an object");
    return undefined;
  }
  unknownKeys(value, ["type", "durationInFrames"], "transition", errors);
  if (!listed(TRANSITION_TYPES, value.type)) {
    errors.push("transition.type must be cut, fade, slide, or wipe");
    return undefined;
  }
  const type = value.type as TransitionType;
  const raw = value.durationInFrames == null ? (type === "cut" ? 0 : 12) : value.durationInFrames;
  if (typeof raw !== "number" || !Number.isInteger(raw) || raw < 0 || raw > 24) {
    errors.push("transition.durationInFrames must be a whole number from 0 to 24");
    return { type, durationInFrames: Math.min(12, Math.max(0, duration - 1)) };
  }
  return { type, durationInFrames: Math.min(raw, Math.max(0, duration - 1)) };
}

function readText(
  value: unknown,
  field: string,
  errors: string[],
  warnings: string[],
  options: { required: boolean; phrase: boolean },
): string {
  if (value == null || value === "") {
    if (options.required) errors.push(`${field} is required`);
    return "";
  }
  if (typeof value !== "string") {
    errors.push(`${field} must be text`);
    return "";
  }
  if (/[\n\r\u00AD\u200B\u200C\u200D]/.test(value)) {
    errors.push(`${field} must not contain line breaks or soft hyphens`);
  }
  const text = value.trim().replace(/\s+/g, " ");
  if (text.length === 0) {
    if (options.required) errors.push(`${field} is required`);
    return "";
  }
  if (text.length > 140) errors.push(`${field} is too long`);
  if (tokenizeWords(text).some((word) => /[A-Za-z]-$/.test(word))) {
    errors.push(`${field} must not hyphenate a word`);
  }
  if (options.phrase) {
    const count = tokenizeWords(text).length;
    if (count < 3 || count > 7) {
      warnings.push(`${field} has ${count} words; captions should stay within 3–7 words`);
    }
  }
  return text;
}

function readEmphasis(value: unknown, text: string, errors: string[]): string[] | undefined {
  if (value == null) return undefined;
  if (!Array.isArray(value) || value.length > 4) {
    errors.push("emphasis must be a short list of whole words");
    return undefined;
  }
  const keys = new Set(tokenizeWords(text).map(wordKey).filter((key) => key.length > 0));
  const emphasis: string[] = [];
  for (const item of value) {
    if (typeof item !== "string" || !keys.has(wordKey(item))) {
      errors.push(`emphasis "${String(item)}" is not a whole word in the text`);
      continue;
    }
    emphasis.push(item.trim());
  }
  return emphasis.length > 0 ? emphasis : undefined;
}

function readAffix(value: unknown, field: string, errors: string[]): string | undefined {
  if (value == null || value === "") return undefined;
  if (typeof value !== "string" || value.length > 4 || /[{}<>;\s]/.test(value)) {
    errors.push(`${field} must be a short affix`);
    return undefined;
  }
  return value;
}

function readSteps(value: unknown, errors: string[]): ProgressStep[] {
  if (!Array.isArray(value) || value.length < 1 || value.length > 6) {
    errors.push("steps must be a list of 1 to 6 steps");
    return [];
  }
  return value.map((item, index) => {
    if (!isRecord(item)) {
      errors.push(`steps[${index}] must be an object with a label`);
      return { label: "" };
    }
    unknownKeys(item, ["label", "state"], `steps[${index}]`, errors);
    const label = typeof item.label === "string" ? item.label.trim().replace(/\s+/g, " ") : "";
    if (label.length === 0 || label.length > 80) errors.push(`steps[${index}].label must be a short phrase`);
    if (typeof item.label === "string" && /[\n\r\u00AD\u200B]/.test(item.label)) {
      errors.push(`steps[${index}].label must not break a word`);
    }
    let state: StepState | undefined;
    if (item.state != null) {
      if (!listed(STEP_STATES, item.state)) errors.push(`steps[${index}].state is invalid`);
      else state = item.state as StepState;
    }
    return state ? { label, state } : { label };
  });
}

function readEvents(value: unknown, errors: string[]): TimelineEvent[] {
  if (!Array.isArray(value) || value.length < 2 || value.length > 6) {
    errors.push("events must be a list of 2 to 6 events");
    return [];
  }
  return value.map((item, index) => {
    if (!isRecord(item)) {
      errors.push(`events[${index}] must be an object with a label`);
      return { label: "" };
    }
    unknownKeys(item, ["label", "date"], `events[${index}]`, errors);
    const label = typeof item.label === "string" ? item.label.trim().replace(/\s+/g, " ") : "";
    if (!label || label.length > 80) errors.push(`events[${index}].label must be a short phrase`);
    let date: string | undefined;
    if (item.date != null) {
      if (typeof item.date !== "string" || /[\n\r]/.test(item.date)) errors.push(`events[${index}].date must be a short label`);
      else date = item.date.trim().replace(/\s+/g, " ");
    }
    return date ? { label, date } : { label };
  });
}

function readSide(value: unknown, path: string, errors: string[]): ComparisonSide {
  if (!isRecord(value)) {
    errors.push(`${path} must be an object with a label`);
    return { label: "" };
  }
  unknownKeys(value, ["label", "detail"], path, errors);
  const label = typeof value.label === "string" ? value.label.trim().replace(/\s+/g, " ") : "";
  if (!label || label.length > 80) errors.push(`${path}.label must be a short phrase`);
  let detail: string | undefined;
  if (value.detail != null) {
    if (typeof value.detail !== "string" || /[\n\r]/.test(value.detail)) errors.push(`${path}.detail must be text`);
    else detail = value.detail.trim().replace(/\s+/g, " ");
  }
  return detail ? { label, detail } : { label };
}

function readMedia(value: unknown, errors: string[], fallback: MediaRole): MediaSpec {
  if (value == null) return { kind: "placeholder", role: fallback };
  if (!isRecord(value)) {
    errors.push("media must be an object");
    return { kind: "placeholder", role: fallback };
  }
  unknownKeys(value, ["kind", "role", "src"], "media", errors);
  const role = value.role == null ? fallback : value.role;
  if (!listed(MEDIA_ROLES, role)) errors.push("media.role is invalid");
  const safeRole = (listed(MEDIA_ROLES, role) ? role : fallback) as MediaRole;
  if (value.kind == null || value.kind === "placeholder") {
    if (value.src != null) errors.push("placeholder media does not take src");
    return { kind: "placeholder", role: safeRole };
  }
  if (value.kind !== "video" && value.kind !== "image" && value.kind !== "screenshot") {
    errors.push("media.kind is invalid");
    return { kind: "placeholder", role: safeRole };
  }
  if (typeof value.src !== "string" || value.src.trim() === "" || /javascript:/i.test(value.src) || /\s/.test(value.src)) {
    errors.push("media.src must be a file path or http(s) url");
    return { kind: "placeholder", role: safeRole };
  }
  return { kind: value.kind, src: value.src, role: safeRole };
}

function readCaptionVariant(value: unknown, errors: string[]): CaptionVariant {
  if (value == null) return "clean";
  if (!listed(CAPTION_VARIANTS, value)) {
    errors.push("captionVariant is invalid");
    return "clean";
  }
  return value as CaptionVariant;
}

function readWords(value: unknown, text: string, duration: number, errors: string[]): TimedWord[] {
  const fallback = timeWords(text, duration);
  if (value == null) return fallback;
  if (!Array.isArray(value)) {
    errors.push("words must be a list of timed words");
    return fallback;
  }
  const expected = tokenizeWords(text);
  const mismatch =
    value.length !== expected.length ||
    value.some((item, index) => !isRecord(item) || item.text !== expected[index]);
  if (mismatch) {
    errors.push("words must be the whole words of the phrase, in order");
    return fallback;
  }
  const words: TimedWord[] = [];
  for (let index = 0; index < value.length; index += 1) {
    const item = value[index] as Record<string, unknown>;
    unknownKeys(item, ["text", "startFrame", "endFrame"], `words[${index}]`, errors);
    const startFrame = item.startFrame;
    const endFrame = item.endFrame;
    if (
      typeof startFrame !== "number" ||
      typeof endFrame !== "number" ||
      !Number.isInteger(startFrame) ||
      !Number.isInteger(endFrame)
    ) {
      errors.push(`words[${index}] timings must be whole frames`);
      continue;
    }
    if (startFrame < 0 || endFrame > duration || endFrame <= startFrame) {
      errors.push(`words[${index}] must start before it ends, inside the scene`);
    }
    if (index > 0 && words[index - 1] && startFrame < words[index - 1].startFrame) {
      errors.push("words must be in time order");
    }
    words.push({ text: expected[index], startFrame, endFrame });
  }
  return words.length === expected.length ? words : fallback;
}

export function validateScene(input: unknown): ValidationResult {
  const warnings: string[] = [];
  const errors: string[] = [];
  if (!isRecord(input)) return { ok: false, errors: ["scene must be an object"], warnings };

  const entry = typeof input.type === "string" ? lookupScene(input.type) : undefined;
  if (!entry) {
    return {
      ok: false,
      errors: [`Unknown scene id "${String(input.type)}". Expected one of: ${SCENE_IDS.join(", ")}`],
      warnings,
    };
  }
  if (!entry.implemented) {
    return {
      ok: false,
      errors: [`${entry.id} is listed in the registry for phase ${entry.phase} and is not renderable yet`],
      warnings,
    };
  }

  const type = entry.id as keyof typeof FIELD_KEYS;
  unknownKeys(input, FIELD_KEYS[type], "scene", errors);
  if (!listed(VARIANTS[type], input.variant)) {
    errors.push(
      `variant "${String(input.variant)}" is not valid for ${type}. Expected ${VARIANTS[type].join(", ")}`,
    );
    return { ok: false, errors, warnings };
  }
  const variant = input.variant;
  const duration = readDuration(input, entry.defaultDurationSeconds, errors);
  const transition = readTransition(input.transition, duration, errors);
  const id = readId(input, type, variant, errors);
  const base = { id, durationInFrames: duration, ...(transition ? { transition } : {}) };

  let scene: Scene;
  if (type === "kinetic_hook") {
    const text = readText(input.text, "text", errors, warnings, { required: true, phrase: true });
    const emphasis = readEmphasis(input.emphasis, text, errors);
    const next: KineticHookScene = {
      ...base,
      type,
      variant: variant as KineticVariant,
      text,
      ...(emphasis ? { emphasis } : {}),
    };
    scene = next;
  } else if (type === "big_number") {
    if (typeof input.value !== "number" || !Number.isFinite(input.value)) {
      errors.push("value must be a finite number");
    }
    const label = readText(input.label, "label", errors, warnings, { required: true, phrase: true });
    const prefix = readAffix(input.prefix, "prefix", errors);
    const suffix = readAffix(input.suffix, "suffix", errors);
    const next: BigNumberScene = {
      ...base,
      type,
      variant: variant as BigNumberVariant,
      value: typeof input.value === "number" ? input.value : 0,
      label,
      ...(prefix ? { prefix } : {}),
      ...(suffix ? { suffix } : {}),
    };
    scene = next;
  } else if (type === "progress_steps") {
    const title = input.title == null ? undefined : readText(input.title, "title", errors, warnings, { required: false, phrase: true });
    const steps = readSteps(input.steps, errors);
    const next: ProgressStepsScene = {
      ...base,
      type,
      variant: variant as ProgressVariant,
      steps,
      ...(title ? { title } : {}),
    };
    scene = next;
  } else if (type === "speaker_focus") {
    const caption =
      input.caption == null
        ? undefined
        : readText(input.caption, "caption", errors, warnings, { required: false, phrase: true });
    const captionVariant = input.captionVariant == null ? undefined : readCaptionVariant(input.captionVariant, errors);
    const media = readMedia(input.media, errors, "speaker");
    const words = caption ? readWords(input.words, caption, duration, errors) : undefined;
    const next: SpeakerFocusScene = {
      ...base,
      type,
      variant: variant as SpeakerVariant,
      media,
      ...(caption ? { caption } : {}),
      ...(captionVariant ? { captionVariant } : {}),
      ...(words ? { words } : {}),
    };
    scene = next;
  } else if (type === "broll_caption") {
    const text = readText(input.text, "text", errors, warnings, { required: true, phrase: true });
    const media = readMedia(input.media, errors, "broll");
    const captionVariant = readCaptionVariant(input.captionVariant, errors);
    const words = readWords(input.words, text, duration, errors);
    const next: BrollCaptionScene = {
      ...base,
      type: "broll_caption",
      variant: variant as BrollVariant,
      text,
      media,
      captionVariant,
      words,
    };
    scene = next;
  } else if (type === "timeline") {
    const next: TimelineScene = { ...base, type, variant: variant as TimelineScene["variant"], events: readEvents(input.events, errors) };
    scene = next;
  } else if (type === "comparison") {
    const next: ComparisonScene = {
      ...base,
      type,
      variant: variant as ComparisonScene["variant"],
      left: readSide(input.left, "left", errors),
      right: readSide(input.right, "right", errors),
    };
    scene = next;
  } else if (type === "split_screen") {
    const text = readText(input.text, "text", errors, warnings, { required: true, phrase: true });
    const next: SplitScreenScene = {
      ...base,
      type,
      variant: variant as SplitScreenScene["variant"],
      text,
      media: readMedia(input.media, errors, "speaker"),
    };
    scene = next;
  } else if (type === "checklist") {
    const next: ChecklistScene = { ...base, type, variant: variant as ChecklistScene["variant"], items: readSteps(input.items, errors) };
    scene = next;
  } else if (type === "animated_diagram") {
    const title =
      input.title == null ? undefined : readText(input.title, "title", errors, warnings, { required: false, phrase: true });
    const leftLabel =
      input.leftLabel == null
        ? undefined
        : readText(input.leftLabel, "leftLabel", errors, warnings, { required: false, phrase: true });
    const rightLabel =
      input.rightLabel == null
        ? undefined
        : readText(input.rightLabel, "rightLabel", errors, warnings, { required: false, phrase: true });
    let labels: string[] | undefined;
    if (input.labels != null) {
      if (!Array.isArray(input.labels)) {
        errors.push("labels must be a list of phrases");
      } else {
        labels = input.labels.map((item, index) =>
          readText(item, `labels[${index}]`, errors, warnings, { required: true, phrase: true }),
        );
      }
    }
    let nodes: DiagramNode[] | undefined;
    if (input.nodes != null) {
      if (!Array.isArray(input.nodes)) {
        errors.push("nodes must be a list");
      } else {
        nodes = input.nodes.map((item, index) => {
          if (!isRecord(item)) {
            errors.push(`nodes[${index}] must be an object`);
            return { label: "" };
          }
          unknownKeys(item, ["label"], `nodes[${index}]`, errors);
          return {
            label: readText(item.label, `nodes[${index}].label`, errors, warnings, { required: true, phrase: true }),
          };
        });
      }
    }
    if (input.value != null && (typeof input.value !== "number" || !Number.isFinite(input.value))) {
      errors.push("value must be a finite number");
    }
    if (input.markAt != null && (typeof input.markAt !== "number" || input.markAt < 0 || input.markAt > 1)) {
      errors.push("markAt must be between 0 and 1");
    }
    const next: AnimatedDiagramScene = {
      ...base,
      type: "animated_diagram",
      variant: variant as AnimatedDiagramScene["variant"],
      ...(title ? { title } : {}),
      ...(labels ? { labels } : {}),
      ...(nodes ? { nodes } : {}),
      ...(typeof input.value === "number" ? { value: input.value } : {}),
      ...(leftLabel ? { leftLabel } : {}),
      ...(rightLabel ? { rightLabel } : {}),
      ...(typeof input.markAt === "number" ? { markAt: input.markAt } : {}),
    };
    scene = next;
  } else {
    if (typeof input.value !== "number" || !Number.isFinite(input.value)) errors.push("value must be a finite number");
    const headline = readText(input.headline, "headline", errors, warnings, { required: true, phrase: true });
    const context = input.context == null ? undefined : readText(input.context, "context", errors, warnings, { required: false, phrase: true });
    const next: StatRevealScene = {
      ...base,
      type: "stat_reveal",
      variant: variant as StatRevealScene["variant"],
      value: typeof input.value === "number" ? input.value : 0,
      headline,
      ...(context ? { context } : {}),
    };
    scene = next;
  }

  if (errors.length > 0 || !scene) return { ok: false, errors, warnings };
  return { ok: true, scene, warnings };
}

type BigNumberVariant = BigNumberScene["variant"];

export function normalizeScene(input: unknown): Scene {
  const result = validateScene(input);
  if (!result.ok) throw new Error(result.errors.join("; "));
  return result.scene;
}
