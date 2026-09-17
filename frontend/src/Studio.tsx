import {CreatorStyle,defaultStyle,type Style} from './CreatorStyle';
import {StatusBadge,TaskProgress,UploadProgress} from './TaskStatus';
import {CreativePlan} from './CreativePlan';
import {uploadVideo} from './resumableUpload';
import {ManualEditor} from './ManualEditor';
import { DirectorAlternatives } from "./DirectorAlternatives";
import { PlatformVariants } from "./PlatformVariants";
import { useEffect, useRef, useState } from "react";
import { DouyinSearch, type Hit } from "./DouyinSearch";
import type { Lang, Project, Analysis, Text } from "./types";
import "./studio.css";
const labels: Record<string, [string, string]> = {
  upload_interrupted: ['Upload connection interrupted. Keep this page open and try again to resume from the last saved chunk.','上传连接中断。请保留此页面并重试，将从已保存的位置继续。'],
  upload_timeout: ['Upload timed out. Try again to resume; completed chunks are saved for 24 hours.','上传超时。请重试以继续上传；已完成部分保留 24 小时。'],
  upload_expired: ['This temporary upload expired. Select the file again to start a new upload.','临时上传已过期。请重新选择文件并开始上传。'],
  too_many_uploads: ['Too many unfinished uploads. Resume an existing upload or try again later.','未完成的上传过多。请继续现有上传或稍后重试。'],
  upload_http_502: ['Upload server temporarily unavailable. Try again to resume.','上传服务暂时不可用。请重试以继续。'],
  upload_http_503: ['Upload server temporarily unavailable. Try again to resume.','上传服务暂时不可用。请重试以继续。'],
  upload_http_504: ['The upload response timed out. Try again to resume.','上传响应超时。请重试以继续。'],

  provider_invalid_analysis: [
    "The AI service returned an invalid analysis. Your video is saved; uploading it again is not necessary.",
    "AI 服务返回的分析格式无效。视频已保存，无需重新上传。",
  ],
  provider_analysis_truncated: [
    "The AI response stopped before the analysis was complete. Your video is saved.",
    "AI 回复在分析完成前被截断。视频已保存。",
  ],
  unauthorized: [
    "Your session expired. Sign in again.",
    "会话已过期，请重新登录。",
  ],
  owned_duration: [
    "Use owned footage between 30 seconds and 7 minutes.",
    "请上传 30 秒至 7 分钟的自有视频。",
  ],
  owned_vertical: [
    "Use a vertical video for this pilot.",
    "试用版请上传竖屏视频。",
  ],
  invalid_settings: [
    "Check the fields and rights confirmation.",
    "请检查表单和使用权确认。",
  ],
  douyin_search_expired: [
    "Reference selection expired. Search again and select the references.",
    "参考视频已过期，请重新搜索并选择。",
  ],
  duplicate_reference: [
    "Choose different reference videos.",
    "请选择不同的参考视频。",
  ],
  too_many_jobs: [
    "Three projects are already processing. Wait for one to finish.",
    "已有三个项目处理中，请等待完成。",
  ],
  plan_changed: [
    "The plan changed. Reload it before saving.",
    "计划已更新，请重新加载后保存。",
  ],
  locked_decision: [
    "Unlock and save first before changing a locked decision.",
    "请先解锁并保存，再修改此决策。",
  ],
  lock_requires_approval: [
    "Approve a change before locking it.",
    "请先批准改动，再锁定。",
  ],
  no_approved_changes: [
    "Approve at least one change before rendering.",
    "请至少批准一项改动。",
  ],
  job_already_running: ["Processing is already running.", "任务已在处理中。"],
  budget_limit: [
    "The project or workspace budget is exhausted.",
    "项目或工作空间预算不足。",
  ],
  upload_too_large: ["Maximum file size is 250 MB.", "文件最大为 250 MB。"],
  not_a_video: [
    "This file could not be read as a supported video.",
    "无法读取该视频文件。",
  ],
  storage_full: [
    "The workspace has insufficient storage.",
    "工作空间存储不足。",
  ],
  hook_overlaps_cut: [
    "The opening overlaps a deleted segment. Adjust the selection.",
    "开场与删除片段重叠，请调整。",
  ],
  too_much_removed: [
    "The selected cuts remove too much footage.",
    "所选剪辑删除了过多内容。",
  ],
  analysis_timestamps_invalid: [
    "Check the start and end times.",
    "请检查起止时间。",
  ],
  douyin_search_failed: [
    "TikHub could not retrieve the selected Douyin reference. Your uploaded video is preserved. Retrying may fail again while the reference is unavailable.",
    "TikHub 无法获取所选抖音参考视频。您上传的视频已保留。参考视频不可用时，重试仍可能失败。",
  ],
  douyin_media_unavailable: [
    "The selected Douyin reference could not be retrieved. Your uploaded video is preserved; this is not an upload failure.",
    "无法获取所选抖音参考视频。您上传的视频已保留，这不是上传失败。",
  ],
  douyin_auth_failed: ["TikHub authentication failed. The service configuration needs attention.", "TikHub 身份验证失败，请检查服务配置。"],
  douyin_credits_required: ["TikHub requires credits to retrieve the reference.", "TikHub 余额不足，无法获取参考视频。"],
  douyin_rate_limited: ["TikHub is rate limiting requests. Please try later.", "TikHub 请求过于频繁，请稍后重试。"],
  provider_credits_required: [
    "The AI provider needs credits.",
    "AI 服务余额不足。",
  ],
};
function message(code: string, lang: Lang) {
  return (labels[code] || [
    "The operation failed. Try again; your source is preserved.",
    "操作失败，请重试。原始素材已保留。",
  ])[lang === "zh" ? 1 : 0];
}
async function request(path: string, init?: RequestInit) {
  const r = await fetch("/api" + path, init);
  let data;
  try {
    data = await r.json();
  } catch {
    throw Error("request_failed");
  }
  if (!r.ok)
    throw Error(
      typeof data.detail === "string" ? data.detail : "request_failed",
    );
  return data;
}
const body = (data: unknown, method = "POST") => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});
export function StudioCreate({
  lang,
  userKey,
  onCreated,
}: {
  lang: Lang;
  userKey: string;
  onCreated: (id: string) => void;
}) {
  const zh = lang === "zh",
    t = (en: string, cn: string) => (zh ? cn : en);
  const cache = "lumen-reference-draft:" + userKey;
  const [refs, setRefs] = useState<Hit[]>(() => {
    try {
      return JSON.parse(sessionStorage.getItem(cache) || "[]");
    } catch {
      return [];
    }
  });
  const [file, setFile] = useState<File | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [percent, setPercent] = useState(0),
    [paused,setPaused] = useState(false);
  const [style,setStyle]=useState<Style>(defaultStyle);
  const [transfer,setTransfer]=useState<{bytes:number;total:number;mbps:number}|null>(null);
  const xhr = useRef<AbortController | null>(null);
  const requestId = useRef(crypto.randomUUID().replaceAll("-", ""));
  useEffect(() => {
    sessionStorage.setItem(cache, JSON.stringify(refs));
  }, [cache, refs]);
  useEffect(
    () => () => {
      xhr.current?.abort();
    },
    [],
  );
  function select(hit: Hit) {
    if (refs.length >= 5) {
      setError("max_references");
      return;
    }
    setRefs((v) =>
      v.some((r) => r.aweme_id === hit.aweme_id) ? v : [...v, hit],
    );
  }
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file || !refs.length) return;
    setError("");
    if (file.size > 250 * 1024 * 1024) {
      setError("upload_too_large");
      return;
    }
    const f = new FormData(e.currentTarget);
    const config = {
      request_id: requestId.current,
      references: refs.map((r) => r.id),
      title: f.get("title"),
      script: f.get("script"),
      creator: {
        style,
        topic: f.get("topic"),
        audience: f.get("audience"),
        tone: f.get("tone"),
        rules: f.get("rules"),
      },
      language: f.get("language"),
      budget: Number(f.get("budget")),
      owned_rights_confirmed: f.has("rights"),
    };
    setBusy(true);setPaused(false);setPercent(0);setTransfer(null);
    const controller=new AbortController();xhr.current=controller;
    try {
      const p=await uploadVideo(file,config,controller.signal,(n,info)=>{setPercent(n);if(info)setTransfer(info)});
      sessionStorage.removeItem(cache);onCreated(p.id);
    } catch(e) {
      const code=e instanceof Error?e.message:'upload_interrupted';
      if(code==='upload_cancelled')setPaused(true);else setError(code);
    } finally {setBusy(false)}

  }
  return (
    <div className="director-create page">
      <header className="director-intro">
        <span className="eyebrow">LUMEN / DIRECTOR STUDIO</span>
        <h1>
          {t(
            "Learn the technique. Tell your story.",
            "借鉴创作方法，讲好自己的故事。",
          )}
        </h1>
        <p>
          {t(
            "Choose 1–5 references, add your own footage, then review an editable plan. Reference footage never enters your final cut.",
            "选择 1–5 支参考视频，上传自己的素材，再审核可编辑的剪辑计划。参考画面不会被用于成片。",
          )}
        </p>
      </header>
      <div className="pilot-platforms">
        <span>Douyin</span>
        <span>Instagram Reels</span>
        <span>YouTube Shorts</span>
        <small>
          {t(
            "Master editing · five platform previews · export",
            "主版本剪辑 · 五个平台预览 · 导出",
          )}
        </small>
      </div>
      <fieldset disabled={busy} className="director-fieldset">
        <DouyinSearch
          lang={lang}
          onImported={() => {}}
          onSelect={select}
          selectedIds={refs.map((r) => r.aweme_id)}
        />
      </fieldset>
      <section className="director-card">
        <h2>
          {t("1. Your references", "1. 参考视频")}{" "}
          <small>{refs.length}/5</small>
        </h2>
        {!refs.length && (
          <p>
            {t(
              "Add references from the search above. These teach Lumen editing techniques, not what footage to copy.",
              "从上方搜索结果添加参考视频，用来分析剪辑方法，而不是复制素材。",
            )}
          </p>
        )}
        <ul className="reference-selection">
          {refs.map((r) => (
            <li key={r.aweme_id}>
              <div>
                <strong>{r.title}</strong>
                <a href={r.share_url} target="_blank" rel="noreferrer">
                  {r.author} ↗
                </a>
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  setRefs((v) => v.filter((x) => x.aweme_id !== r.aweme_id))
                }
              >
                {t("Remove", "移除")}
              </button>
            </li>
          ))}
        </ul>
      </section>
      <form onSubmit={submit} className="director-form">
        <fieldset disabled={busy} className="director-fieldset">
          <section className="director-card">
            <h2>{t("2. Your own footage & script", "2. 自有素材与脚本")}</h2>
            <p>
              {t(
                "One vertical video · 30 seconds–7 minutes · up to 250 MB. Use footage you own or are licensed to edit.",
                "一支竖屏视频 · 30 秒至 7 分钟 · 最大 250 MB。请使用自有或已获授权的素材。",
              )}
            </p>
            <label>
              {t("Choose your video to upload", "选择要上传的自有视频")}
              <input
                required
                className="director-file-input"
                aria-describedby="owned-video-selection"
                type="file"
                accept="video/mp4,video/quicktime,video/webm,.mov"
                onChange={(e) => {
                  const selected = e.target.files?.[0] || null;
                  if (selected && selected.size > 250 * 1024 * 1024) {
                    setError("upload_too_large");
                    setFile(null);
                    e.target.value = "";
                  } else {
                    setFile(selected);
                    setError("");
                  }
                }}
              />
            </label>
            <p id="owned-video-selection" role="status" className="director-file-status">
              {file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(1)} MB` : t("No video selected. Choose a file from your device above.", "尚未选择视频。请在上方从设备中选择文件。")}
            </p>
            <label>
              {t("Project name", "项目名称")}
              <input name="title" required maxLength={120} />
            </label>
            <label>
              {t("Script & intended message", "脚本与核心信息")}
              <textarea
                name="script"
                required
                maxLength={6000}
                rows={4}
                placeholder={t(
                  "What should the viewer understand or do? Include your script and facts that must stay unchanged.",
                  "观众应理解什么、采取什么行动？请填写脚本以及必须保留的事实。",
                )}
              />
            </label>
            <label className="director-check">
              <input name="rights" type="checkbox" required />
              {t(
                "I own or have permission to edit this footage.",
                "我拥有或已获得此素材的编辑使用权。",
              )}
            </label>
          </section>
          <section className="director-card">
            <h2>{t("3. Creator & brand profile", "3. 创作者与品牌风格")}</h2>
            <div className="director-form-grid">
              <label>
                {t("Topic", "主题")}
                <select name="topic">
                  <option value="real_estate">
                    {t("Real estate", "房地产")}
                  </option>
                  <option value="citizenship">
                    {t("Citizenship abroad", "海外国籍")}
                  </option>
                  <option value="travel">{t("Travel", "旅行")}</option>
                </select>
              </label>
              <label>
                {t("Caption language", "字幕语言")}
                <select name="language" defaultValue={lang}>
                  <option value="en">English</option>
                  <option value="zh">简体中文</option>
                </select>
              </label>
              <label>
                {t("Audience", "目标受众")}
                <input
                  name="audience"
                  required
                  maxLength={1000}
                  placeholder={t("Who is this for?", "这支视频是为谁制作的？")}
                />
              </label>
              <label>
                {t("Voice & style", "语气与风格")}
                <input
                  name="tone"
                  required
                  maxLength={1000}
                  placeholder={t(
                    "For example: calm, factual, personal",
                    "例如：平静、客观、亲切",
                  )}
                />
              </label>
            </div>
            <CreatorStyle value={style} onChange={setStyle} lang={lang}/>
            <label>
              {t("Brand rules & claims to avoid", "品牌规则与禁止的表述")}
              <textarea name="rules" maxLength={2000} rows={3} />
            </label>
            <label>
              {t("Project AI spending limit", "项目 AI 费用上限")}
              <select name="budget" defaultValue="5">
                <option value="1">$1</option>
                <option value="3">$3</option>
                <option value="5">$5</option>
                <option value="10">$10</option>
              </select>
            </label>
            <p className="director-note">
              {t(
                "This is a spending ceiling, not a price quote. Reference analysis, planning and review share it; TikHub charges are separate. Footage is sent to the configured AI provider. No rendering starts before your approval.",
                "这是费用上限，不是报价。参考分析、计划和复核共用该额度；TikHub 费用另计。素材会发送至已配置的 AI 服务。审核前不会开始制作成片。",
              )}
            </p>
          </section>
        </fieldset>
        {error && (
          <p role="alert" className="error-box">
            {error === "max_references"
              ? t("Choose up to five references.", "最多选择五支参考视频。")
              : message(error, lang)}
          </p>
        )}
        {paused && <p role="status"><StatusBadge status="paused">{t('Upload paused — saved chunks are preserved. Start again to resume.','上传已暂停 — 已保存的部分保留。再次开始即可继续。')}</StatusBadge></p>}
        <div className="director-submit">
          {busy ? <UploadProgress percent={percent} lang={lang} bytes={transfer?.bytes} total={transfer?.total} mbps={transfer?.mbps}/> : <span role="status">
            {busy
              ? percent === 100
                ? t(
                    "Upload received. Checking the file…",
                    "上传已完成，正在检查文件…",
                  )
                : `${t("Uploading · saved", "上传中 · 已保存")} ${percent}%${transfer?` · ${(transfer.bytes/1048576).toFixed(1)} / ${(transfer.total/1048576).toFixed(1)} MB${transfer.mbps>0?` · ${transfer.mbps.toFixed(1)} MB/s`:""}`:""}`
              : !file && !refs.length
                ? t("Select at least one reference in step 1 and your own video in step 2.", "请在第 1 步选择至少一个参考视频，并在第 2 步选择自有视频。")
                : !file
                  ? t("Choose your own video in step 2 to continue.", "请在第 2 步选择自有视频以继续。")
                  : !refs.length
                    ? t("Select at least one reference in step 1 to continue.", "请在第 1 步选择至少一个参考视频以继续。")
                    : t(
                  "Next: Video DNA → Director Timeline → your approval",
                  "下一步：视频 DNA → 剪辑计划 → 您的审核",
                )}
          </span>}
          {busy ? (
            <button
              type="button"
              className="secondary"
              onClick={() => xhr.current?.abort()}
            >
              {t("Pause upload", "暂停上传")}
            </button>
          ) : (
            <button className="primary" disabled={!file || !refs.length}>
              {t("Analyze & build my plan", "分析并创建剪辑计划")}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

type Decision = {
  id: string;
  approved: boolean;
  locked: boolean;
  start: number;
  end: number;
};
type Transfer = {
  recommendation_id: string;
  reference_id: string;
  reference_start: number;
  reference_end: number;
  method: Text;
  fit: Text;
};
type State = {
  context: {
    creator: { style?:Style; topic: string; audience: string; tone: string; rules: string };
    references: {
      aweme_id: string;
      title: string;
      author: string;
      share_url: string;
    }[];
    platforms: string[];
  };
  dna: {
    reference_id: string;
    duration: number;
    analysis: {
      summary: Text;
      shots: ({
        start: number;
        end: number;
        observation: Text;
        reusable_method: Text;
      } & Record<string, unknown>)[];
      uncertainties: Text[];
    };
  }[];
  plan: (Analysis & { transfers: Transfer[] }) | null;
  decisions: Decision[];
  revision: number;
};
export function DirectorProject({
  p,
  lang,
  onBack,
  onRefresh,
}: {
  p: Project;
  lang: Lang;
  onBack: () => void;
  onRefresh: () => Promise<void>;
}) {
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const [state, setState] = useState<State | null>(null),
    [decisions, setDecisions] = useState<Decision[]>([]),
    [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [section, setSection] = useState("plan"),
    [mode, setMode] = useState("source");
  const video = useRef<HTMLVideoElement>(null),
    editing = useRef(false);
  const pendingSeek = useRef<number | null>(null);
  const draftKey = "lumen-plan-draft:" + p.id;
  const hydrated = useRef(false);
  useEffect(() => {
    let live = true;
    async function get() {
      try {
        const s = await request("/studio/projects/" + p.id);
        if (live && !editing.current) {
          setState(s);
          if (!hydrated.current) {
            hydrated.current = true;
            try {
              const draft = JSON.parse(
                sessionStorage.getItem(draftKey) || "null",
              );
              if (draft && draft.revision === s.revision) {
                setDecisions(draft.decisions);
                editing.current = true;
                setDirty(true);
                return;
              }
              if (draft) sessionStorage.removeItem(draftKey);
            } catch {
              sessionStorage.removeItem(draftKey);
            }
          }
          setDecisions(s.decisions);
        }
      } catch (e) {
        if (live) setError((e as Error).message);
      }
    }
    void get();
    const id = setInterval(get, 5000);
    return () => {
      live = false;
      clearInterval(id);
    };
  }, [p.id]);
  useEffect(() => {
    const listener = (e: BeforeUnloadEvent) => {
      if (editing.current) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", listener);
    return () => window.removeEventListener("beforeunload", listener);
  }, []);
  useEffect(() => {
    if (dirty && state)
      sessionStorage.setItem(
        draftKey,
        JSON.stringify({ revision: state.revision, decisions }),
      );
  }, [dirty, state, decisions, draftKey]);
  const working = ["queued", "analyzing", "rendering"].includes(p.status);
  function change(id: string, patch: Partial<Decision>) {
    editing.current = true;
    setDirty(true);
    setDecisions((ds) => ds.map((d) => (d.id === id ? { ...d, ...patch } : d)));
  }
  async function save() {
    if (!state) return;
    setBusy(true);
    setError("");
    try {
      const s = await request(
        "/studio/projects/" + p.id + "/plan",
        body({ revision: state.revision, decisions }, "PUT"),
      );
      setState(s);
      setDecisions(s.decisions);
      editing.current = false;
      setDirty(false);
      sessionStorage.removeItem(draftKey);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function render() {
    if (!state) return;
    setBusy(true);
    setError("");
    try {
      await request(
        "/studio/projects/" + p.id + "/render",
        body({ revision: state.revision }),
      );
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function retry() {
    setBusy(true);
    try {
      await request("/projects/" + p.id + "/retry", { method: "POST" });
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function seek(n: number) {
    pendingSeek.current = n;
    if (mode === "source" && video.current && video.current.readyState >= 1) {
      video.current.currentTime = n;
      pendingSeek.current = null;
    }
    setMode("source");
    video.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  const stages: Record<string, string> = {
    queued: t("Queued", "排队中"),
    preparing: t("Preparing your footage", "准备自有素材"),
    reference_analysis: t("Analyzing reference techniques", "分析参考视频"),
    director_planning: t("Building your Director Timeline", "创建剪辑计划"),
    render_queued: t("Render queued", "等待制作"),
    creating: t("Preparing the cut", "准备剪辑"),
    rendering: t("Rendering", "制作中"),
    checking: t("Reviewing quality", "质量复核"),
  };
  return (
    <div className="page director-project">
      <button
        className="text-button"
        onClick={() => {
          if (
            !dirty ||
            window.confirm(t("Discard unsaved changes?", "放弃未保存的修改？"))
          ) {
            sessionStorage.removeItem(draftKey);
            onBack();
          }
        }}
      >
        ← {t("Projects", "项目库")}
      </button>
      <header className="director-project-header">
        <div>
          <span className="eyebrow">DIRECTOR STUDIO</span>
          <h1>{p.title}</h1>
          <p>
            {t(
              "Owned footage · references are used for techniques only",
              "自有素材 · 参考视频仅用于分析创作方法",
            )}
          </p>
        </div>
        {p.result && (
          <a
            className="primary"
            href={`/api/projects/${p.id}/media/result`}
            download
          >
            {t("Download master", "下载主版本")}
          </a>
        )}
      </header>
      {error && (
        <p className="error-box" role="alert">
          {message(error, lang)}{" "}
          <button onClick={() => setError("")}>{t("Dismiss", "关闭")}</button>
        </p>
      )}
      <div className="director-layout">
        <section className="director-player">
          <div className="director-tabs">
            <button
              aria-pressed={mode === "source"}
              onClick={() => setMode("source")}
            >
              {t("Owned source", "自有原片")}
            </button>
            <button
              disabled={!p.result}
              aria-pressed={mode === "result"}
              onClick={() => setMode("result")}
            >
              {t("Master preview", "主版本预览")}
            </button>
          </div>
          {p.metadata?.preview_ready ? (
            <video
              key={
                p.id + mode + (mode === "result" ? p.result?.metadata.size : "")
              }
              ref={video}
              controls
              playsInline
              src={`/api/projects/${p.id}/media/${mode}`}
              onLoadedMetadata={() => {
                if (
                  mode === "source" &&
                  video.current &&
                  pendingSeek.current !== null
                ) {
                  video.current.currentTime = pendingSeek.current;
                  pendingSeek.current = null;
                }
              }}
              onError={() => setError("media_error")}
            />
          ) : (
            <p className="director-placeholder">
              {t("Preparing your video preview…", "正在准备预览…")}
            </p>
          )}
          {!working && !p.error && <p><StatusBadge status={p.status}>{p.status==='complete'?t('Completed successfully','已成功完成'):p.status==='needs_review'?t('Video created — review required','视频已生成 — 需要审核'):t('Analysis complete — review decisions','分析已完成 — 请审核决策')}</StatusBadge></p>}
          {working && (
            <TaskProgress title={stages[p.stage] || t("Processing", "处理中")} percent={p.progress} detail={t("Your source is saved. This page updates automatically.","原片已保存，页面会自动更新。")}/>
          )}
          {p.error && (
            <div role="alert" className="task-state-panel">
              <StatusBadge status="failed">{t("Failed — action needed","失败 — 需要处理")}</StatusBadge>
              <p>{message(p.error, lang)}</p>
              {!p.analysis && (
                <button className="secondary" onClick={retry} disabled={busy}>
                  {t("Retry analysis", "重新分析")}
                </button>
              )}
            </div>
          )}
          <div className="director-spend">
            <strong>
              ${p.cost.toFixed(3)} / ${p.budget.toFixed(2)}
            </strong>
            <span>
              {t(
                "AI usage / limit · reservations included",
                "AI 用量 / 上限 · 含预留费用",
              )}
            </span>
            <span>
              {t("Remaining", "剩余额度")}: $
              {Math.max(0, p.budget - p.cost).toFixed(2)}
            </span>
          </div>
          {p.result && (
            <section className="director-result">
              <h2>{t("Master review", "主版本复核")}</h2>
              {state && p.result.plan_revision !== state.revision && <p role="status">{t("This master belongs to an earlier plan. Review and render the updated plan to include your changes.","此主版本来自旧计划。请审核并制作更新后的计划以应用改动。")}</p>}
              <p>
                {p.result.qa_status === "passed"
                  ? t(
                      "AI review passed — check the final cut yourself.",
                      "AI 复核通过，请亲自检查成片。",
                    )
                  : t("This cut needs human review.", "此版本需要人工复核。")}
              </p>
              {p.result.quality_score!==undefined&&<p><strong>{t('AI editorial score','AI 编辑评分')}: {p.result.quality_score}/100</strong> · {t('Review target: 75. This is not an engagement prediction.','审核目标：75。此分数不预测传播效果。')}</p>}
              {p.result.qa?.scores?.map(score=><p key={score.category}>{score.category}: {score.value}/100 · {score.reason[lang]}</p>)}
              {p.result.qa?.revisions?.map((revision,i)=><p key={`revision-${i}`}><strong>{t('Suggested correction','建议修改')}:</strong> {revision[lang]}</p>)}
              {p.result.quality_comparison&&<section className="director-card"><h3>{t('Compared with the previous render','与上一版成片比较')}</h3>{p.result.quality_comparison.comparable?<><p><strong>{p.result.quality_comparison.previous_score} → {p.result.quality_comparison.current_score}/100</strong> · {t('Score change','评分变化')}: {(p.result.quality_comparison.delta||0)>0?'+':''}{p.result.quality_comparison.delta}</p><table><thead><tr><th>{t('Criterion','指标')}</th><th>{t('Previous','上一版')}</th><th>{t('Current','当前版')}</th><th>{t('Change','变化')}</th></tr></thead><tbody>{p.result.quality_comparison.categories?.map(c=><tr key={c.category}><td>{({hook:t('Hook','吸引力'),clarity:t('Clarity','清晰度'),pacing:t('Pacing','节奏'),visuals:t('Visuals','画面'),audio:t('Audio','声音')} as Record<string,string>)[c.category]||c.category}</td><td>{c.previous}</td><td>{c.current}</td><td style={{color:c.delta<0?'#9d2626':c.delta>0?'#166039':undefined}}>{c.delta>0?'+':''}{c.delta}</td></tr>)}</tbody></table>{!!p.result.quality_comparison.regressions?.length&&<p>{t('Some criteria scored lower. Check them before approving this version.','部分指标评分下降，请在批准此版本前检查。')}</p>}<small>{t('Separate AI reviews can vary. A higher score is not proof of a better edit or a prediction of engagement.','独立 AI 评估可能存在波动。更高评分不证明剪辑更好，也不预测传播效果。')}</small></>:<p>{t('Scores cannot be compared: one review is missing, or the evaluator/rubric is different or unknown.','无法比较评分：某版缺少评估，或评估模型、标准不同或未知。')}</p>}</section>}
              {p.result.quality_revision_id&&<p>{t('An improvement draft has been requested. Review it in Editing decisions from your Video DNA.','已请求生成改进草案，请在基于视频 DNA 的剪辑决策中审核。')}</p>}
              {p.result.quality_revision_blocked&&<p>{t('Drafting was skipped because decisions are locked or the plan changed. Review suggestions remain available.','因决策已锁定或计划已更改，未自动生成草案。您仍可查看改进建议。')}</p>}
              {p.result.qa?.issues.map((x, i) => (
                <p key={i}>{x[lang]}</p>
              ))}
              <ul>
                {p.result.applied.map((id) => (
                  <li key={id}>
                    {(p.result?.plan_revision === state?.revision ? state?.plan?.recommendations.find((r) => r.id === id)?.title[lang] : null) || id}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </section>
        <section className="director-inspector">
          <nav
            className="director-tabs"
            aria-label={t("Project sections", "项目内容")}
          >
            {[
              ["plan", t("Director Timeline", "剪辑计划")],
              ["manual", t("Manual editor", "手动剪辑")],
              ["dna", "Video DNA"],
              ["profile", t("Creator profile", "创作者风格")],
              ["platforms", t("Platform versions", "平台版本")],
            ].map(([key, label]) => (
              <button
                key={key}
                aria-pressed={section === key}
                onClick={() => setSection(key)}
              >
                {label}
              </button>
            ))}
          </nav>
          {!state ? (
            <p role="status">{t("Loading…", "加载中…")}</p>
          ) : section === "manual" ? (
            state.plan ? <ManualEditor hasAudio={p.metadata?.has_audio??false} pid={p.id} lang={lang} outputLanguage={p.language} duration={p.metadata?.duration||1} ratio={(p.metadata?.width||9)/(p.metadata?.height||16)} disabled={dirty||working||busy} onSaved={async()=>{const s=await request('/studio/projects/'+p.id);setState(s);setDecisions(s.decisions);await onRefresh();}} /> : <p className="director-card">{t("The manual editor becomes available when analysis is complete.","分析完成后即可使用手动剪辑。")}</p>
          ) : section === "profile" ? (
            <div className="director-card">
              <h2>{t("Creator profile", "创作者风格")}</h2>
              <dl>
                <dt>{t("Topic", "主题")}</dt>
                <dd>
                  {
                    (
                      {
                        real_estate: t("Real estate", "房地产"),
                        citizenship: t("Citizenship abroad", "海外国籍"),
                        travel: t("Travel", "旅行"),
                      } as Record<string, string>
                    )[state.context.creator.topic]
                  }
                </dd>
                <dt>{t("Audience", "受众")}</dt>
                <dd>{state.context.creator.audience}</dd>
                <dt>{t("Tone", "语气")}</dt>
                <dd>{state.context.creator.tone}</dd>
                <dt>{t("Rules", "规则")}</dt>
                <dd>{state.context.creator.rules || "—"}</dd>
                <dt>{t("Script", "脚本")}</dt>
                <dd>{p.brief}</dd>
              </dl>
            </div>
          ) : section === "platforms" ? (
            <PlatformVariants p={p} lang={lang} />
          ) : section === "dna" ? (
            <div>
              {state.context.references.map((r) => {
                const dna = state.dna.find(
                  (d) => d.reference_id === r.aweme_id,
                );
                return (
                  <article className="director-card" key={r.aweme_id}>
                    <h2>{r.title}</h2>
                    <a href={r.share_url} target="_blank" rel="noreferrer">
                      {r.author} ↗
                    </a>
                    {dna ? (
                      <>
                        <video
                          controls
                          playsInline
                          preload="none"
                          src={`/api/studio/projects/${p.id}/references/${r.aweme_id}`}
                        />
                        <p>{dna.analysis.summary[lang]}</p>
                        {dna.analysis.shots.map((s, i) => (
                          <details key={i}>
                            <summary>
                              {s.start.toFixed(1)}–{s.end.toFixed(1)}s ·{" "}
                              {s.observation[lang]}
                            </summary>
                            <p>{s.reusable_method[lang]}</p>
                            {Object.entries(s)
                              .filter(
                                ([k, v]) =>
                                  ![
                                    "start",
                                    "end",
                                    "observation",
                                    "reusable_method",
                                  ].includes(k) &&
                                  v &&
                                  typeof v === "object",
                              )
                              .map(([k, v]) => (
                                <p key={k}>
                                  <strong>
                                    {
                                      (
                                        {
                                          visual_type: t("Visual", "画面类型"),
                                          narrative_role: t(
                                            "Narrative role",
                                            "叙事作用",
                                          ),
                                          motion: t("Motion", "运动"),
                                          transition: t("Transition", "转场"),
                                          subtitle_emphasis: t(
                                            "Captions",
                                            "字幕重点",
                                          ),
                                          music: t("Music", "音乐"),
                                          emotion: t("Emotion", "情绪"),
                                          information_density: t(
                                            "Information density",
                                            "信息密度",
                                          ),
                                        } as Record<string, string>
                                      )[k]
                                    }
                                  </strong>
                                  : {(v as Text)[lang]}
                                </p>
                              ))}
                          </details>
                        ))}
                        {dna.analysis.uncertainties.map((v, i) => (
                          <p key={i}>{v[lang]}</p>
                        ))}
                      </>
                    ) : (
                      <p>
                        {t("Reference analysis pending", "参考分析尚未完成")}
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
          ) : (
            <div>
              <header className="director-card">
                <h2>{t("Review before rendering", "制作前审核")}</h2>
                <p>
                  {t(
                    "All times below refer to your owned footage. Approve changes, adjust their ranges, and lock decisions you want to preserve. Unlock and save before changing a locked decision.",
                    "以下时间均对应您的自有视频。批准改动、调整时间范围，并锁定需要保留的决策。修改锁定项前，请先解锁并保存。",
                  )}
                </p>
              </header>
              {!state.plan ? (
                <p role="status">
                  {t(
                    "The editable plan appears after reference and owned-footage analysis.",
                    "参考与自有素材分析完成后，将显示可编辑计划。",
                  )}
                </p>
              ) : (
                <>
                  <div className="director-card"><p>{state.plan.summary[lang]}</p><button className="secondary" onClick={()=>setSection("manual")}>{t("Open Director Timeline", "打开导演时间线")}</button></div>
                  <CreativePlan onSave={dirty&&!working&&!busy?save:undefined} disabledReason={dirty?t("Save your plan changes to continue.","请先保存计划更改。") : t("Wait for the current task to finish.","请等待当前任务完成。")} initialStyle={state.context.creator.style} pid={p.id} revision={state.revision} lang={lang} disabled={dirty||working||busy} onApplied={async()=>{const s=await request('/studio/projects/'+p.id);setState(s);setDecisions(s.decisions);setSection('manual');await onRefresh();}} />
                  <details className="cleanup-controls"><summary>{t('Additional cleanup controls','更多基础调整')}</summary>
                  <DirectorAlternatives onSave={dirty&&!working&&!busy?save:undefined} pid={p.id} revision={state.revision} recs={state.plan.recommendations} locked={decisions.filter(d=>d.locked).map(d=>d.id)} disabled={dirty||working||busy} lang={lang} onApplied={async()=>{const s=await request("/studio/projects/"+p.id);setState(s);setDecisions(s.decisions);await onRefresh();}} />
                  {state.plan.recommendations.length === 0 && (
                    <p className="director-card">
                      {t(
                        "No useful executable changes were identified. Your footage has not been changed.",
                        "未找到有价值的可执行改动。您的素材未被修改。",
                      )}
                    </p>
                  )}
                  {state.plan.recommendations.map((r) => {
                    const d = decisions.find((x) => x.id === r.id);
                    if (!d) return null;
                    const transfer = state.plan?.transfers.find(
                      (x) => x.recommendation_id === r.id,
                    );
                    return (
                      <article
                        className="director-card director-decision"
                        key={r.id}
                      >
                        <h3>{r.action==="normalize_audio"?t("Normalize overall audio loudness","统一整体音量"):r.title[lang]}</h3>
                        <p>{r.action==="normalize_audio"?t("Adjusts overall mixed-track loudness. Does not separate or rebalance voice and music.","调整混合音轨的整体音量，不分离或重新平衡人声与音乐。"):r.improvement[lang]}</p>
                        <p>
                          <strong>
                            {t("Evidence in your footage", "自有素材依据")}:
                          </strong>{" "}
                          {r.evidence[lang]}
                        </p>
                        {transfer && (
                          <details>
                            <summary>
                              {t(
                                "Why this reference technique fits",
                                "为什么采用此参考方法",
                              )}
                            </summary>
                            <p>{transfer.method[lang]}</p>
                            <p>{transfer.fit[lang]}</p>
                            <a
                              href={
                                state.context.references.find(
                                  (x) => x.aweme_id === transfer.reference_id,
                                )?.share_url
                              }
                              target="_blank"
                              rel="noreferrer"
                            >
                              {t("Reference", "参考")} ·{" "}
                              {transfer.reference_start}–
                              {transfer.reference_end}s ↗
                            </a>
                          </details>
                        )}
                        {["captions", "normalize_audio"].includes(r.action) && (
                          <p>
                            {t(
                              "Applies to the entire clip.",
                              "应用于整段视频。",
                            )}
                          </p>
                        )}
                        <div className="decision-controls">
                          <label>
                            {t("Start (s)", "开始（秒）")}
                            <input
                              type="number"
                              step="0.1"
                              min={0}
                              max={p.metadata?.duration}
                              value={d.start}
                              disabled={
                                d.locked ||
                                working ||
                                busy ||
                                ["captions", "normalize_audio"].includes(
                                  r.action,
                                )
                              }
                              onChange={(e) =>
                                change(d.id, { start: Number(e.target.value) })
                              }
                            />
                          </label>
                          <label>
                            {t("End (s)", "结束（秒）")}
                            <input
                              type="number"
                              step="0.1"
                              min={0}
                              max={p.metadata?.duration}
                              value={d.end}
                              disabled={
                                d.locked ||
                                working ||
                                busy ||
                                ["captions", "normalize_audio"].includes(
                                  r.action,
                                )
                              }
                              onChange={(e) =>
                                change(d.id, { end: Number(e.target.value) })
                              }
                            />
                          </label>
                          <button
                            className="secondary"
                            onClick={() => seek(d.start)}
                          >
                            {t("View moment", "查看片段")}
                          </button>
                        </div>
                        <label className="director-check">
                          <input
                            type="checkbox"
                            checked={d.approved}
                            disabled={d.locked || working || busy}
                            onChange={(e) =>
                              change(d.id, { approved: e.target.checked })
                            }
                          />
                          {t("Approve this change", "批准此改动")}
                        </label>
                        <label className="director-check">
                          <input
                            type="checkbox"
                            checked={d.locked}
                            disabled={!d.approved || working || busy}
                            onChange={(e) =>
                              change(d.id, { locked: e.target.checked })
                            }
                          />
                          {t("Lock this decision", "锁定此决策")}
                        </label>
                      </article>
                    );
                  })}
                  <footer className="director-submit">
                    <span>
                      {decisions.filter((x) => x.approved).length}{" "}
                      {t("approved", "项已批准")} · {t("Revision", "版本")}{" "}
                      {state.revision}
                      {dirty && ` · ${t("Unsaved changes", "尚未保存")}`}
                    </span>
                    <button
                      className="secondary"
                      disabled={!dirty || busy || working}
                      onClick={save}
                    >
                      {t("Save plan", "保存计划")}
                    </button>
                    <button
                      className="primary"
                      disabled={
                        dirty ||
                        busy ||
                        working ||
                        !decisions.some((x) => x.approved)
                      }
                      onClick={render}
                    >
                      {t("Render approved plan", "制作已批准计划")}
                    </button>
                  </footer>
                  <p className="director-note">
                    {t(
                      "Rendering uses owned footage only. AI quality review reserves up to $0.50; the project limit still applies.",
                      "制作仅使用自有素材。AI 质量复核最多预留 $0.50，仍受项目总额度限制。",
                    )}
                  </p>
                  </details>
                </>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
