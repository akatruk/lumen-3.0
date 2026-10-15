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
  TRANSCRIPTION_PROVIDER_UNAVAILABLE: [
    "Расшифровка недоступна на этом сервере.",
    "Transcription is not available on this server.",
    "此服务器无法转写。",
  ],
  TRANSCRIPTION_FAILED: [
    "Не удалось разобрать речь в исходнике.",
    "Could not transcribe the source audio.",
    "无法转写原片声音。",
  ],
  TRANSCRIPTION_TIMEOUT: [
    "Расшифровка не уложилась в лимит времени.",
    "Transcription timed out.",
    "转写超时。",
  ],
  SOURCE_TRANSCRIPT_UNAVAILABLE: [
    "Нет проверенной расшифровки. Ролик не собирается.",
    "No verified transcript. The video was not built.",
    "没有经过校验的字幕稿，未生成视频。",
  ],
  SOURCE_LANGUAGE_UNVERIFIED: [
    "Язык речи не подтверждён.",
    "Source language was not verified.",
    "未能确认原片语言。",
  ],
  MISSING_TARGET_LANGUAGE_VOICE: [
    "Нет голоса для выбранного языка.",
    "No voice for the selected language.",
    "所选语言没有可用声音。",
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
  if (kind === "transcribe") return w("Расшифровка", "Transcript", "转写");
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
  const transcript = p.metadata?.transcription;
  const preparing = transcript === "transcription_pending" || transcript === "transcription_running";
  if (p.status === "complete" || p.stage === "complete") {
    return w("Ролик готов", "Video ready", "视频已就绪");
  }
  if (p.status === "rendering" || p.stage === "rendering") {
    return w("Собираем видео", "Creating video", "正在生成视频");
  }
  if (preparing && (p.status === "ready" || p.status === "queued" || p.stage === "ready" || p.stage === "render_queued")) {
    return w("Готовим расшифровку", "Preparing transcript", "正在准备字幕稿");
  }
  if (transcript === "transcription_failed" && (p.status === "ready" || p.stage === "ready")) {
    return w("Расшифровка не удалась", "Transcript failed", "字幕稿失败");
  }
  if (transcript === "transcription_completed" && (p.status === "ready" || p.stage === "ready")) {
    return w("Расшифровка готова", "Transcript ready", "字幕稿已就绪");
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
        : p.metadata?.transcription === "transcription_pending" || p.metadata?.transcription === "transcription_running"
        ? w(
            "Исходник загружен. Речь разбирается в фоне.",
            "Source uploaded. Speech is being transcribed.",
            "原片已上传，正在后台转写。",
          )
        : p.metadata?.transcription === "transcription_failed"
          ? w(
              "Расшифровка не удалась. Ролик из заглушек не собирается.",
              "Transcript failed. No video is built from placeholder speech.",
              "转写失败。不会用占位文本生成视频。",
            )
      : p.metadata?.director_mode === "heuristic" || p.metadata?.analysis_quality === "local_baseline"
          ? w(
              "План локальный (без LLM Director). Качество не равно AI-режиссуре.",
              "Local baseline plan (no LLM Director). Not AI-directed quality.",
              "本地基线计划（非 LLM 导演），不等于 AI 导演质量。",
            )
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
