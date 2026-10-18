import { useEffect, useRef, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { Lang, Project } from "./types";
import { ProjectJobStatus } from "./ProjectJobStatus";
import { workspaceText } from "./ProjectWorkspace";
import { chosenDuration } from "./durationChoice";

type Speech = "ru-RU" | "en-US" | "zh-CN";

type StudioState = {
  plan?: {
    transcript?: { original?: string; zh?: string; en?: string; ru?: string }[];
  } | null;
  context?: {
    video_language?: string;
    reference_file?: boolean;
    references?: { aweme_id?: string; title?: string; author?: string }[];
    visual_energy?: string;
    visual_variation?: string;
    semantic_motion_profile?: string | null;
    editing_controls?: {
      animation?: number;
      intensity?: number;
      motion?: number;
      density?: number;
      visualEnergy?: string;
      preset?: string;
      durationMode?: "full" | "custom";
      durationSeconds?: number;
    };
  };
};

type Energy = "calm" | "balanced" | "dynamic" | "custom";

const ENERGY_PRESETS: Record<"calm" | "balanced" | "dynamic", { animation: number; intensity: number; motion: number; density: number }> = {
  calm: { animation: 40, intensity: 40, motion: 40, density: 40 },
  balanced: { animation: 60, intensity: 60, motion: 80, density: 70 },
  dynamic: { animation: 85, intensity: 85, motion: 90, density: 85 },
};

function matchPreset(levels: { animation: number; intensity: number; motion: number; density: number }): Energy {
  for (const id of ["calm", "balanced", "dynamic"] as const) {
    const preset = ENERGY_PRESETS[id];
    if (
      levels.animation === preset.animation &&
      levels.intensity === preset.intensity &&
      levels.motion === preset.motion &&
      levels.density === preset.density
    ) {
      return id;
    }
  }
  return "custom";
}

function effectLine(
  key: Share["key"],
  value: number,
  w: (ru: string, en: string, zh: string) => string,
) {
  if (key === "animation") {
    return w(
      `~${value}% сцен с осмысленной анимацией графики. Не добавляет лишние картинки.`,
      `~${value}% of scenes get purposeful graphics motion. Does not invent extra plates.`,
      `约 ${value}% 的场景有有意义的图形动画。不会硬塞无关画面。`,
    );
  }
  if (key === "intensity") {
    return w(
      `Сила акцентов и переходов: ${value}%. Не меняет скорость речи.`,
      `Accent and transition strength: ${value}%. Does not change speech rate.`,
      `强调与转场强度：${value}%。不改变语速。`,
    );
  }
  if (key === "motion") {
    return w(
      `Скорость/амплитуда камеры и элементов: ${value}%. Не скорость речи.`,
      `Camera/element speed and amplitude: ${value}%. Not speech rate.`,
      `镜头与元素运动幅度：${value}%。不是语速。`,
    );
  }
  return w(
    `Сколько доп. информации на экране сразу: ${value}%. Приоритет — смысл речи и лицо.`,
    `How much extra info at once: ${value}%. Speech meaning and face stay first.`,
    `同时显示的额外信息量：${value}%。语音含义与面部优先。`,
  );
}

const VOICE_CHOICES: Record<Speech, { id: string; label: string }[]> = {
  "en-US": [
    { id: "en-male", label: "Male — gentle" },
    { id: "en-female", label: "Female — warm" },
  ],
  "ru-RU": [
    { id: "ru-male", label: "Мужской — спокойный" },
    { id: "ru-female", label: "Женский — выразительный" },
  ],
  "zh-CN": [
    { id: "zh-male", label: "男声 — 温和" },
    { id: "zh-female", label: "女声 — 亲切" },
  ],
};

const LANGUAGES: { id: Speech; label: string; voice: string }[] = [
  { id: "ru-RU", label: "Русский", voice: "Мужской — спокойный" },
  { id: "en-US", label: "English", voice: "Male — gentle" },
  { id: "zh-CN", label: "中文", voice: "男声 — 温和" },
];

function detectSpeech(text: string): Speech | null {
  if (/[\u4e00-\u9fff]/.test(text)) return "zh-CN";
  if (/[\u0400-\u04FF]/.test(text)) return "ru-RU";
  if (/[A-Za-z]/.test(text)) return "en-US";
  return null;
}

function spokenLanguage(data: StudioState | null): Speech {
  const lines = data?.plan?.transcript ?? [];
  const original = lines.map((line) => line.original || "").join(" ");
  const rest = lines.map((line) => line.en || line.ru || line.zh || "").join(" ");
  return detectSpeech(original) || detectSpeech(rest) || "en-US";
}

function savedLanguage(value: unknown): Speech | null {
  if (value === "ru" || value === "ru-RU") return "ru-RU";
  if (value === "en" || value === "en-US") return "en-US";
  if (value === "zh" || value === "zh-CN") return "zh-CN";
  return null;
}

type Share = {
  key: "animation" | "intensity" | "motion" | "density";
  label: [string, string, string];
  min: number;
};

type RenditionSnap = {
  locale?: string;
  status?: string;
  voiceName?: string | null;
  audioMode?: string | null;
};

function boardMap(board: unknown): Record<string, RenditionSnap> {
  const out: Record<string, RenditionSnap> = {};
  if (!Array.isArray(board)) return out;
  for (const item of board) {
    if (!item || typeof item !== "object") continue;
    const row = item as RenditionSnap;
    if (row.locale) out[row.locale] = row;
  }
  return out;
}

function apiDetail(body: unknown): string {
  if (!body || typeof body !== "object") return "";
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
    return String((detail[0] as { msg?: string }).msg || "");
  }
  return "";
}

function createErrorKind(detail: string): "voice" | "voice_not_ready" | "busy" | "provider" | "failed" {
  if (detail === "MISSING_TARGET_LANGUAGE_VOICE" || detail === "VOICE_SETUP_REQUIRED") return "voice";
  if (detail === "target_voice_not_ready") return "voice_not_ready";
  if (detail === "job_already_running" || detail === "project_busy") return "busy";
  if (detail === "provider_not_configured" || detail === "VOICE_PROVIDER_NOT_CONFIGURED") return "provider";
  return "failed";
}

const SHARES: Share[] = [
  { key: "animation", label: ["Анимация, %", "Animation, %", "动画，%"], min: 0 },
  { key: "intensity", label: ["Интенсивность, %", "Intensity, %", "强度，%"], min: 5 },
  { key: "motion", label: ["Движение, %", "Motion, %", "运动，%"], min: 0 },
  { key: "density", label: ["Плотность, %", "Density, %", "密度，%"], min: 0 },
];

function durationLimit(sourceSeconds: number) {
  const max = Math.max(10, sourceSeconds);
  return { min: 10, max, step: 5 };
}

export function CreateVideo({
  pid,
  lang,
  project,
  working,
  sourceSeconds,
  onStarted,
}: {
  pid: string;
  lang: Lang;
  project?: Project | null;
  working: boolean;
  sourceSeconds: number;
  onStarted: () => Promise<void>;
}) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  const limit = durationLimit(sourceSeconds);
  const [durationMode, setDurationMode] = useState<"full" | "custom">("full");
  const [customLength, setCustomLength] = useState(limit.max >= 20 ? 20 : limit.max);
  const length = durationMode === "full" && sourceSeconds > 0 ? sourceSeconds : customLength;
  const [variation, setVariation] = useState<"automatic" | "keep" | "remix">("automatic");
  const [energy, setEnergy] = useState<Energy>("balanced");
  const [levels, setLevels] = useState({ animation: 60, intensity: 60, motion: 80, density: 70 });
  const [hydrated, setHydrated] = useState(false);
  const [language, setLanguage] = useState<Speech | null>(null);
  const [debug, setDebug] = useState("");
  const [uploads, setUploads] = useState<StudioState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errorDetail, setErrorDetail] = useState("");
  const [voiceChoice, setVoiceChoice] = useState<string | null>(null);
  const [motionProfile, setMotionProfile] = useState(false);
  const [renditions, setRenditions] = useState<Record<string, RenditionSnap>>({});
  const notice = useRef<HTMLParagraphElement>(null);
  const persistTimer = useRef<number | null>(null);
  const durationRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const node = durationRef.current;
    if (!node) return;
    const onWheel = (event: WheelEvent) => {
      if (document.activeElement !== node && !node.matches(":hover")) return;
      event.preventDefault();
      const direction = event.deltaY > 0 ? -limit.step : limit.step;
      const base = durationMode === "full" && sourceSeconds > 0 ? sourceSeconds : customLength;
      const next = chosenDuration(Math.min(limit.max, Math.max(limit.min, base + direction)), sourceSeconds);
      setDurationMode("custom");
      setCustomLength(next);
      if (hydrated) persistEditing(levels, energy, variation, "custom", next);
    };
    node.addEventListener("wheel", onWheel, { passive: false });
    return () => node.removeEventListener("wheel", onWheel);
  });
  useEffect(() => {
    let cancelled = false;
    fetch("/api/studio/projects/" + pid, { credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (cancelled) return;
        setUploads(data);
        const saved = data?.context?.editing_controls;
        if (saved && typeof saved === "object") {
          const next = {
            animation: Number(saved.animation ?? 60),
            intensity: Number(saved.intensity ?? 60),
            motion: Number(saved.motion ?? 80),
            density: Number(saved.density ?? 70),
          };
          setLevels(next);
          if (saved.durationMode === "full" || saved.durationMode === "custom") {
            setDurationMode(saved.durationMode);
          }
          if (typeof saved.durationSeconds === "number" && saved.durationSeconds > 0) {
            setCustomLength(saved.durationSeconds);
          }
          const fromSaved = (saved.visualEnergy || data?.context?.visual_energy || matchPreset(next)) as Energy;
          setEnergy(fromSaved === "custom" ? "custom" : matchPreset(next) === fromSaved ? fromSaved : matchPreset(next));
        }
        if (data?.context?.visual_variation && ["automatic", "keep", "remix"].includes(data.context.visual_variation)) {
          setVariation(data.context.visual_variation);
        }
        setMotionProfile(data?.context?.semantic_motion_profile === "evidence_gated_v1");
        setHydrated(true);
      })
      .catch(() => {
        if (!cancelled) {
          setUploads(null);
          setHydrated(true);
        }
      });
    fetch("/api/studio/projects/" + pid + "/rendition", { credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled && data?.renditions) setRenditions(boardMap(data.renditions));
      })
      .catch(() => {
        if (!cancelled) setRenditions({});
      });
    return () => {
      cancelled = true;
    };
  }, [pid]);
  function persistEditing(
    nextLevels: typeof levels,
    nextEnergy: Energy,
    nextVariation = variation,
    nextMode = durationMode,
    nextLength = length,
    nextProfile = motionProfile,
  ) {
    // Debounced save only — never enqueue render / TTS / GPU.
    if (persistTimer.current) window.clearTimeout(persistTimer.current);
    persistTimer.current = window.setTimeout(() => {
      void fetch("/api/studio/projects/" + pid + "/editing-controls", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          animation_percent: nextLevels.animation,
          intensity_percent: nextLevels.intensity,
          motion_percent: nextLevels.motion,
          density_percent: nextLevels.density,
          visual_energy: nextEnergy,
          visual_variation: nextVariation,
          semantic_motion_profile: nextProfile ? "evidence_gated_v1" : null,
          duration_mode: nextMode,
          duration_seconds: nextLength,
        }),
      }).catch(() => undefined);
    }, 400);
  }
  function chooseEnergy(next: "calm" | "balanced" | "dynamic") {
    const preset = ENERGY_PRESETS[next];
    setEnergy(next);
    setLevels(preset);
    if (hydrated) persistEditing(preset, next);
  }
  function changeLevel(key: Share["key"], value: number) {
    setLevels((current) => {
      const next = { ...current, [key]: value };
      const matched = matchPreset(next);
      setEnergy(matched);
      if (hydrated) persistEditing(next, matched);
      return next;
    });
  }
  const references = uploads?.context?.references ?? [];
  const videos = [
    w("Ваше видео", "Your video", "你的视频"),
    ...(uploads?.context?.reference_file ? [w("Референс", "Reference video", "参考视频")] : []),
    ...references.map((item) => item.title || item.author || item.aweme_id || w("Референс", "Reference video", "参考视频")),
  ];
  const speech = language ?? savedLanguage(uploads?.context?.video_language) ?? savedLanguage(project?.language) ?? spokenLanguage(uploads);
  const speechLabel = LANGUAGES.find((item) => item.id === speech)?.label ?? speech;
  const sourceSpeech =
    detectSpeech((uploads?.plan?.transcript ?? []).map((line) => line.original || "").join(" "))
    || savedLanguage(project?.metadata?.source_language);
  const originalVoice = !sourceSpeech || sourceSpeech === speech;
  const voiceLabel = originalVoice
    ? w("Оригинальный голос ведущего", "Original speaker audio", "原声")
    : (LANGUAGES.find((item) => item.id === speech)?.voice ?? speech);
  const rendition = renditions[speech] || {};
  const voiceStatus = originalVoice
    ? "ready"
    : ["audio_ready", "aligned", "ready", "rendered"].includes(String(rendition.status || ""))
      ? "ready"
      : rendition.status === "script_ready"
        ? "script_ready"
        : String(rendition.status || "missing");
  useEffect(() => {
    notice.current?.scrollIntoView({ block: "nearest" });
  }, [error, speech]);
  async function choose(next: Speech) {
    setLanguage(next);
    setError("");
    setErrorDetail("");
    try {
      const response = await fetch("/api/studio/projects/" + pid + "/language", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: next }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = apiDetail(body);
        setErrorDetail(detail);
        setError(createErrorKind(detail));
      }
      const board = await fetch("/api/studio/projects/" + pid + "/rendition", { credentials: "same-origin" });
      if (board.ok) {
        const data = await board.json();
        if (data?.renditions) setRenditions(boardMap(data.renditions));
      }
    } catch {
      setError("failed");
    }
  }
  async function showDebug() {
    const params = new URLSearchParams({
      animation_percent: String(levels.animation),
      intensity_percent: String(levels.intensity),
      motion_percent: String(levels.motion),
      density_percent: String(levels.density),
      language: speech,
    });
    const response = await fetch("/api/studio/picture-prompt?" + params.toString(), { credentials: "same-origin" });
    if (!response.ok) {
      setDebug("");
      return;
    }
    const body = await response.json();
    setDebug(
      [
        "project.language: " + (body.language || speech),
        "typography: " + (body.typographyProfile || ""),
        "voice locale: " + (body.voiceLocale || ""),
        "directive locale: " + (String(body.directive || "").includes(speech) ? speech : "missing"),
        "prompt locale: " + (String(body.prompt || "").includes(speech) ? speech : "missing"),
      ].join("\n"),
    );
  }
  async function preview() {
    setError("");
    setErrorDetail("");
    try {
      const response = await fetch("/api/studio/projects/" + pid + "/voice-preview", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: speech }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = apiDetail(body);
        setErrorDetail(detail);
        setError(createErrorKind(detail));
        return;
      }
      setDebug([body?.voiceName || "", body?.text || ""].filter(Boolean).join("\n"));
      const board = await fetch("/api/studio/projects/" + pid + "/rendition", { credentials: "same-origin" });
      if (board.ok) {
        const data = await board.json();
        if (data?.renditions) setRenditions(boardMap(data.renditions));
      }
    } catch {
      setError("failed");
    }
  }
  async function create() {
    if (working || busy) return;
    setBusy(true);
    setError("");
    setErrorDetail("");
    try {
      const response = await fetch("/api/studio/projects/" + pid + "/create-video", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          animation_percent: levels.animation,
          intensity_percent: levels.intensity,
          motion_percent: levels.motion,
          density_percent: levels.density,
          duration_seconds: length,
          visual_variation: variation,
          visual_energy: energy === "custom" ? "balanced" : energy,
          language: speech,
          voice: voiceChoice,
          semantic_motion_profile: motionProfile ? "evidence_gated_v1" : null,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = apiDetail(body);
        setErrorDetail(detail);
        setError(createErrorKind(detail));
        notice.current?.scrollIntoView({ block: "nearest" });
        return;
      }
      await onStarted();
    } catch {
      setError("failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="create-video" aria-label={w("Создать видео", "Create video", "创建视频")}>
      {project ? <ProjectJobStatus p={project} lang={lang} /> : null}
      <div>
        <span className="eyebrow">{w("ЗАГРУЖЕННЫЕ ВИДЕО", "UPLOADED VIDEOS", "已上传视频")}</span>
        <ul>
          {videos.map((name, index) => (
            <li key={index}>{name}</li>
          ))}
        </ul>
      </div>
      <label>
        {w("Длительность, с", "Duration, s", "时长，秒")}
        <input
          ref={durationRef}
          type="range"
          min={limit.min}
          max={limit.max}
          step={limit.step}
          value={Math.min(durationMode === "full" && sourceSeconds > 0 ? sourceSeconds : customLength, limit.max)}
          aria-valuetext={length + "s"}
          onChange={(event) => {
            const next = chosenDuration(Number(event.target.value), sourceSeconds);
            setDurationMode("custom");
            setCustomLength(next);
            if (hydrated) persistEditing(levels, energy, variation, "custom", next);
          }}
        />
      </label>
      <button
        type="button"
        className="secondary"
        aria-pressed={durationMode === "full"}
        onClick={() => {
          const next = durationMode === "full" ? "custom" : "full";
          setDurationMode(next);
          const seconds = next === "full" && sourceSeconds > 0 ? sourceSeconds : customLength;
          if (hydrated) persistEditing(levels, energy, variation, next, seconds);
        }}
      >
        {w("Весь исходник", "Use full source", "使用完整原片")}
      </button>
      <strong>
        {durationMode === "full"
          ? w("Весь исходник", "Full source", "完整原片")
          : w("Выбранная длина", "Selected length", "选定时长")}
        {" · "}
        {length}
        {w(" с", "s", " 秒")}
      </strong>
      <div className="language-switch" role="radiogroup" aria-label={w("Вариация картинки", "Visual variation", "画面变化")}>
        {(
          [
            ["automatic", w("Авто", "Automatic", "自动")],
            ["keep", w("Тот же стиль", "Keep style", "保持风格")],
            ["remix", w("Новая", "New variation", "新变化")],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={variation === id} onClick={() => setVariation(id)}>
            {label}
          </button>
        ))}
      </div>
      <div className="language-switch" role="radiogroup" aria-label={w("Энергия картинки", "Visual energy", "画面能量")}>
        {(
          [
            ["calm", w("Спокойно", "Calm", "平静")],
            ["balanced", w("Баланс", "Balanced", "平衡")],
            ["dynamic", w("Динамика", "Dynamic", "动感")],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="radio"
            aria-checked={energy === id}
            onClick={() => chooseEnergy(id)}
          >
            {label}
          </button>
        ))}
        {energy === "custom" && (
          <button type="button" role="radio" aria-checked disabled>
            {w("Свой", "Custom", "自定义")}
          </button>
        )}
      </div>
      <p className="hint">
        {w(
          "Ползунки сохраняются сразу. Новый монтаж — только после «Создать видео» (не постобработка готового MP4).",
          "Sliders save immediately. A new montage only after Create video (not a post-process of the finished MP4).",
          "滑块会立即保存。新的剪辑只在「创建视频」后生效（不会后处理成品 MP4）。",
        )}
      </p>
      {SHARES.map((share) => (
        <label key={share.key}>
          {w(...share.label)}
          <input
            type="range"
            min={share.min}
            max={100}
            step={5}
            value={levels[share.key]}
            aria-valuetext={levels[share.key] + "%"}
            onChange={(event) => changeLevel(share.key, Number(event.target.value))}
          />
          <strong>{levels[share.key]}%</strong>
          <span className="slider-effect">{effectLine(share.key, levels[share.key], w)}</span>
        </label>
      ))}
      <label>
        <input
          type="checkbox"
          checked={motionProfile}
          disabled={working || busy}
          onChange={(event) => {
            const next = event.target.checked;
            setMotionProfile(next);
            if (hydrated) persistEditing(levels, energy, variation, durationMode, length, next);
          }}
        />{" "}
        {w(
          "Визуальный интеллект: графика по речи (эксперимент)",
          "Visual intelligence: evidence-gated motion (experimental)",
          "视觉智能：按讲话证据出图（实验）",
        )}
      </label>
      <div className="create-actions">
        <div
          className="language-switch"
          role="radiogroup"
          aria-label={w("Язык видео", "Video language", "视频语言")}
        >
          {LANGUAGES.map((item) => (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={speech === item.id}
              disabled={working || busy}
              onClick={() => void choose(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p>
          {working || busy
            ? w("Собираем видео:", "Generating video in:", "正在生成视频：")
            : w("Язык видео:", "Video language:", "视频语言：")}{" "}
          {speechLabel}
        </p>
        <p>
          {w("Голос:", "Voice:", "声音：")} {voiceLabel}
        </p>
        {sourceSpeech && sourceSpeech !== speech && (
          <p>
            {speech === "en-US" && w("Английская озвучка", "Dubbed English", "英语配音")}
            {speech === "ru-RU" && w("Русская озвучка", "Dubbed Russian", "俄语配音")}
            {speech === "zh-CN" && w("Китайская озвучка", "Dubbed Chinese", "中文配音")}
            {" · "}
            {voiceStatus === "ready"
              ? w("озвучка готова", "voice ready", "配音已就绪")
              : voiceStatus === "script_ready"
                ? w(
                    "есть перевод — Create video соберёт озвучку",
                    "script ready — Create video will build the voice",
                    "文案已就绪 — 创建视频时会生成配音",
                  )
                : w(
                    "озвучка соберётся при Create video",
                    "voice builds on Create video",
                    "创建视频时生成配音",
                  )}
          </p>
        )}
        <button type="button" disabled={working || busy} onClick={() => void preview()}>
          {w("Прослушать голос", "Preview voice", "试听声音")}
        </button>
        <button className="primary" type="button" disabled={working || busy} onClick={() => void create()}>
          {working || busy ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
          {w("Создать видео", "Create video", "创建视频")}
        </button>
        {(error === "voice" ||
          error === "voice_not_ready" ||
          error === "busy" ||
          error === "provider" ||
          error === "failed") && (
          <p className="error-box" role="alert" ref={notice}>
            {error === "voice" &&
              (speech === "zh-CN"
                ? w(
                    "Выберите китайский голос для создания этой версии.",
                    "Choose a Chinese voice to create this version.",
                    "请选择中文配音以创建此版本。",
                  )
                : speech === "ru-RU"
                  ? w(
                      "Выберите русский голос для создания этой версии.",
                      "Choose a Russian voice to create this version.",
                      "请选择俄语配音以创建此版本。",
                    )
                  : w(
                      "Выберите английский голос для создания этой версии.",
                      "Choose an English voice to create this version.",
                      "请选择英文配音以创建此版本。",
                    ))}
            {error === "voice_not_ready" &&
              w(
                "Не удалось собрать озвучку для этого языка. Исходный русский голос не подставляется — смотрите блок Статус.",
                "Could not build voice for this language. Source Russian is not substituted — see Status above.",
                "无法为此语言生成配音。不会改用原片俄语 — 请看上方状态。",
              )}
            {error === "busy" &&
              w(
                "Уже идёт задача по этому проекту. Смотрите блок Статус выше — дождитесь завершения.",
                "A task is already running. See Status above — wait for it to finish.",
                "该项目已有任务进行中。请看上方状态并等待结束。",
              )}
            {error === "provider" &&
              w(
                "Голос для этого языка не настроен. Другой язык не подставляется.",
                "The voice provider is not configured. Another language is not substituted.",
                "这个语言的声音服务未配置，不会改用其他语言。",
              )}
            {error === "failed" &&
              (errorDetail
                ? `${w("Не удалось поставить в очередь", "Could not queue", "无法加入队列")}: ${errorDetail}`
                : w(
                    "Не удалось поставить видео в очередь. Смотрите блок Статус выше или обновите страницу.",
                    "Could not queue the video. See Status above or reload.",
                    "无法加入视频队列。请看上方状态或刷新页面。",
                  ))}
          </p>
        )}
        {error === "voice" &&
          VOICE_CHOICES[speech].map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={voiceChoice === item.id}
              onClick={() => setVoiceChoice(item.id)}
            >
              {item.label}
            </button>
          ))}
      </div>
      <details
        onToggle={(event) => {
          if ((event.currentTarget as HTMLDetailsElement).open) void showDebug();
        }}
      >
        <summary>{w("Проверка языка", "Language debug", "语言检查")}</summary>
        <pre>{debug}</pre>
      </details>
    </section>
  );
}
