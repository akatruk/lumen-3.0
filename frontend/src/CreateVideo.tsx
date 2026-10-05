import { useEffect, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import type { Lang } from "./types";
import { workspaceText } from "./ProjectWorkspace";

type StudioState = {
  context?: {
    reference_file?: boolean;
    references?: { aweme_id?: string; title?: string; author?: string }[];
  };
};

/** The same sentence create-video stores. The page does not build another one. */
export const filmedPrompt =
  "Один ролик, без склейки. Анимация 40%  ведущий в кружке, передний план — графика сказанного. Интенсивность 60%, движение 80%, плотность 70%. Рост — стрелка вверх, падение — стрелка вниз, число — крупная цифра, сравнение — две колонки, срок — отметка на шкале. Только сказанные слова.\n" +
  "Эффекты: color, glow, shadow, blur по краю, kinetic, progress, speed на коротких акцентах, stabilize, split на сравнении, screen, zoom на цифре. Переходы: растворение, шторка, круг. Субтитры средние, белые, внизу. Голос очистить, громкость выровнять, лицо и исходный кадр резкие. Музыка −24 дБ, тише под речь. Звуковые акценты: щелчок, свист, колокольчик.";

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
  const [percent, setPercent] = useState(50);
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
  async function create() {
    if (working || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/studio/projects/" + pid + "/create-video", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ illustration_percent: percent }),
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
      <label>
        {w("Иллюстрация, %", "Illustration, %", "插画，%")}
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={percent}
          aria-valuetext={percent + "%"}
          onChange={(event) => setPercent(Number(event.target.value))}
        />
        <strong>{percent}%</strong>
      </label>
      <pre>{filmedPrompt}</pre>
      <button className="primary" type="button" disabled={working || busy} onClick={() => void create()}>
        {working || busy ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
        {w("Создать видео", "Create video", "创建视频")}
      </button>
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
