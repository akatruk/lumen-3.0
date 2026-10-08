import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { Lang } from "./types";
import { workspaceText } from "./ProjectWorkspace";

type Speech = "ru" | "en" | "zh";

type StudioState = {
  plan?: {
    transcript?: { original?: string; zh?: string; en?: string; ru?: string }[];
  } | null;
  context?: {
    reference_file?: boolean;
    references?: { aweme_id?: string; title?: string; author?: string }[];
  };
};

const LANGUAGES: { id: Speech; label: string }[] = [
  { id: "ru", label: "русский" },
  { id: "en", label: "English" },
  { id: "zh", label: "中文" },
];

function spokenLanguage(data: StudioState | null): Speech {
  const lines = data?.plan?.transcript ?? [];
  const shown = lines
    .map((line) => line.zh || line.original || line.en || line.ru || "")
    .join(" ");
  if (/[\u4e00-\u9fff]/.test(shown)) return "zh";
  if (/[\u0400-\u04FF]/.test(shown)) return "ru";
  if (/[A-Za-z]/.test(shown)) return "en";
  return "zh";
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
  const [uploads, setUploads] = useState<StudioState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
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
  const speech = language ?? spokenLanguage(uploads);
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
        }),
      });
      if (!response.ok) {
        setError("failed");
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
          aria-label={w("Язык", "Language", "语言")}
        >
          {LANGUAGES.map((item) => (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={speech === item.id}
              disabled={working || busy}
              onClick={() => setLanguage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <button className="primary" type="button" disabled={working || busy} onClick={() => void create()}>
          {working || busy ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
          {w("Создать видео", "Create video", "创建视频")}
        </button>
      </div>
      {error && (
        <p role="alert">
          {w(
            "Не удалось поставить видео в очередь. Дождитесь текущей задачи или обновите страницу.",
            "Could not queue the video. Wait for the current task or reload.",
            "无法加入视频队列。请等待当前任务或刷新页面。",
          )}
        </p>
      )}
    </section>
  );
}
