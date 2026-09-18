import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Scissors,
  Captions,
  AudioLines,
  Sparkles,
  FolderOpen,
  ListChecks,
  History,
  Download,
  ArrowLeft,
  X,
  Play,
  Layers,
  CheckCircle2,
} from "lucide-react";
import type { Project, Lang } from "./types";
import { contentLanguage } from "./locale";
import { StatusBadge, TaskProgress } from "./TaskStatus";
export type WorkspaceTask =
  "edit" | "subtitles" | "audio" | "effects" | "materials" | "review";
export const workspaceText = (
  lang: Lang,
  ru: string,
  en: string,
  zh: string,
) => (lang === "ru" ? ru : lang === "zh" ? zh : en);
type WorkspaceContextValue = {
  task: WorkspaceTask;
  setTask: (t: WorkspaceTask) => void;
  previewTarget: HTMLDivElement | null;
  scenesTarget: HTMLDivElement | null;
  actionsTarget: HTMLDivElement | null;
  deliveryTarget: HTMLDivElement | null;
  renderId?: string;
  finalAudioId?: string;
  draftActive: boolean;
  showDraft: () => void;
  seekSource: (start: number, end?: number) => void;
  refreshFinal: () => void;
  previewVersion: (url: string, label: string) => void;
};
const Context = createContext<WorkspaceContextValue | null>(null);
export function useWorkspace() {
  return useContext(Context);
}
type Version = {
  id: string;
  label: string;
  url: string;
  download: string;
  detail: string;
};
const fmt = (n: number) =>
  `${Math.floor(n / 60)}:${String(Math.floor(n % 60)).padStart(2, "0")}`;
export function ProjectWorkspace({
  p,
  lang,
  onBack,
  children,
}: {
  p: Project;
  lang: Lang;
  onBack: () => void;
  children: ReactNode;
}) {
  const w = (r: string, e: string, z: string) => workspaceText(lang, r, e, z);
  const [task, setTask] = useState<WorkspaceTask>(p.studio ? "edit" : "review");
  const [version, setVersion] = useState("result"),
    [dubs, setDubs] = useState<Version[]>([]),
    [loadError, setLoadError] = useState(false),
    [draftActive, setDraftActive] = useState(false),
    [custom, setCustom] = useState<Version | null>(null);
  const [finalVoiceState, setFinalVoice] = useState<{id:string; label:string; masterId:string; url:string} | null>(null);
  const finalVoice = finalVoiceState?.masterId === p.result?.render_id ? finalVoiceState : null;
  const [finalRefresh, setFinalRefresh] = useState(0);
  const finalIdentity = useRef<string | null>(null);
  const [previewTarget, setPreviewTarget] = useState<HTMLDivElement | null>(
      null,
    ),
    [scenesTarget, setScenesTarget] = useState<HTMLDivElement | null>(null),
    [actionsTarget, setActionsTarget] = useState<HTMLDivElement | null>(null);
  const [deliveryTarget,setDeliveryTarget]=useState<HTMLDivElement|null>(null);
  const comparison = useRef<Version | null>(null);
  const [mediaError, setMediaError] = useState(false);
  const [playNotice, setPlayNotice] = useState("");
  const player = useRef<HTMLVideoElement>(null),
    dialog = useRef<HTMLDialogElement>(null),
    returnFocus = useRef<HTMLElement | null>(null),
    pending = useRef<{ start: number; end?: number } | null>(null),
    stop = useRef<number | undefined>(undefined);
  const base = `/api/projects/${p.id}/media/`;
  const working = ["queued", "importing", "analyzing", "rendering"].includes(
    p.status,
  );
  const versions: Version[] = [
    ...(p.result
      ? [
          {
            id: "result",
            label: w("Готовый ролик", "Finished video", "已完成视频") + (finalVoice ? ` · ${finalVoice.label}` : ''),
            url: finalVoice ? finalVoice.url : base + "result?v=" + (p.result.render_id || ''),
            download: base + "result",
            detail: `${fmt(p.result.metadata.duration)} · ${p.result.metadata.width} × ${p.result.metadata.height}`,
          },
        ]
      : []),
    ...(p.result && finalVoice ? [{id:'master',label:w('Монтаж до озвучки','Edit before voiceover','配音前的剪辑'),url:base+'master?v='+p.result.render_id,download:base+'master',detail:w('Звук сохранённого монтажа','Audio from the rendered edit','已渲染剪辑的声音')}] : []),
    ...dubs,
    {
      id: "source",
      label: w("Исходник", "Original footage", "原始素材"),
      url: base + "source",
      download: base + "original",
      detail: w(
        "Оригинальные звук и изображение",
        "Original picture and sound",
        "原始画面与声音",
      ),
    },
  ];
  const selected =
    custom || versions.find((v) => v.id === version) || versions[0];
  const exportVersion =
    selected.id === "source"
      ? versions.find((v) => v.id === "result")
      : selected;
  useEffect(() => {
    if (!p.studio) return;
    let alive = true;
    const controller = new AbortController();
    async function poll() {
      try {
        const r = await fetch(`/api/studio/projects/${p.id}/dubbing`, {
          signal: controller.signal,
        });
        if (!r.ok) throw Error();
        const d = await r.json();
        if (alive) {
          const finalId = d.final_version_id || 'master';
          const finalVersion = d.final_version || d.versions.find((v:{id:string})=>v.id===finalId);
          const identity = `${d.master_id}:${finalId}`;
          if (finalIdentity.current !== null && finalIdentity.current !== identity) {
            switchVersion('result');
          }
          finalIdentity.current = identity;
          const versionUrl=(v:{id:string;kind:string})=>v.kind==='mix'?`/api/studio/projects/${p.id}/final-music/${v.id}/video.mp4`:`/api/studio/projects/${p.id}/dubbing/${v.id}/files/video.mp4`;
          const versionLabel=(v:{language:string;voice:string;kind:string;music_title?:string;music?:unknown})=>[v.voice?`${({ru:'Русский',en:'English',zh:'中文'} as Record<string,string>)[v.language]||v.language} · ${d.voices.find((voice:{id:string})=>voice.id===v.voice)?.name||v.voice}`:'',v.kind==='mix'?(v.music?v.music_title:w('Без добавленной музыки','No added music','无新增音乐')):''].filter(Boolean).join(' · ');
          setFinalVoice(finalVersion && finalId!=='master' ? {id:finalVersion.id,masterId:d.master_id,url:versionUrl(finalVersion),label:versionLabel(finalVersion)} : null);
          setDubs(
            d.versions
              .filter(
                (v: { kind: string; status: string }) =>
                  (v.kind === "video" || v.kind === "mix") && v.status === "ready",
              )
              .map(
                (v: {
                  id: string;
                  kind: string;
                  music_title?:string;
                  music?:unknown;
                  language: string;
                  voice: string;
                  stale: boolean;
                  created: number;
                }) => ({
                  id: v.id,
                  label: versionLabel(v),
                  url: versionUrl(v),
                  download: versionUrl(v)+'?download=true',
                  detail: `${new Date(v.created * 1000).toLocaleString(lang)} · ${v.stale ? w("Предыдущий ролик", "Earlier video", "较早版本") : w("Текущий ролик", "Current video", "当前版本")} · ${v.id.slice(0, 6)}`,
                }),
              ),
          );
          setLoadError(false);
        }
      } catch {
        if (alive) setLoadError(true);
      }
    }
    void poll();
    const timer = setInterval(poll, 5000);
    return () => {
      alive = false;
      controller.abort();
      clearInterval(timer);
    };
  }, [p.id, p.studio, p.result?.render_id, lang, finalRefresh]);
  function switchVersion(id: string) {
    player.current?.pause();
    pending.current = null;
    stop.current = undefined;
    setCustom(null);
    setVersion(id);
    setDraftActive(false);
    setMediaError(false);
  }
  function playPendingMoment() {
    const video = player.current,
      range = pending.current;
    if (!video || !range || video.readyState < 1) return;
    pending.current = null;
    video.currentTime = Math.min(
      range.start,
      Math.max(0, video.duration - 0.01),
    );
    stop.current = range.end;
    void video
      .play()
      .catch(() =>
        setPlayNotice(
          w(
            "Нажмите Play, чтобы посмотреть выбранный момент.",
            "Press Play to watch the selected moment.",
            "请点击播放查看所选片段。",
          ),
        ),
      );
    requestAnimationFrame(() =>
      video.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
  }
  function seekSource(start: number, end?: number) {
    if (
      !Number.isFinite(start) ||
      start < 0 ||
      (end !== undefined && (!Number.isFinite(end) || end <= start))
    )
      return;
    switchVersion("source");
    setPlayNotice("");
    pending.current = { start, end };
    if (selected.id === "source") playPendingMoment();
  }
  function compare() {
    if (selected.id === "source" && comparison.current) {
      const previous = comparison.current;
      switchVersion(previous.id);
      if (!versions.some((v) => v.id === previous.id)) setCustom(previous);
      comparison.current = null;
    } else if (selected.id === "source" && p.result) switchVersion("result");
    else {
      comparison.current = selected;
      switchVersion("source");
    }
  }
  function openVersions() {
    returnFocus.current = document.activeElement as HTMLElement;
    dialog.current?.showModal();
  }
  const tools = p.studio
    ? ([
        ["edit", Scissors, w("Монтаж", "Edit", "剪辑")],
        ["subtitles", Captions, w("Субтитры", "Subtitles", "字幕")],
        ["audio", AudioLines, w("Звук", "Audio", "声音")],
        ["effects", Sparkles, w("Эффекты", "Effects", "效果")],
        ["materials", FolderOpen, w("Материалы", "Materials", "素材")],
        ["review", ListChecks, w("Проверка", "Review", "审核")],
      ] as const)
    : ([["review", ListChecks, w("Анализ", "Analysis", "分析")]] as const);
  return (
    <Context.Provider
      value={{
        task,
        setTask,
        previewTarget,
        scenesTarget,
        actionsTarget,
        deliveryTarget,
        renderId:p.result?.render_id,
        finalAudioId:finalVoice?.id,
        draftActive,
        showDraft: () => {
          player.current?.pause();
          setDraftActive(true);
        },
        seekSource,
        refreshFinal: () => { switchVersion('result'); setFinalRefresh(n=>n+1); },
        previewVersion: (url, label) => {
          setCustom({
            id: url,
            url,
            label,
            download: url + "?download=true",
            detail: "",
          });
          setDraftActive(false);
        },
      }}
    >
      <div className="project-workspace">
        <button className="text-button ws-back" onClick={onBack}>
          <ArrowLeft size={15} />
          {w("Проекты", "Projects", "项目")}
        </button>
        <header className="ws-heading">
          <div>
            <span className="eyebrow">
              {w("ВАШ ПРОЕКТ", "YOUR PROJECT", "您的项目")}
            </span>
            <h1>{p.title}</h1>
          </div>
          <div className="ws-heading-actions">
            <button className="secondary" onClick={openVersions}>
              <History size={16} />
              {w("Версии", "Versions", "版本")} <span>{versions.length}</span>
            </button>
            {p.result && (
              <a
                className="primary ws-header-download"
                href={exportVersion?.download || base + "result"}
                title={exportVersion?.label}
                download
              >
                <Download size={16} />
                {w("Скачать видео", "Download video", "下载视频")}
              </a>
            )}
          </div>
        </header>
        <div className="ws-grid">
          <nav
            className="ws-tools"
            aria-label={w("Инструменты проекта", "Project tools", "项目工具")}
          >
            {tools.map(([key, Icon, label]) => (
              <button
                key={key}
                aria-pressed={task === key}
                onClick={() => setTask(key)}
              >
                <Icon size={21} />
                <span>{label}</span>
              </button>
            ))}
          </nav>
          <section className="ws-preview">
            <div className="ws-preview-heading">
              <button className="text-button" onClick={openVersions}>
                <span className="ws-dot" />
                {draftActive
                  ? w("Черновой просмотр", "Draft preview", "草稿预览")
                  : selected.label}
                <History size={14} />
              </button>
              <button
                className="text-button"
                onClick={compare}
                aria-label={w(
                  "Сравнить с исходником",
                  "Compare with original",
                  "对比原片",
                )}
              >
                <Layers size={16} />
                <span>{w("Сравнить", "Compare", "对比")}</span>
              </button>
            </div>
            <div ref={setDeliveryTarget} className="ws-delivery-status"/>
            <div hidden={draftActive} className="ws-ready-player">
              {p.metadata?.preview_ready ? (
                <video
                  ref={player}
                  key={selected.url + p.result?.render_id}
                  controls
                  playsInline
                  preload="metadata"
                  src={selected.url}
                  aria-label={selected.label}
                  onError={() => setMediaError(true)}
                  onLoadedMetadata={playPendingMoment}
                  onLoadedData={() => setMediaError(false)}
                  onTimeUpdate={(e) => {
                    if (
                      stop.current !== undefined &&
                      e.currentTarget.currentTime >= stop.current
                    ) {
                      e.currentTarget.pause();
                      stop.current = undefined;
                    }
                  }}
                />
              ) : (
                <p role="status">
                  {w(
                    "Готовим предпросмотр видео…",
                    "Preparing video preview…",
                    "正在准备视频预览…",
                  )}
                </p>
              )}
            </div>
            {playNotice && !draftActive && <p role="status">{playNotice}</p>}
            {mediaError && !draftActive && (
              <p role="alert">
                {w(
                  "Не удалось загрузить видео. Выберите другую версию или обновите страницу.",
                  "Could not load video. Select another version or reload.",
                  "无法加载视频，请选择其他版本或刷新。",
                )}
              </p>
            )}
            <div
              ref={setPreviewTarget}
              hidden={!draftActive}
              className="ws-draft-slot"
            />
            <div className="ws-preview-meta">
              <span>
                {draftActive
                  ? w(
                      "Приблизительный просмотр · исходный звук",
                      "Approximate preview · original sound",
                      "近似预览 · 原声",
                    )
                  : selected.detail}
              </span>
              {!draftActive && selected.id !== "source" && (
                <a href={selected.download} download>
                  <Download size={15} />
                  {w("Скачать видео", "Download video", "下载视频")}
                </a>
              )}
              {p.studio && p.analysis && !draftActive && (
                <button
                  className="text-button"
                  onClick={() => {
                    player.current?.pause();
                    setDraftActive(true);
                    setTask("edit");
                  }}
                >
                  {w("Редактировать", "Edit video", "编辑视频")}
                </button>
              )}
            </div>
            <div ref={setScenesTarget} className="ws-scene-slot" />
            {!p.studio && p.analysis && (
              <div className="ws-scenes">
                {p.analysis.scenes.map((s, i) => (
                  <button key={i} onClick={() => seekSource(s.start, s.end)}>
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    <strong>{s.title[contentLanguage(lang)]}</strong>
                    <small>
                      {fmt(s.start)}–{fmt(s.end)}
                    </small>
                  </button>
                ))}
              </div>
            )}
            {working && (
              <TaskProgress
                title={w(
                  "Обработка проекта",
                  "Processing project",
                  "正在处理项目",
                )}
                percent={p.progress}
              />
            )}
            {p.error && (
              <p role="alert" className="error-box">
                {w(
                  "Задача завершилась с ошибкой. Готовые версии сохранены; подробности в разделе проверки.",
                  "Task failed. Finished versions are safe; see Review for details.",
                  "任务失败，已完成版本仍保留，请查看审核详情。",
                )}
              </p>
            )}
            <div className="ws-budget">
              ${p.cost.toFixed(3)} / ${p.budget.toFixed(2)} ·{" "}
              {w(
                "Расходы AI / лимит проекта",
                "AI usage / project budget",
                "AI 用量 / 项目预算",
              )}
            </div>
          </section>
          <aside
            className="ws-inspector"
            aria-label={w("Настройки проекта", "Project settings", "项目设置")}
          >
            <header className="ws-inspector-heading">
              <span className="eyebrow">
                {w("ИНСТРУМЕНТЫ", "TOOLS", "工具")}
              </span>
              <h2>{tools.find((t) => t[0] === task)?.[2]}</h2>
            </header>
            {children}
          </aside>
        </div>
        <footer className="ws-footer">
          <div ref={setActionsTarget} className="ws-actions-slot" />
          <div className="ws-fallback-actions">
            <StatusBadge status={p.status}>
              <CheckCircle2 size={14} />{" "}
              {working
                ? w("Обработка", "Processing", "处理中")
                : p.result
                  ? w(
                      "Готовая версия сохранена",
                      "Finished version saved",
                      "已完成版本已保存",
                    )
                  : w(
                      "Проверьте план монтажа",
                      "Review your edit plan",
                      "请审核剪辑计划",
                    )}
            </StatusBadge>
            {p.result && (
              <a
                className="primary"
                href={exportVersion?.download || base + "result"}
                title={exportVersion?.label}
                download
              >
                <Download size={16} />
                {w("Скачать видео", "Download video", "下载视频")}
              </a>
            )}
          </div>
        </footer>
        <dialog
          className="ws-versions"
          ref={dialog}
          onClose={() => returnFocus.current?.focus()}
        >
          <header>
            <h2>{w("Версии ролика", "Video versions", "视频版本")}</h2>
            <button
              className="icon"
              aria-label={w("Закрыть", "Close", "关闭")}
              onClick={() => dialog.current?.close()}
            >
              <X size={20} />
            </button>
          </header>
          <p>
            {w(
              "Выберите версию для просмотра или скачивания.",
              "Select a version to play or download.",
              "选择版本进行播放或下载。",
            )}
          </p>
          {loadError && (
            <p role="alert">
              {w(
                "Не удалось обновить список озвучек. Повторяем подключение…",
                "Could not refresh voiceovers. Reconnecting…",
                "无法刷新配音列表，正在重连…",
              )}
            </p>
          )}
          {versions.map((v) => (
            <article key={v.id}>
              <div>
                <strong>{v.label}</strong>
                <small>{v.detail}</small>
              </div>
              <button
                className="secondary"
                onClick={() => {
                  switchVersion(v.id);
                  dialog.current?.close();
                }}
                aria-label={`${w("Смотреть", "Play", "播放")}: ${v.label}`}
              >
                <Play size={16} />
              </button>
              <a
                className="secondary"
                href={v.download}
                download
                aria-label={`${w("Скачать", "Download", "下载")}: ${v.label}`}
              >
                <Download size={16} />
              </a>
            </article>
          ))}
        </dialog>
      </div>
    </Context.Provider>
  );
}
