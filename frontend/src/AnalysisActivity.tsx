import { useEffect, useState } from "react";
import { translate } from "./locale";
import type { AnalysisActivityState, Lang } from "./types";

type ActivityProject = {
  stage: string;
  progress: number;
  metadata: { activity?: AnalysisActivityState | null } | null;
};

function fallbackStep(stage?: string) {
  if (stage === "queued") return "queued";
  if (stage === "preparing") return "prepare";
  if (stage === "reference_analysis") return "reference_model";
  if (stage === "measuring_reference") return "reference_cuts";
  if (stage === "measuring_owned") return "owned_color";
  if (stage === "understanding") return "owned_model";
  if (stage === "planning" || stage === "director_planning") return "director";
  if (stage === "style_match") return "style_cut";
  return "";
}

function stepTitle(step: string, lang: Lang) {
  if (step === "queued") return translate(lang, "Waiting to start", "等待开始");
  if (step === "prepare") return translate(lang, "Reading the uploaded video", "正在读取上传的视频");
  if (step === "reference_fetch") return translate(lang, "Downloading the reference", "正在下载参考视频");
  if (step === "reference_model") return translate(lang, "The model is reading the reference", "模型正在阅读参考视频");
  if (step === "reference_cuts") return translate(lang, "Finding cuts in the reference", "正在查找参考视频的剪辑点");
  if (step === "reference_shots") return translate(lang, "Reading each reference shot", "逐个读取参考镜头");
  if (step === "reference_grade") return translate(lang, "Reading color in the reference", "正在读取参考视频的色彩");
  if (step === "owned_color") return translate(lang, "Reading color in your video", "正在读取您视频的色彩");
  if (step === "owned_sound") return translate(lang, "Finding pauses in your audio", "正在查找声音里的停顿");
  if (step === "owned_motion") return translate(lang, "Tracking motion in your video", "正在跟踪您视频中的运动");
  if (step === "owned_model") return translate(lang, "The model is watching your video", "模型正在观看您的视频");
  if (step === "director") return translate(lang, "Writing the edit plan", "正在编写剪辑方案");
  if (step === "style_cut") return translate(lang, "Building the styled picture", "正在生成风格化画面");
  return translate(lang, "Working on your video", "正在处理您的视频");
}

function partDetail(step: string, part: string | null | undefined, lang: Lang) {
  if (step === "queued") return translate(lang, "Your video is saved. A worker will pick it up.", "视频已保存。空闲的处理器会开始分析。");
  if (step === "prepare") return translate(lang, "Checking the file and preparing a preview.", "正在检查文件并准备预览。");
  if (step === "reference_fetch") return translate(lang, "The reference is saved before it is read.", "参考视频会先保存，再开始阅读。");
  if (step === "reference_model") return translate(lang, "Techniques are taken from the reference, not copied as footage.", "只提取参考手法，不复制参考画面。");
  if (step === "reference_cuts") return translate(lang, "The whole reference is scanned for shot changes.", "正在扫描整段参考视频里的镜头切换。");
  if (part === "frame") return translate(lang, "Color, blur, and light in this shot", "这个镜头的色彩、模糊和光线");
  if (part === "graphics") return translate(lang, "Graphics on this shot", "这个镜头上的图形");
  if (part === "motion") return translate(lang, "Speed and camera move", "速度和镜头运动");
  if (part === "type") return translate(lang, "Type and emphasis", "字体和强调");
  if (part === "places" && step === "reference_shots") return translate(lang, "Where titles and callouts sit", "标题和标注的位置");
  if (part === "color") return translate(lang, "Sampling color across the file", "正在整段采样色彩");
  if (part === "flat") return translate(lang, "Looking for a flat background", "正在查找纯色背景");
  if (step === "owned_color") return translate(lang, "Your picture is compared with the reference.", "正在把您的画面和参考视频比较。");
  if (step === "owned_sound") return translate(lang, "Silent stretches are measured. Speech on a usable frame stays.", "正在测量无声片段。有可用画面的讲话会保留。");
  if (part === "room") return translate(lang, "Finding the person in the frame", "正在查找画面中的人");
  if (part === "track") return translate(lang, "Following the face", "正在跟随面部");
  if (part === "gaps") return translate(lang, "Looking for black or frozen stretches", "正在查找黑场或静止画面");
  if (part === "light") return translate(lang, "Comparing light", "正在比较光线");
  if (part === "highlight") return translate(lang, "Marking the strongest moment", "正在标记最强的瞬间");
  if (part === "places") return translate(lang, "Reading how the reference is laid out", "正在读取参考视频的版式");
  if (step === "owned_motion") return translate(lang, "Tracking motion in your video", "正在跟踪您视频中的运动");
  if (step === "owned_model") return translate(lang, "Speech, scenes, and edit ideas are written from this file.", "语音、场景和剪辑想法都来自这个文件。");
  if (step === "director") return translate(lang, "The model turns what it saw into timed decisions.", "模型把看到的内容写成按时间排列的决定。");
  if (step === "style_cut") return translate(lang, "Measurements become the cut. Your footage stays the only picture.", "测量结果变成剪辑。成片画面仍然只用您的素材。");
  if (step === "reference_grade") return translate(lang, "Sampling color across the file", "正在整段采样色彩");
  return translate(lang, "This page updates every few seconds while the job runs.", "任务进行时，此页面每隔几秒更新一次。");
}

function renderTitle(stage: string | undefined, lang: Lang) {
  if (stage === "importing") return translate(lang, "Downloading from Douyin", "正在从抖音导入");
  if (stage === "render_queued") return translate(lang, "Your new cut is queued", "新版本已排队");
  if (stage === "creating") return translate(lang, "Preparing selected changes", "准备所选改动");
  if (stage === "rendering") return translate(lang, "Rendering the new cut", "渲染新版本");
  if (stage === "checking") return translate(lang, "Checking the finished video", "检查成片");
  return "";
}

function renderDetail(stage: string | undefined, lang: Lang) {
  if (stage === "importing") return translate(lang, "Lumen is retrieving the selected source. Analysis starts after the download is verified.", "正在获取所选原视频，下载验证完成后开始分析。");
  if (stage === "render_queued") return translate(lang, "The saved edit is waiting for the renderer.", "已保存的剪辑正在等待渲染。");
  if (stage === "creating") return translate(lang, "The cut is being prepared from your saved edit.", "正在根据已保存的剪辑准备成片。");
  if (stage === "rendering") return translate(lang, "Frames are being written. The previous finished video stays until this one succeeds.", "正在写出画面。上一版成片会保留，直到这一版成功。");
  if (stage === "checking") return translate(lang, "The finished file is being checked.", "正在检查成片文件。");
  return "";
}

export function activityTitle(activity: AnalysisActivityState | null | undefined, lang: Lang, stage?: string) {
  const rendered = renderTitle(stage, lang);
  if (rendered) return rendered;
  const step = activity?.step || fallbackStep(stage);
  if (step === "reference_shots" && activity?.total) {
    return translate(lang, "Reading reference shot {done} of {total}", "正在读取参考镜头 {done}/{total}")
      .replaceAll("{done}", String(activity.done || 0))
      .replaceAll("{total}", String(activity.total));
  }
  if (!step) return translate(lang, "Working on your video", "正在处理您的视频");
  return stepTitle(step, lang);
}

export function activityDetail(activity: AnalysisActivityState | null | undefined, lang: Lang, stage?: string) {
  const rendered = renderDetail(stage, lang);
  if (rendered) return rendered;
  const step = activity?.step || fallbackStep(stage);
  if (!step) return translate(lang, "This page updates every few seconds while the job runs.", "任务进行时，此页面每隔几秒更新一次。");
  return partDetail(step, activity?.part, lang);
}

function clock(lang: Lang, at?: number, now = Date.now()) {
  if (!at) return "";
  const seconds = Math.max(0, Math.floor(now / 1000 - at));
  const shown = seconds >= 60 ? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}` : `${seconds}s`;
  return translate(lang, "Running {time}", "已进行 {time}").replaceAll("{time}", shown);
}

export function AnalysisActivity({ project, lang }: { project: ActivityProject; lang: Lang }) {
  const activity = renderTitle(project.stage, lang) ? undefined : project.metadata?.activity;
  const step = activity?.step || fallbackStep(project.stage);
  const plan = activity?.plan || [];
  const done = new Set((activity?.log || []).map((row) => row.step));
  const current = plan.indexOf(step);
  const rows = plan.length
    ? plan.filter((id, index) => index === current || done.has(id) || (current >= 0 && index > current))
    : step
      ? [step]
      : [];
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const percent = Math.max(0, Math.min(100, project.progress || 0));
  const headline = activityTitle(activity, lang, project.stage);
  const detail = activityDetail(activity, lang, project.stage);
  const elapsed = clock(lang, activity?.at, now);
  return (
    <section className="analysis-activity" aria-label={translate(lang, "What is happening", "当前进度")}>
      <div className="analysis-activity-head">
        <div>
          <span className="analysis-activity-kicker">{translate(lang, "What is happening", "当前进度")}</span>
          <strong>{headline}</strong>
        </div>
        <b>{percent}%</b>
      </div>
      <div className="analysis-activity-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label={headline}>
        <i style={{ width: `${Math.max(percent, 4)}%` }} />
      </div>
      <p className="analysis-activity-now">
        <span>{detail}</span>
        {elapsed && <span className="analysis-activity-clock">{elapsed}</span>}
      </p>
      {rows.length > 0 && (
        <ol>
          {rows.map((id) => {
            const state = id === step ? "current" : done.has(id) ? "done" : "wait";
            const label = id === step ? headline : stepTitle(id, lang);
            return (
              <li key={id} className={"is-" + state}>
                <span aria-hidden="true">{state === "done" ? "✓" : state === "current" ? "●" : "○"}</span>
                <span>{label}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
