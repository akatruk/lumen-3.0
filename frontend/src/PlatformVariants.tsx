import {StatusBadge} from './TaskStatus';
import { VariantEditor } from "./VariantEditor";
import { useEffect, useState } from "react";
import type { Lang, Project, Text, Metadata } from "./types";
type Output = {
  platform: string;
  title: string;
  description: string;
  hashtags: string[];
  cta: string;
  rationale: Text;
  metadata: Metadata;
  segments: { start: number; end: number }[];
  review_status?: string;
  locked?: boolean;
};
type Package = {
  status: string;
  master_id: string;
  package_id: string;
  stale: boolean;
  result: {
    variants: Output[];
    completed?: number;
    total?: number;
    scene_boundaries?: number[];
    asset_credits?: unknown[];
  } | null;
};
export function PlatformVariants({ p, lang }: { p: Project; lang: Lang }) {
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const [structures,setStructures]=useState<Record<string,string>>({douyin:'hook_proof_takeaway',instagram_reels:'preserve',youtube_shorts:'problem_solution',tiktok:'hook_proof_takeaway',xiaohongshu:'comparison'});
  const [limits,setLimits]=useState<Record<string,number>>({douyin:60,instagram_reels:60,youtube_shorts:60,tiktok:60,xiaohongshu:60});
  const [pack, setPack] = useState<Package | null>(null),
    [reviewed, setReviewed] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [history, setHistory] = useState<
    { package_id: string; created: number }[]
  >([]);
  const [selected, setSelected] = useState("");
  const [historic, setHistoric] = useState<Package | null>(null);
  const url = "/api/studio/projects/" + p.id + "/variants";
  useEffect(() => {
    setReviewed(false);
  }, [p.result?.render_id]);
  useEffect(() => {
    let live = true;
    async function load() {
      try {
        const r = await fetch(url);
        if (!r.ok) throw Error();
        const s = await r.json();
        if (live) setPack(s);
        const h = await fetch(url + "/history");
        if (h.ok && live) setHistory(await h.json());
      } catch {
        if (live)
          setError(
            t("Could not load platform versions.", "无法加载平台版本。"),
          );
      }
    }
    void load();
    const timer = setInterval(load, 4000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [url, lang]);
  async function create() {
    setBusy(true);
    setError("");
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ master_id: p.result?.render_id, reviewed, max_seconds:limits, structures }),
      });
      if (!r.ok) {
        const e = await r.json();
        throw Error(
          e.detail === "job_already_running"
            ? t("Wait for the current task to finish.", "请等待当前任务完成。")
            : t(
                "Could not start. Refresh the project and check its remaining budget.",
                "无法启动。请刷新项目并检查剩余额度。",
              ),
        );
      }
      const s = await fetch(url);
      setPack(await s.json());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function action(kind: string, data: Record<string, unknown>) {
    setBusy(true);
    setError("");
    try {
      const r = await fetch(url + "/" + kind, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ package_id: pack?.package_id, ...data }),
      });
      if (!r.ok) {
        const e = await r.json();
        const messages: Record<string, string> = {
          variant_locked: t("Unlock this version first.", "请先解锁此版本。"),
          package_changed: t(
            "The package changed. Refresh and try again.",
            "版本包已更新，请刷新后重试。",
          ),
          invalid_variant_edit: t(
            "Use scene boundaries and complete speech ranges; check the content language and overlapping ranges.",
            "请使用完整场景边界，检查语句、内容语言和重叠时间段。",
          ),
          master_changed: t(
            "This package belongs to an older master.",
            "此版本包属于旧主版本。",
          ),
          job_already_running: t(
            "Wait for the current task to finish.",
            "请等待当前任务完成。",
          ),
        };
        throw Error(
          messages[e.detail] ||
            t("Could not save this change.", "无法保存此修改。"),
        );
      }
      setSelected("");
      setHistoric(null);
      const r2 = await fetch(url);
      setPack(await r2.json());
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function selectVersion(id: string) {
    setSelected(id);
    if (!id) {
      setHistoric(null);
      return;
    }
    try {
      const r = await fetch(url + "/history/" + id);
      if (!r.ok) throw Error();
      setHistoric(await r.json());
    } catch {
      setError(t("Could not load this version.", "无法加载此版本。"));
    }
  }
  const displayed = selected ? historic : pack;
  const fileUrl = (name: string) =>
    url +
    "/files/" +
    name +
    (displayed?.package_id ? "?package_id=" + displayed.package_id : "");
  const running = pack && ["queued", "running"].includes(pack.status);
  const names: Record<string, string> = {
    douyin: "Douyin",
    instagram_reels: "Instagram Reels",
    youtube_shorts: "YouTube Shorts",
    tiktok: "TikTok",
    xiaohongshu: "Xiaohongshu / 小红书",
  };
  return (
    <div className="director-card">
      <h2>{t("Platform versions", "平台版本")}</h2>
      <p>
        {t(
          "Create five editorial versions from your reviewed master, with individual titles, covers, post copy and subtitle files. Review each result before publishing.",
          "从已审核主版本生成五个编辑版本，包含各自的标题、封面、发布文案与字幕文件。发布前请逐一审核。",
        )}
      </p>
      <p>
        {t(
          "Export only · nothing is published automatically. Existing master captions and voice are preserved; this does not generate a new voice.",
          "仅导出 · 不会自动发布。保留主版本已有字幕和声音，不生成新配音。",
        )}
      </p>
      <p>
        {t("Content language", "内容语言")}:{" "}
        {p.language === "zh" ? "简体中文" : "English"}
      </p>
      {history.length > 0 && (
        <label>
          {t("Package history", "版本历史")}
          <select
            value={selected}
            onChange={(e) => void selectVersion(e.target.value)}
          >
            <option value="">{t("Current package", "当前版本包")}</option>
            {history.map((h, i) => (
              <option key={h.package_id} value={h.package_id}>
                {new Date(h.created * 1000).toLocaleString()} ·{" "}
                {h.package_id.slice(0, 6)}
              </option>
            ))}
          </select>
        </label>
      )}
      {selected && historic && (
        <p>
          {t(
            "Viewing a saved package. Downloads include that version's review state.",
            "正在查看历史版本包。下载包含该版本的审核状态。",
          )}
          {!historic.stale && (
            <button
              disabled={busy || Boolean(running)}
              onClick={() => void action("restore", { package_id: selected })}
            >
              {t("Restore this package", "恢复此版本包")}
            </button>
          )}
        </p>
      )}
      {!p.result ? (
        <p>
          {t("Render and review a master first.", "请先制作并审核主版本。")}
        </p>
      ) : (
        <>
          {pack?.stale && (
            <p role="status">
              {t(
                "These versions belong to an older master. Generate a new package for the current master.",
                "这些版本来自旧主版本。请为当前主版本生成新包。",
              )}
            </p>
          )}
          {(!pack || pack.stale || pack.status === "failed") && !running && (
            <>
              <fieldset disabled={busy}><legend>{t('Story structure per platform','各平台叙事结构')}</legend><div className="director-form-grid">{Object.entries(structures).map(([key,value])=><label key={key}>{names[key]}<select value={value} onChange={e=>setStructures({...structures,[key]:e.target.value})}>{[['preserve',t('Keep master order','保持主版本顺序')],['hook_proof_takeaway',t('Hook → evidence → takeaway','吸引点 → 证据 → 总结')],['problem_solution',t('Problem → solution','问题 → 解决方案')],['comparison',t('Comparison → conclusion','比较 → 结论')]].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>)}</div><p>{t('AI selects and orders complete scenes independently. If your footage cannot support a structure, the proposal explains the limitation. Review meaning and continuity before approving.','AI 分别选择并排列完整场景。若素材不支持所选结构，建议将说明限制。批准前请检查含义与连贯性。')}</p></fieldset>
              <fieldset disabled={busy}><legend>{t("Initial version duration limits", "首次生成版本的时长上限")}</legend><div className="director-form-grid">{Object.entries(limits).map(([key,value])=><label key={key}>{names[key]}<select value={value} onChange={e=>setLimits({...limits,[key]:Number(e.target.value)})}>{[30,60,90,180,...(key==='youtube_shorts'?[]:[300,420])].map(n=><option value={n} key={n}>{n}s</option>)}</select></label>)}</div><p>{t("AI selects complete scenes within these limits. You can adjust ranges afterward. YouTube Shorts stays square or vertical and at most 180 seconds.","AI 在这些上限内选择完整场景，之后可手动调整范围。YouTube Shorts 保持方形或竖屏，且不超过 180 秒。")}</p></fieldset>
              <label>
                <input
                  type="checkbox"
                  checked={reviewed}
                  onChange={(e) => setReviewed(e.target.checked)}
                />
                {t(
                  "I reviewed this master and approve creating platform previews.",
                  "我已审核此主版本，同意生成平台预览。",
                )}
              </label>
              <p>
                {t(
                  "Planning reserves $0.50 per attempt, with at most one repair, within your project budget. Rendering runs sequentially.",
                  "规划每次尝试预留 $0.50，最多修复一次，受项目预算限制。各版本依次制作。",
                )}
              </p>
              <button
                className="primary"
                disabled={!reviewed || busy}
                onClick={create}
              >
                {t(
                  pack?.status === "failed"
                    ? "Retry platform versions"
                    : "Create 5 versions",
                  pack?.status === "failed" ? "重试平台版本" : "生成 5 个版本",
                )}
              </button>
            </>
          )}
          {pack && <p><StatusBadge status={pack.status}>{pack.status==='failed'?t('Failed','失败'):pack.status==='complete'?t('Package created','版本包已生成'):t('Preparing versions','正在准备版本')}</StatusBadge></p>}
          {running && (
            <p role="status">
              {pack?.result?.completed ?? 0}/{pack?.result?.total ?? 5} ·{" "}
              {t(
                "Processing this package… You can leave this page and return later.",
                "正在处理版本包… 您可以稍后返回查看。",
              )}
            </p>
          )}
          {pack?.status === "failed" && (
            <p role="alert">
              {t(
                "Version creation failed. Your master is preserved. Check remaining budget before retrying.",
                "版本生成失败，主版本已保留。重试前请检查剩余额度。",
              )}
            </p>
          )}
          {displayed?.status === "complete" && displayed.result && (
            <>
              <p>
                <strong>
                  {
                    displayed.result.variants.filter(
                      (v) => v.review_status === "approved",
                    ).length
                  }
                  /{displayed.result.variants.length} {t("versions approved", "个版本已批准")}
                </strong>
              </p>
              <a className="primary" href={fileUrl("package.zip")}>
                {t("Download full package (ZIP)", "下载完整包（ZIP）")}
              </a>
              {!!displayed.result.asset_credits?.length&&<p><a href={fileUrl("credits.json")}>{t("Download source credits — also included in ZIP", "下载素材署名信息（ZIP 中也包含）")}</a></p>}
              {displayed.result.variants.map((v) => (
                <article
                  className="director-card"
                  aria-label={names[v.platform]}
                  key={displayed.package_id + v.platform}
                >
                  <h3>{names[v.platform]}</h3>
                  <p>{v.rationale[lang]}</p>
                  <video
                    controls
                    playsInline
                    preload="metadata"
                    poster={fileUrl(v.platform + ".jpg")}
                    src={fileUrl(v.platform + ".mp4")}
                  />
                  <p>
                    {v.metadata.duration.toFixed(1)}s · {v.metadata.width}×
                    {v.metadata.height} ·{" "}
                    <StatusBadge status={v.review_status === 'approved'?'approved':'needs_review'}>{v.review_status === "approved"
                      ? t("Approved", "已批准")
                      : t("Needs your review", "待您审核")}</StatusBadge>
                  </p>
                  {displayed.result?.scene_boundaries && (
                    <p>
                      {t("Master scene boundaries (s)", "主版本场景边界（秒）")}
                      : {displayed.result.scene_boundaries.join(" · ")}
                    </p>
                  )}
                  <VariantEditor
                    key={displayed.package_id + v.platform}
                    v={v}
                    lang={lang}
                    busy={busy}
                    disabled={
                      Boolean(selected) ||
                      Boolean(running) ||
                      Boolean(displayed.stale)
                    }
                    onAction={action}
                  />
                  <h4>{v.title}</h4>
                  <p style={{ whiteSpace: "pre-wrap" }}>{v.description}</p>
                  <p>{v.hashtags.join(" ")}</p>
                  <p>{v.cta}</p>
                  <a href={fileUrl(v.platform + ".mp4")} download>
                    {t("Video", "视频")}
                  </a>
                  {" · "}
                  <a href={fileUrl(v.platform + ".jpg")} download>
                    {t("Cover", "封面")}
                  </a>
                  {" · "}
                  <a href={fileUrl(v.platform + ".vtt")}>
                    {t("Subtitles", "字幕")}
                  </a>
                  {" · "}
                  <a href={fileUrl(v.platform + ".json")}>
                    {t("Post copy + edit plan", "文案与剪辑计划")}
                  </a>
                </article>
              ))}
            </>
          )}
        </>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
