import {PlanRenderReview} from './PlanRenderReview';
import {useWorkspace, workspaceText} from './ProjectWorkspace';
import { translate, contentLanguage } from './locale';
import { Dubbing } from './Dubbing';
import {CreatorStyle,defaultStyle,type Style} from './CreatorStyle';
import {StatusBadge,TaskProgress,UploadProgress} from './TaskStatus';
import {CreativePlan} from './CreativePlan';
import {holdUpload, uploadVideo} from './resumableUpload';
import {readBoard} from './look';
import {ManualEditor} from './ManualEditor';
import { DirectorAlternatives } from "./DirectorAlternatives";
import { PlatformVariants } from "./PlatformVariants";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
  style_match_off: ["Automatic style match is off for this project.", "此项目未开启自动风格匹配。"],
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
  return translate(lang, ...(labels[code] || [
    "The operation failed. Try again; your source is preserved.",
    "操作失败，请重试。原始素材已保留。",
  ]) as [string, string]);
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
  const t = (en: string, cn: string) => translate(lang, en, cn);
  const cache = "lumen-reference-draft:" + userKey;
  const [refs, setRefs] = useState<Hit[]>(() => {
    try {
      return JSON.parse(sessionStorage.getItem(cache) || "[]");
    } catch {
      return [];
    }
  });
  const [file, setFile] = useState<File | null>(null),
    [referenceFile, setReferenceFile] = useState<File | null>(null),
    [lookSaved, setLookSaved] = useState(() => readBoard() !== null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [percent, setPercent] = useState(0),
    [paused,setPaused] = useState(false);
  const [style,setStyle]=useState<Style>(defaultStyle);
  const [transfer,setTransfer]=useState<{bytes:number;total:number;mbps:number}|null>(null);
  const xhr = useRef<AbortController | null>(null);
  const requestId = useRef(crypto.randomUUID().replaceAll("-", ""));
  const [handoff] = useState<{ concept_id: string; title: string; script: string; trend: string } | null>(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem("lumen-trend-handoff") || "null");
      return saved?.concept_id ? saved : null;
    } catch {
      return null;
    }
  });
  useEffect(() => {
    sessionStorage.setItem(cache, JSON.stringify(refs));
  }, [cache, refs]);
  useEffect(() => {
    const sync = () => setLookSaved(readBoard() !== null);
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
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
    if (!file || (!refs.length && !referenceFile)) return;
    setError("");
    if (file.size > 250 * 1024 * 1024 || (referenceFile && referenceFile.size > 250 * 1024 * 1024)) {
      setError("upload_too_large");
      return;
    }
    const f = new FormData(e.currentTarget);
    setBusy(true);setPaused(false);setPercent(0);setTransfer(null);
    const controller=new AbortController();xhr.current=controller;
    let referenceUpload = "";
    try {
      if (referenceFile) referenceUpload = await holdUpload(referenceFile, controller.signal);
    } catch (err) {
      const code = err instanceof Error ? err.message : "upload_interrupted";
      if (code === "upload_cancelled") setPaused(true); else setError(code);
      setBusy(false);
      return;
    }
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
      style_match: f.has("style_match") || Boolean(referenceUpload),
      ...((f.has("style_match") || referenceUpload) && readBoard() ? { effect_board: readBoard() } : {}),
      ...(referenceUpload ? { reference_upload_id: referenceUpload } : {}),
      ...(handoff ? { concept_id: handoff.concept_id } : {}),
    };
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
        <span className="eyebrow">{translate(lang, "LUMEN / DIRECTOR STUDIO", "LUMEN / DIRECTOR STUDIO")}</span>
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
      {handoff && (
        <p className="director-note">
          {t(
            "This project starts from a trend. The script is a new structure, not the reference video. New project clears it.",
            "这个项目从趋势开始。脚本是新的结构，不是参考视频。新建项目会清除它。",
          )}{" "}
          {handoff.trend}
        </p>
      )}
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
              <input name="title" required maxLength={120} defaultValue={handoff?.title || ""} />
            </label>
            <label>
              {t("Script & intended message", "脚本与核心信息")}
              <textarea
                name="script"
                required
                maxLength={6000}
                rows={4}
                defaultValue={handoff?.script || ""}
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
            <label>
              {t("Reference video", "参考视频")}
              <input
                className="director-file-input"
                type="file"
                accept="video/mp4,video/quicktime,video/webm,.mov"
                onChange={(e) => setReferenceFile(e.target.files?.[0] || null)}
              />
              <small>
                {referenceFile
                  ? referenceFile.name
                  : t("Upload the reference video. The finished film still uses only your footage.", "上传参考视频。成片仍然只用你的素材。")}
              </small>
            </label>
            <label className="director-check">
              <input name="style_match" type="checkbox" />
              {t(
                "Match the reference pacing and the visual effects this editor can reproduce, then render. You still approve the result and can edit every cut.",
                "按该参考的节奏和本编辑器可实现的视觉效果制作成片。你仍需批准结果，也可以修改每一处剪辑。",
              )}
            </label>
            <p className="look-create-note">
              <button type="button" className="secondary" onClick={() => { window.location.hash = "look"; }}>
                {t("Open the visual effect plaque", "打开视觉效果面板")}
              </button>
              {lookSaved && (
                <small>{t("Saved on this device. Style match on the next project uses this plaque.", "已保存在此设备。下一个项目的风格匹配会使用这个面板。")}</small>
              )}
            </p>
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
                <select name="language" defaultValue={contentLanguage(lang)}>
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
            <button className="primary" disabled={!file || (!refs.length && !referenceFile)}>
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
type StyleReport = {
  scores: Record<string, number>;
  applied: string[];
  gaps: { id: string; essential: boolean }[];
  sections: { index: number; start: number; end: number }[];
  compared?: boolean;
  effect_similarity_rule?: number;
  measured_effect_similarity?: number;
  comparison_note?: string;
};

function StyleMatch({
  pid,
  lang,
  report,
  status,
  plaque,
  locked,
  working,
  onDone,
}: {
  pid: string;
  lang: Lang;
  report?: StyleReport | null;
  status?: string;
  plaque?: boolean;
  locked: boolean;
  working: boolean;
  onDone: () => Promise<void>;
}) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const [section, setSection] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(path: string) {
    setError("");
    setBusy(true);
    try {
      await request(path, { method: "POST" });
      await onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function appliedLine(id: string) {
    if (id === "cuts") return t("The owned video was cut to the reference rhythm.", "已按参考节奏切开你的视频。");
    if (id === "trimmed") return t("Unusable sections that do not cut through speech were removed.", "已去掉不切断语音的无用片段。");
    if (id === "framing") return t("Crop, punch-in and camera moves follow the reference.", "裁切、推近和运镜跟随参考。");
    if (id === "zoom") return t("Zoom and punch-in were applied where the reference uses them.", "参考使用了推近的地方已加上变焦。");
    if (id === "callouts") return t("Short labels use words from your own speech.", "短标签使用你自己语音里的词。");
    if (id === "cards") return t("Charts and number cards use figures from your script.", "图表和数字卡使用你脚本里的数字。");
    if (id === "cutaway") return t("A cutaway uses another moment of your own footage.", "插入镜头使用你素材里的另一个片段。");
    if (id === "emphasis") return t("Numbers and keywords from your speech are highlighted.", "你语音里的数字和关键词已突出显示。");
    if (id === "enhance") return t("Exposure and color were lifted slightly. The reference grade was not copied.", "曝光和色彩略作提升。没有复制参考的调色。");
    if (id === "grade") return t("Color was shifted toward the reference measurement.", "色彩已按参考测量值调整。");
    if (id === "speed") return t("Short reference beats play with a speed change.", "参考里的短镜头用了变速。");
    if (id === "blur") return t("Blur was applied where the reference uses it.", "参考使用模糊的地方已加上模糊。");
    if (id === "glow") return t("A light glow was applied.", "已加上轻微发光。");
    if (id === "shadow") return t("A vignette shadow was applied.", "已加上暗角。");
    if (id === "split") return t("The frame was split into two panels.", "画面分成了两栏。");
    if (id === "stabilize") return t("The shot was stabilized.", "镜头已做防抖。");
    if (id === "cutout") return t("A flat background was separated and softened.", "纯色背景已分离并柔化。");
    if (id === "kinetic") return t("The on-screen label moves across the frame.", "屏幕文字会在画面中移动。");
    if (id === "track") return t("The frame follows where the detail moves.", "画面跟着细节移动。");
    if (id === "mask") return t("The presenter sits in a soft window over a clean plate.", "主讲人位于干净底板上的柔和窗口中。");
    if (id === "exposure") return t("Exposure was shifted toward the reference measurement.", "曝光已按参考测量值调整。");
    if (id === "progress") return t("A progress bar follows the position in the cut.", "进度条跟着成片的位置走。");
    if (id === "illustration") return t("A title-like reference shot is replaced by a chart of your figures, fading in and out.", "参考里的标题镜头换成了你的数字图，淡入再淡出。");
    if (id === "lower") return t("A lower band fades in and out over the presenter.", "下沿条带在主讲人画面上淡入再淡出。");
    if (id === "icon") return t("A small mark fades in and out on that band.", "这条带上的小标记会淡入再淡出。");
    if (id === "still") return t("A title-like shot with no figures holds another frame of your footage, then lets it go.", "没有数字的标题镜头会定格你素材里的另一帧，然后再放开。");
    if (id === "screen") return t("A screen-like reference shot holds your frame inside a border, then lets it go.", "像屏幕的参考镜头会把你的画面放进边框，然后再放开。");
    if (id === "diagram") return t("An illustration of equal shapes is drawn from your words and fades out.", "根据你的词语画出等大图形，然后淡出。");
    if (id === "art") return t("One generated picture uses your words. It has no text from the reference.", "生成的一张图只用你的词语，不含参考视频里的文字。");
    if (id === "stock") return t("A Commons clip with a CC BY, CC0, or public-domain license was inserted. Its credit stays on the asset.", "已插入一条 CC BY、CC0 或公有领域的 Commons 视频，署名保留在素材上。");
    if (id === "panel") return t("The other half of a split frame is another moment of your footage.", "分屏的另一半是你视频的另一个时刻。");
    if (id === "transitions") return t("Cuts, fades, dissolves, wipes and circle transitions follow the reference.", "切、淡入、叠化、擦除和圆形转场跟随参考。");
    if (id === "captions") return t("Owned speech was burned as captions.", "已烧录你自己的语音字幕。");
    if (id === "normalize") return t("Audio level was normalized.", "已均衡音量。");
    if (id === "no_captions") return t("No owned captions were added.", "没有添加你自己的字幕。");
    return id;
  }
  function gapLine(id: string) {
    if (id === "motion_tracking") return t("Face tracking is not available. The frame follows a moving bright area when one is measured.", "无法跟踪人脸。测到移动的亮区时，画面会跟着它。");
    if (id === "presenter_cutout") return t("Presenter cutout is not available.", "无法抠出主讲人。");
    if (id === "background_replacement") return t("Background replacement is not available.", "无法替换背景。");
    if (id === "speed_ramp") return t("Speed ramps are not available.", "无法做速度渐变。");
    if (id === "mask") return t("Masks are not available.", "无法使用蒙版。");
    if (id === "split_screen") return t("Split screen is not available.", "无法做分屏。");
    if (id === "color_grade") return t("Automatic color and lighting match is not available.", "无法自动匹配色彩和光线。");
    if (id === "kinetic_type") return t("Kinetic typography is not cloned. Owned captions are used when speech exists.", "不会复制动态标题。有语音时使用你自己的字幕。");
    if (id === "number_card") return t("A chart or number card needs the figure and its label from you. Nothing was invented.", "图表或数字卡需要你提供数字和标签。系统不会编造。");
    if (id === "broll") return t("No Commons clip with a CC BY, CC0, or public-domain license matched your words.", "没有找到与你的词语匹配、且为 CC BY、CC0 或公有领域的 Commons 视频。");
    if (id === "captions_need_speech") return t("Captions need a speech transcript from your video.", "字幕需要你视频里的语音文本。");
    if (id === "reference_music") return t("Reference music was not copied.", "没有复制参考视频的音乐。");
    if (id === "blur") return t("Blur is not available.", "无法做模糊。");
    if (id === "glow") return t("Glow is not available.", "无法做发光。");
    if (id === "shadow") return t("Drop shadows are not available.", "无法做投影。");
    if (id === "stabilize") return t("Stabilization is not available.", "无法做防抖。");
    if (id === "style_match_failed") return t("The automatic cut could not be built. Regenerate video to try again.", "未能自动生成剪辑。请重新生成视频。");
    return id;
  }
  const title = t("Automatic style match", "自动风格匹配");
  if (!report) {
    return (
      <details className="style-match-fold">
        <summary>{title}</summary>
        <div className="style-match-body">
          <p>{t("Style match starts when analysis finishes.", "分析完成后开始风格匹配。")}</p>
        </div>
      </details>
    );
  }
  return (
    <details className="style-match-fold">
      <summary>
        {title}
        <strong>{report.scores.overall}/100</strong>
      </summary>
      <div className="style-match-body">
      <p>
        <strong>{report.scores.overall}/100</strong>{" "}
        {report.compared === true && report.measured_effect_similarity != null
          ? t(
              "Effect similarity averages the rule score with the measured frames. It is not a copy of the reference. Unsupported effects are listed and are not imitated. The cut uses your footage only.",
              "效果相似度是规则分和画面测量的平均。这不是参考视频的副本。无法实现的效果会列出，不会被模仿。成片只用你的素材。",
            )
          : t(
              "These scores follow the edit rules. A score of 100 is not a picture match. Frames have not been compared yet. Unsupported effects are listed and are not imitated. The cut uses your footage only.",
              "这些分数遵循剪辑规则。100 分不是画面核对。尚未比较画面。无法实现的效果会列出，不会被模仿。成片只用你的素材。",
            )}
      </p>
      <p>
        {t(
          "Approve renders the saved edit with the voice and music you selected. It does not publish the video, and it does not copy the reference. The editor stays on this page.",
          "批准会渲染已保存的剪辑，并带上你选的声音和音乐。它不会发布视频，也不会复制参考视频。编辑器仍留在此页。",
        )}
      </p>
      {status === "approved" && <p>{t("The saved edit was sent to render. Nothing was published, and the reference was not copied.", "已保存的剪辑已送去渲染。没有发布任何内容，也没有复制参考视频。")}</p>}
      {plaque && <p>{t("This cut follows your visual effect plaque.", "这个成片遵循你的视觉效果面板。")}</p>}
      <ul>
        <li>{t("Shot structure", "镜头结构")}: {report.scores.shot_structure}/100</li>
        <li>{t("Visual pacing", "视觉节奏")}: {report.scores.visual_pacing}/100</li>
        {report.compared === true && report.measured_effect_similarity != null ? (
          <li>
            {t("Effect similarity", "效果相似度")}: {report.scores.effect_similarity}/100
            {" · "}
            {t("Effect rule score", "效果规则分")}: {report.effect_similarity_rule ?? report.scores.effect_similarity}/100
            {" · "}
            {t("Frame measurement", "画面测量")}: {report.measured_effect_similarity}/100
          </li>
        ) : (
          <li>{t("Effect rule score", "效果规则分")}: {report.effect_similarity_rule ?? report.scores.effect_similarity}/100</li>
        )}
        <li>{t("Motion-graphic style", "动态图形风格")}: {report.scores.motion_graphic_style}/100</li>
        <li>{t("Color treatment", "色彩处理")}: {report.scores.color_treatment}/100</li>
        <li>{t("Production quality", "成片完成度")}: {report.scores.production_quality}/100</li>
      </ul>
      <ul>
        {report.applied.map((id) => (
          <li key={id}>{appliedLine(id)}</li>
        ))}
      </ul>
      {report.gaps.map((gap) => (
        <p key={gap.id}>
          {gap.essential ? t("Needs your input", "需要你补充") : t("Not reproduced", "未能复现")}
          : {gapLine(gap.id)}
        </p>
      ))}
      {error && (
        <p className="error-box" role="alert">
          {message(error, lang)}
        </p>
      )}
      <div className="trend-actions">
        <button type="button" className="primary" disabled={busy || working} onClick={() => void run(`/studio/projects/${pid}/style-match/approve`)}>
          {t("Approve this cut", "批准这个成片")}
        </button>
        <button type="button" className="secondary" disabled={busy || locked} onClick={() => void run(`/studio/projects/${pid}/style-match/regenerate`)}>
          {t("Regenerate video", "重新生成视频")}
        </button>
        {!!report.sections.length && (
          <label>
            {t("Section", "片段")}
            <select aria-label={t("Style section", "风格片段")} value={section} onChange={(e) => setSection(Number(e.target.value))}>
              {report.sections.map((item) => (
                <option key={item.index} value={item.index}>
                  {item.index + 1} · {item.start.toFixed(1)}–{item.end.toFixed(1)}s
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          type="button"
          className="secondary"
          disabled={busy || locked || !report.sections.length}
          onClick={() => void run(`/studio/projects/${pid}/style-match/sections/${section}/regenerate`)}
        >
          {t("Regenerate selected section", "重新生成所选片段")}
        </button>
      </div>
      </div>
    </details>
  );
}

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
    style_match?: boolean;
    style_report?: StyleReport | null;
    style_match_status?: string;
    effect_board?: { name?: string } | null;
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
  onRefresh,
}: {
  p: Project;
  lang: Lang;
  onBack: () => void;
  onRefresh: () => Promise<void>;
}) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const workspace=useWorkspace();
  const [manualDirty,setManualDirty]=useState(false);
  const manualTask=workspace && workspace.task!=="review";
  const w=(ru:string,en:string,zh:string)=>workspaceText(lang,ru,en,zh);
  const [state, setState] = useState<State | null>(null),
    [decisions, setDecisions] = useState<Decision[]>([]),
    [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [section, setSection] = useState("plan");
  const editing = useRef(false);
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
    if(manualDirty)return;
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
  function seek(start:number,end:number) { workspace?.seekSource(start,end); }
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
      {error && (
        <p className="error-box" role="alert">
          {message(error, lang)}{" "}
          <button onClick={() => setError("")}>{t("Dismiss", "关闭")}</button>
        </p>
      )}
      {lang === 'ru' && !manualTask && <p className="muted">{t('Generated analysis is displayed in English.','AI 分析文本以英语显示。')}</p>}
      <div className="director-layout">
        <section className="director-inspector">
          {state?.context.style_match && workspace?.styleTarget && createPortal(
            <StyleMatch
              pid={p.id}
              lang={lang}
              report={state.context.style_report}
              status={state.context.style_match_status}
              working={working}
              plaque={!!state.context.effect_board}
              locked={working || busy}
              onDone={async () => {
                const next = await request("/studio/projects/" + p.id);
                setState(next);
                await onRefresh();
              }}
            />,
            workspace.styleTarget,
          )}
          {state?.plan && <div hidden={!manualTask}><ManualEditor serverRevision={state.revision} onDirtyChange={setManualDirty} hasAudio={p.metadata?.has_audio??false} pid={p.id} lang={lang} outputLanguage={p.language} duration={p.metadata?.duration||1} ratio={(p.metadata?.width||9)/(p.metadata?.height||16)} disabled={dirty||working||busy} onSaved={async()=>{const s=await request('/studio/projects/'+p.id);setState(s);setDecisions(s.decisions);await onRefresh();}} voiceover={<Dubbing key={p.id} pid={p.id} lang={lang} masterId={p.result?.render_id} embedded onFinalChange={()=>workspace?.refreshFinal()} onPreview={(url,label)=>workspace?.previewVersion(url,label)}/>} /></div>}
          {manualTask&&!state?.plan&&<p role="status">{w('Инструменты станут доступны после анализа видео.','Tools become available after video analysis.','视频分析完成后即可使用工具。')}</p>}
          <div hidden={!!manualTask}>
          {manualDirty&&<p role="status">{w('Сначала сохраните правки в разделе «Монтаж».','Save your manual edits in Edit first.','请先在剪辑中保存手动更改。')}</p>}
          {working && <TaskProgress title={stages[p.stage] || t("Processing", "处理中")} percent={p.progress}/>}
          {p.error&&<div role="alert"><p>{message(p.error,lang)}</p>{!p.analysis&&<button onClick={retry} disabled={busy}>{t("Retry analysis","重新分析")}</button>}</div>}
          <details className="ws-quality"><summary>{w('Проверка готовой версии','Finished video review','成片审核')}</summary>
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
              {p.result.qa?.scores?.map(score=><p key={score.category}>{score.category}: {score.value}/100 · {score.reason[contentLanguage(lang)]}</p>)}
              {p.result.qa?.revisions?.map((revision,i)=><p key={`revision-${i}`}><strong>{t('Suggested correction','建议修改')}:</strong> {revision[contentLanguage(lang)]}</p>)}
              {p.result.quality_comparison&&<section className="director-card"><h3>{t('Compared with the previous render','与上一版成片比较')}</h3>{p.result.quality_comparison.comparable?<><p><strong>{p.result.quality_comparison.previous_score} → {p.result.quality_comparison.current_score}/100</strong> · {t('Score change','评分变化')}: {(p.result.quality_comparison.delta||0)>0?'+':''}{p.result.quality_comparison.delta}</p><table><thead><tr><th>{t('Criterion','指标')}</th><th>{t('Previous','上一版')}</th><th>{t('Current','当前版')}</th><th>{t('Change','变化')}</th></tr></thead><tbody>{p.result.quality_comparison.categories?.map(c=><tr key={c.category}><td>{({hook:t('Hook','吸引力'),clarity:t('Clarity','清晰度'),pacing:t('Pacing','节奏'),visuals:t('Visuals','画面'),audio:t('Audio','声音')} as Record<string,string>)[c.category]||c.category}</td><td>{c.previous}</td><td>{c.current}</td><td style={{color:c.delta<0?'#9d2626':c.delta>0?'#166039':undefined}}>{c.delta>0?'+':''}{c.delta}</td></tr>)}</tbody></table>{!!p.result.quality_comparison.regressions?.length&&<p>{t('Some criteria scored lower. Check them before approving this version.','部分指标评分下降，请在批准此版本前检查。')}</p>}<small>{t('Separate AI reviews can vary. A higher score is not proof of a better edit or a prediction of engagement.','独立 AI 评估可能存在波动。更高评分不证明剪辑更好，也不预测传播效果。')}</small></>:<p>{t('Scores cannot be compared: one review is missing, or the evaluator/rubric is different or unknown.','无法比较评分：某版缺少评估，或评估模型、标准不同或未知。')}</p>}</section>}
              {p.result.quality_revision_id&&<p>{t('An improvement draft has been requested. Review it in Editing decisions from your Video DNA.','已请求生成改进草案，请在基于视频 DNA 的剪辑决策中审核。')}</p>}
              {p.result.quality_revision_blocked&&<p>{t('Drafting was skipped because decisions are locked or the plan changed. Review suggestions remain available.','因决策已锁定或计划已更改，未自动生成草案。您仍可查看改进建议。')}</p>}
              {p.result.qa?.issues.map((x, i) => (
                <p key={i}>{x[contentLanguage(lang)]}</p>
              ))}
              <ul>
                {p.result.applied.map((id) => (
                  <li key={id}>
                    {(p.result?.plan_revision === state?.revision ? state?.plan?.recommendations.find((r) => r.id === id)?.title[contentLanguage(lang)] : null) || id}
                  </li>
                ))}
              </ul>
            </section>
          )}
          </details>
          <nav
            className="director-tabs"
            aria-label={t("Project sections", "项目内容")}
          >
            {[
              ["plan", t("Director Timeline", "剪辑计划")],
              ["dna", t("Video DNA", "视频 DNA")],
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
                        <p>{dna.analysis.summary[contentLanguage(lang)]}</p>
                        {dna.analysis.shots.map((s, i) => (
                          <details key={i}>
                            <summary>
                              {s.start.toFixed(1)}–{s.end.toFixed(1)}s ·{" "}
                              {s.observation[contentLanguage(lang)]}
                            </summary>
                            <p>{s.reusable_method[contentLanguage(lang)]}</p>
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
                                  : {(v as Text)[contentLanguage(lang)]}
                                </p>
                              ))}
                          </details>
                        ))}
                        {dna.analysis.uncertainties.map((v, i) => (
                          <p key={i}>{v[contentLanguage(lang)]}</p>
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
                  <div className="director-card"><p>{state.plan.summary[contentLanguage(lang)]}</p><button className="secondary" onClick={()=>workspace?.setTask("edit")}>{t("Open Director Timeline", "打开导演时间线")}</button></div>
                  <CreativePlan onSave={dirty&&!manualDirty&&!working&&!busy?save:undefined} disabledReason={dirty?t("Save your plan changes to continue.","请先保存计划更改。") : t("Wait for the current task to finish.","请等待当前任务完成。")} initialStyle={state.context.creator.style} pid={p.id} revision={state.revision} lang={lang} disabled={dirty||manualDirty||working||busy} onApplied={async()=>{const s=await request('/studio/projects/'+p.id);setState(s);setDecisions(s.decisions);workspace?.setTask('edit');await onRefresh();}} />
                  <details className="cleanup-controls"><summary>{t('Additional cleanup controls','更多基础调整')}</summary>
                  <DirectorAlternatives onSave={dirty&&!manualDirty&&!working&&!busy?save:undefined} pid={p.id} revision={state.revision} recs={state.plan.recommendations} locked={decisions.filter(d=>d.locked).map(d=>d.id)} disabled={dirty||manualDirty||working||busy} lang={lang} onApplied={async()=>{const s=await request("/studio/projects/"+p.id);setState(s);setDecisions(s.decisions);await onRefresh();}} />
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
                        <h3>{r.action==="normalize_audio"?t("Normalize overall audio loudness","统一整体音量"):r.title[contentLanguage(lang)]}</h3>
                        <p>{r.action==="normalize_audio"?t("Adjusts overall mixed-track loudness. Does not separate or rebalance voice and music.","调整混合音轨的整体音量，不分离或重新平衡人声与音乐。"):r.improvement[contentLanguage(lang)]}</p>
                        <p>
                          <strong>
                            {t("Evidence in your footage", "自有素材依据")}:
                          </strong>{" "}
                          {r.evidence[contentLanguage(lang)]}
                        </p>
                        {transfer && (
                          <details>
                            <summary>
                              {t(
                                "Why this reference technique fits",
                                "为什么采用此参考方法",
                              )}
                            </summary>
                            <p>{transfer.method[contentLanguage(lang)]}</p>
                            <p>{transfer.fit[contentLanguage(lang)]}</p>
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
                                manualDirty ||
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
                                manualDirty ||
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
                            onClick={() => seek(d.start,d.end)}
                          >
                            {t("View moment", "查看片段")}
                          </button>
                        </div>
                        <label className="director-check">
                          <input
                            type="checkbox"
                            checked={d.approved}
                            disabled={d.locked || manualDirty || working || busy}
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
                            disabled={!d.approved || manualDirty || working || busy}
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
                      disabled={!dirty || manualDirty || busy || working}
                      onClick={save}
                    >
                      {t("Save plan", "保存计划")}
                    </button>
                    <PlanRenderReview pid={p.id} revision={state.revision} lang={lang} disabled={dirty||manualDirty||busy||working||!decisions.some(x=>x.approved)} onRender={render}/>

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
          </div>
        </section>
      </div>
    </div>
  );
}
