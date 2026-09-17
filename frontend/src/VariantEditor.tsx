import { useState } from "react";
import type { Lang } from "./types";
export type EditableVariant = {
  platform: string;
  aspect?: "9:16" | "16:9" | "1:1" | "4:5";
  cover_time?: number;
  title: string;
  description: string;
  cta: string;
  hashtags: string[];
  segments: { start: number; end: number }[];
  review_status?: string;
  locked?: boolean;
};
export function VariantEditor({
  v,
  lang,
  busy,
  disabled,
  onAction,
}: {
  v: EditableVariant;
  lang: Lang;
  busy: boolean;
  disabled: boolean;
  onAction: (action: string, data: Record<string, unknown>) => Promise<boolean>;
}) {
  const t = (en: string, zh: string) => (lang === "zh" ? zh : en);
  const [editing, setEditing] = useState(false),
    [draft, setDraft] = useState(v),
    [tags, setTags] = useState(v.hashtags.join(" "));
  const approved = v.review_status === "approved";
  async function review(approved: boolean, locked: boolean) {
    await onAction("review", { platform: v.platform, approved, locked });
  }
  return (
    <section className="variant-editor">
      <p>
        <strong>
          {v.locked
            ? t("Approved · locked", "已批准 · 已锁定")
            : approved
              ? t("Approved", "已批准")
              : t("Needs your review", "待您审核")}
        </strong>
      </p>
      {!disabled && (
        <div className="variant-actions">
          {!approved && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => review(true, false)}
            >
              {t("Approve this version", "批准此版本")}
            </button>
          )}
          {approved && !v.locked && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => review(true, true)}
            >
              {t("Lock approved version", "锁定已批准版本")}
            </button>
          )}
          {v.locked && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => review(true, false)}
            >
              {t("Unlock", "解锁")}
            </button>
          )}
          {approved && !v.locked && (
            <button
              className="text-button"
              disabled={busy}
              onClick={() => review(false, false)}
            >
              {t("Reopen review", "重新审核")}
            </button>
          )}
          <button
            className="secondary"
            disabled={busy || v.locked}
            onClick={() => {
              setDraft(v);
              setTags(v.hashtags.join(" "));
              setEditing(!editing);
            }}
          >
            {t(
              editing ? "Cancel editing" : "Edit this version",
              editing ? "取消编辑" : "编辑此版本",
            )}
          </button>
        </div>
      )}
      {editing && !disabled && (
        <form
          className="variant-edit-form"
          onSubmit={async (e) => {
            e.preventDefault();
            if (
              await onAction("edit", {
                platform: v.platform,
                aspect: draft.aspect || "9:16",
                cover_time: draft.cover_time ?? 1,
                title: draft.title,
                description: draft.description,
                cta: draft.cta,
                hashtags: tags.split(/\s+/).filter(Boolean),
                segments: draft.segments,
              })
            )
              setEditing(false);
          }}
        >
          <p>
            {t(
              "Changes create a new package. Other videos and their approvals remain unchanged. No AI planning charge for manual edits.",
              "修改会创建新版本包，其余视频及批准状态保持不变。手动编辑不产生 AI 规划费用。",
            )}
          </p>
          <label>
            {t("Export frame", "导出画幅")}
            <select value={draft.aspect || "9:16"} onChange={e => setDraft({...draft, aspect:e.target.value as EditableVariant["aspect"]})}>
              {(v.platform==='youtube_shorts'?["9:16", "1:1", "4:5"]:["9:16", "16:9", "1:1", "4:5"]).map(a => <option key={a}>{a}</option>)}
            </select>
          </label>
          <p>{t("The entire reviewed image and its captions are preserved; padding is added when needed.", "完整保留已审核的画面和字幕，必要时添加边框。")}</p>
          <label>
            {t("Cover frame · output second", "封面画面 · 成片秒数")}
            <input type="number" min="0" max="840" step="0.1" required value={draft.cover_time ?? 1} onChange={e => setDraft({...draft,cover_time:Number(e.target.value)})}/>
          </label>
          <p>{t("Output duration", "成片时长")}: {draft.segments.reduce((n,s)=>n+Math.max(0,s.end-s.start),0).toFixed(1)} s</p>
          <label>
            {t("On-screen title", "画面标题")}
            <input
              required
              maxLength={80}
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            />
          </label>
          <label>
            {t("Description", "发布文案")}
            <textarea
              required
              maxLength={1600}
              value={draft.description}
              onChange={(e) =>
                setDraft({ ...draft, description: e.target.value })
              }
            />
          </label>
          <label>
            {t("Hashtags (up to 8)", "话题标签（最多 8 个）")}
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
          </label>
          <label>
            CTA
            <input
              required
              maxLength={160}
              value={draft.cta}
              onChange={(e) => setDraft({ ...draft, cta: e.target.value })}
            />
          </label>
          <p>
            {t(
              "Ranges refer to the reviewed master, in playback order. Use complete scene boundaries; cuts through spoken phrases are rejected.",
              "时间对应已审核主版本，按播放顺序排列。请使用完整场景边界，不可切断语句。",
            )}
          </p>
          {draft.segments.map((s, i) => (
            <div className="variant-range" key={i}>
              <label>
                {t("Start (s)", "开始（秒）")}
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  required
                  value={s.start}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      segments: draft.segments.map((r, j) =>
                        i === j ? { ...r, start: Number(e.target.value) } : r,
                      ),
                    })
                  }
                />
              </label>
              <label>
                {t("End (s)", "结束（秒）")}
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  required
                  value={s.end}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      segments: draft.segments.map((r, j) =>
                        i === j ? { ...r, end: Number(e.target.value) } : r,
                      ),
                    })
                  }
                />
              </label>
              <button
                type="button"
                disabled={draft.segments.length === 1}
                onClick={() =>
                  setDraft({
                    ...draft,
                    segments: draft.segments.filter((_, j) => j !== i),
                  })
                }
              >
                {t("Remove range", "移除片段")}
              </button>
            </div>
          ))}
          <button
            type="button"
            disabled={draft.segments.length >= 12}
            onClick={() =>
              setDraft({
                ...draft,
                segments: [
                  ...draft.segments,
                  {
                    start: draft.segments.at(-1)?.end || 0,
                    end: (draft.segments.at(-1)?.end || 0) + 1,
                  },
                ],
              })
            }
          >
            {t("Add range", "添加片段")}
          </button>
          {v.platform==='youtube_shorts'&&<p>{t('Shorts: square or vertical, up to 180 seconds. Shorten the selected ranges if needed.','Shorts：方形或竖屏，最多 180 秒。必要时缩短所选片段。')}</p>}
          <button className="primary" disabled={busy||(v.platform==='youtube_shorts'&&draft.segments.reduce((n,s)=>n+s.end-s.start,0)>180)} type="submit">
            {t("Save and render this version", "保存并制作此版本")}
          </button>
        </form>
      )}
    </section>
  );
}
