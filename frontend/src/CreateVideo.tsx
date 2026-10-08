import { useEffect, useRef, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { Lang } from "./types";
import { workspaceText } from "./ProjectWorkspace";

type Speech = "ru-RU" | "en-US" | "zh-CN";

type StudioState = {
  plan?: {
    transcript?: { original?: string; zh?: string; en?: string; ru?: string }[];
  } | null;
  context?: {
    video_language?: string;
    reference_file?: boolean;
    references?: { aweme_id?: string; title?: string; author?: string }[];
  };
};

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

const SHARES: Share[] = [
  { key: "animation", label: ["Анимация, %", "Animation, %", "动画，%"], min: 0 },
  { key: "intensity", label: ["Интенсивность, %", "Intensity, %", "强度，%"], min: 5 },
  { key: "motion", label: ["Движение, %", "Motion, %", "运动，%"], min: 0 },
  { key: "density", label: ["Плотность, %", "Density, %", "密度，%"], min: 0 },
];

export function CreateVideo({
  pid,
  lang,
  working,
  onStarted,
}: {
  pid: string;
  lang: Lang;
  working: boolean;
  onStarted: () => Promise<void>;
}) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  const [levels, setLevels] = useState({ animation: 60, intensity: 60, motion: 80, density: 70 });
  const [language, setLanguage] = useState<Speech | null>(null);
  const [debug, setDebug] = useState("");
  const [uploads, setUploads] = useState<StudioState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [voiceChoice, setVoiceChoice] = useState<string | null>(null);
  const notice = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    let cancelled = false;
    fetch("/api/studio/projects/" + pid, { credentials: "same-origin" })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled) setUploads(data);
      })
      .catch(() => {
        if (!cancelled) setUploads(null);
      });
    return () => {
      cancelled = true;
    };
  }, [pid]);
  const references = uploads?.context?.references ?? [];
  const videos = [
    w("Ваше видео", "Your video", "你的视频"),
    ...(uploads?.context?.reference_file ? [w("Референс", "Reference video", "参考视频")] : []),
    ...references.map((item) => item.title || item.author || item.aweme_id || w("Референс", "Reference video", "参考视频")),
  ];
  const speech = language ?? savedLanguage(uploads?.context?.video_language) ?? spokenLanguage(uploads);
  const speechLabel = LANGUAGES.find((item) => item.id === speech)?.label ?? speech;
  const sourceSpeech = detectSpeech((uploads?.plan?.transcript ?? []).map((line) => line.original || "").join(" "));
  const originalVoice = sourceSpeech === speech;
  const voiceLabel = originalVoice
    ? w("Оригинальный голос ведущего", "Original speaker audio", "原声")
    : (LANGUAGES.find((item) => item.id === speech)?.voice ?? speech);
  useEffect(() => {
    notice.current?.scrollIntoView({ block: "nearest" });
  }, [error, speech]);
  async function choose(next: Speech) {
    setLanguage(next);
    setError("");
    try {
      const response = await fetch("/api/studio/projects/" + pid + "/language", {
        method: "PUT",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: next }),
      });
      if (!response.ok) setError("failed");
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
    try {
      const response = await fetch("/api/studio/projects/" + pid + "/voice-preview", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: speech }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setError(body?.detail === "MISSING_TARGET_LANGUAGE_VOICE" ? "voice" : body?.detail === "provider_not_configured" ? "provider" : "failed");
        return;
      }
      setDebug([body?.voiceName || "", body?.text || ""].filter(Boolean).join("\n"));
    } catch {
      setError("failed");
    }
  }
  async function create() {
    if (working || busy) return;
    setBusy(true);
    setError("");
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
          language: speech,
          voice: voiceChoice,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        setError(body?.detail === "MISSING_TARGET_LANGUAGE_VOICE" || body?.detail === "VOICE_SETUP_REQUIRED" ? "voice" : "failed");
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
      <div>
        <span className="eyebrow">{w("ЗАГРУЖЕННЫЕ ВИДЕО", "UPLOADED VIDEOS", "已上传视频")}</span>
        <ul>
          {videos.map((name, index) => (
            <li key={index}>{name}</li>
          ))}
        </ul>
      </div>
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
            onChange={(event) =>
              setLevels((current) => ({ ...current, [share.key]: Number(event.target.value) }))
            }
          />
          <strong>{levels[share.key]}%</strong>
        </label>
      ))}
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
          </p>
        )}
        <button type="button" disabled={working || busy} onClick={() => void preview()}>
          {w("Прослушать голос", "Preview voice", "试听声音")}
        </button>
        <button className="primary" type="button" disabled={working || busy} onClick={() => void create()}>
          {working || busy ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
          {w("Создать видео", "Create video", "创建视频")}
        </button>
        {(error === "voice" || error === "provider" || error === "failed") && (
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
            {error === "provider" &&
              w(
                "Голос для этого языка не настроен. Другой язык не подставляется.",
                "The voice provider is not configured. Another language is not substituted.",
                "这个语言的声音服务未配置，不会改用其他语言。",
              )}
            {error === "failed" &&
              w(
                "Не удалось поставить видео в очередь. Дождитесь текущей задачи или обновите страницу.",
                "Could not queue the video. Wait for the current task or reload.",
                "无法加入视频队列。请等待当前任务或刷新页面。",
              )}
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
