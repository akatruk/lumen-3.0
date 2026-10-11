import { Loader2 } from "lucide-react";
import { activityTitle, activityDetail } from "./AnalysisActivity";
import { workspaceText } from "./ProjectWorkspace";
import type { Lang, Project } from "./types";

type JobSnap = {
  id: string;
  kind: string;
  status: string;
  updated?: number;
  language?: string | null;
  duration_seconds?: number | null;
  composition?: string | null;
  picture_engine?: string | null;
};

const ERROR_COPY: Record<string, [string, string, string]> = {
  target_voice_not_ready: [
    "Нет готовой озвучки для выбранного языка. Исходный голос не подставляется.",
    "No finished voice for this video language. Source voice is not substituted.",
    "所选视频语言还没有成品配音，不会改用原片声音。",
  ],
  VOICE_SETUP_REQUIRED: [
    "Нужно выбрать голос для этого языка.",
    "Choose a voice for this language.",
    "请为此语言选择配音。",
  ],
  job_already_running: [
    "Уже идёт задача по этому проекту.",
    "A task is already running for this project.",
    "该项目已有任务在进行。",
  ],
  director_v3_render_failed: [
    "Рендер режиссёрской картины не удался. Исходник сохранён.",
    "Director picture render failed. Your original is safe.",
    "导演画面渲染失败。原始视频已保留。",
  ],
  processing_failed: [
    "Обработка не завершена. Исходник сохранён.",
    "Processing could not finish. Your original is safe.",
    "处理未能完成，原视频已保留。",
  ],
};

function localeLabel(lang: Lang, locale?: string | null) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  if (!locale) return w("не задан", "not set", "未设置");
  if (locale.startsWith("ru")) return w("Русский", "Russian", "俄语");
  if (locale.startsWith("en")) return w("English", "English", "英语");
  if (locale.startsWith("zh")) return w("中文", "Chinese", "中文");
  return locale;
}

function kindLabel(lang: Lang, kind?: string | null) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  if (kind === "director_v3") return w("Director V3 (Remotion)", "Director V3 (Remotion)", "Director V3（Remotion）");
  if (kind === "studio_render" || kind === "render") return w("Сборка ролика", "Video render", "视频渲染");
  if (kind === "analysis") return w("Анализ", "Analysis", "分析");
  return kind || w("задача", "job", "任务");
}

function jobPhase(lang: Lang, status?: string | null) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  if (status === "queued") return w("В очереди", "Queued", "排队中");
  if (status === "running") return w("Выполняется", "Running", "进行中");
  if (status === "complete") return w("Готово", "Complete", "已完成");
  if (status === "failed") return w("Ошибка", "Failed", "失败");
  return status || "—";
}

function projectPhase(lang: Lang, p: Project) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  if (p.status === "complete" || p.stage === "complete") {
    return w("Ролик готов", "Video ready", "视频已就绪");
  }
  if (p.status === "needs_review" || p.stage === "needs_review") {
    return w("На проверке", "Needs review", "待复核");
  }
  if (p.status === "failed" || p.stage === "failed") {
    return w("Ошибка", "Failed", "失败");
  }
  if (["queued", "render_queued"].includes(p.status) || p.stage === "render_queued") {
    return w("В очереди на сборку", "Queued for render", "等待渲染");
  }
  return activityTitle(p.metadata?.activity, lang, p.stage);
}

function errorText(lang: Lang, code?: string | null) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  if (!code) return null;
  const row = ERROR_COPY[code];
  if (row) return w(...row);
  return `${w("Код", "Code", "代码")}: ${code}`;
}

export function projectIsBusy(p: Project) {
  if (p.active_job) return true;
  return ["queued", "importing", "analyzing", "rendering"].includes(p.status);
}

/** Live STATUS strip: step, progress, locale, job, human error — not a dead-end. */
export function ProjectJobStatus({
  p,
  lang,
  compact,
}: {
  p: Project;
  lang: Lang;
  compact?: boolean;
}) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  const busy = projectIsBusy(p);
  const job = (p.active_job || p.latest_job) as JobSnap | null | undefined;
  const locale = p.video_language || job?.language || null;
  const err = errorText(lang, p.error);
  const title = busy
    ? activityTitle(p.metadata?.activity, lang, p.stage) || projectPhase(lang, p)
    : projectPhase(lang, p);
  const activityNote = p.metadata?.activity?.note || "";
  const detail = busy
    ? activityDetail(p.metadata?.activity, lang, p.stage)
    : p.error
      ? [err, activityNote && activityNote !== err ? activityNote : ""].filter(Boolean).join(" — ")
      : p.result?.render_id
        ? w("Можно смотреть и скачать текущую версию.", "You can play and download the current version.", "可播放并下载当前版本。")
        : w("Исходник сохранён. Можно создать видео.", "Your original is safe. You can create a video.", "原始素材已保留，可以创建视频。");

  return (
    <section
      className={"project-job-status" + (busy ? " is-live" : "") + (p.error ? " is-error" : "")}
      aria-live="polite"
      role="status"
    >
      <header>
        {busy ? <Loader2 className="spin" size={16} aria-hidden /> : null}
        <strong>{w("Статус", "Status", "状态")}</strong>
        <span className="phase">{title}</span>
      </header>
      <p className="detail">{detail}</p>
      <dl>
        <div>
          <dt>{w("Проект", "Project", "项目")}</dt>
          <dd>
            {p.status} · {p.stage}
            {typeof p.progress === "number" ? ` · ${p.progress}%` : ""}
          </dd>
        </div>
        <div>
          <dt>{w("Язык видео", "Video language", "视频语言")}</dt>
          <dd>{localeLabel(lang, locale)}</dd>
        </div>
        {job && (
          <div>
            <dt>{w("Задача", "Job", "任务")}</dt>
            <dd>
              {kindLabel(lang, job.kind)} · {jobPhase(lang, job.status)}
              {job.id ? ` · ${job.id.slice(0, 8)}` : ""}
            </dd>
          </div>
        )}
        {p.error && (
          <div>
            <dt>{w("Ошибка", "Error", "错误")}</dt>
            <dd>
              <code>{p.error}</code>
              {!compact && err ? ` — ${err}` : ""}
            </dd>
          </div>
        )}
      </dl>
      {busy && (
        <p className="hint">
          {w(
            "Страница обновляется сама. Исходник не трогаем.",
            "This page refreshes automatically. Your original stays untouched.",
            "页面会自动刷新。原始素材不会改动。",
          )}
        </p>
      )}
    </section>
  );
}
