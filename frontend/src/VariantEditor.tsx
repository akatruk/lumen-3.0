import { useState } from "react";
import type { Lang } from "./types";
export type EditableVariant = {
  caption_editable?:boolean; caption_mode?:"inherit"|"custom"|"off"; caption_size?:"small"|"medium"|"large"; caption_position?:"top"|"bottom"; caption_color?:"white"|"yellow";
  hook_seconds?:number; cta_seconds?:number; title_style?:"clean"|"bold"|"panel"; title_position?:"top"|"center";
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
                hook_seconds:draft.hook_seconds??3, cta_seconds:draft.cta_seconds??0, title_style:draft.title_style||"clean", title_position:draft.title_position||"top",
                caption_mode:draft.caption_mode||"inherit", caption_size:draft.caption_size||"medium", caption_position:draft.caption_position||"bottom", caption_color:draft.caption_color||"white",
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
          <p>{t("The entire reviewed image is preserved; padding is added when needed.", "完整保留已审核的画面，必要时添加边框。")}</p>
          {v.caption_editable ? <fieldset disabled={busy}>
            <legend>{t('Captions for this platform','此平台的字幕')}</legend>
            <label>{t('Caption mode','字幕模式')}<select value={draft.caption_mode||'inherit'} onChange={e=>setDraft({...draft,caption_mode:e.target.value as EditableVariant['caption_mode']})}>
              <option value="inherit">{t('Use master settings','使用主版本设置')}</option><option value="custom">{t('Customize','自定义')}</option><option value="off">{t('Off','关闭')}</option>
            </select></label>
            {draft.caption_mode==='custom'&&<>
              <label>{t('Size','大小')}<select value={draft.caption_size||'medium'} onChange={e=>setDraft({...draft,caption_size:e.target.value as EditableVariant['caption_size']})}>{[['small',t('Small','小')],['medium',t('Medium','中')],['large',t('Large','大')]].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
              <label>{t('Position','位置')}<select value={draft.caption_position||'bottom'} onChange={e=>setDraft({...draft,caption_position:e.target.value as EditableVariant['caption_position']})}><option value="bottom">{t('Bottom','底部')}</option><option value="top">{t('Top','顶部')}</option></select></label>
              <label>{t('Color','颜色')}<select value={draft.caption_color||'white'} onChange={e=>setDraft({...draft,caption_color:e.target.value as EditableVariant['caption_color']})}><option value="white">{t('White','白色')}</option><option value="yellow">{t('Yellow','黄色')}</option></select></label>
            </>}
            <p>{t('Changes affect Lumen captions only. Text already in the source video stays visible. Check for overlap with your title.','仅修改 Lumen 字幕，原视频自带文字仍会保留。请检查字幕是否与标题重叠。')}</p>
          </fieldset>:<p>{t('To customize captions, render a new master and create a new platform package. This older master has embedded captions.','如需自定义字幕，请重新制作主版本并创建平台版本包。旧主版本的字幕已嵌入画面。')}</p>}
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
          <div className="manual-grid">
            <label>{t('Title style','标题样式')}<select value={draft.title_style||'clean'} onChange={e=>setDraft({...draft,title_style:e.target.value as EditableVariant['title_style']})}>{[['clean',t('Clean','简洁')],['bold',t('Bold','粗体')],['panel',t('Background panel','背景框')]].map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
            <label>{t('Title position','标题位置')}<select value={draft.title_position||'top'} onChange={e=>setDraft({...draft,title_position:e.target.value as EditableVariant['title_position']})}><option value="top">{t('Top','顶部')}</option><option value="center">{t('Center','居中')}</option></select></label>
            <label>{t('Opening title (seconds; 0 = off)','开场标题（秒；0 为关闭）')}<input type="number" min={0} max={8} step={.5} value={draft.hook_seconds??3} onChange={e=>setDraft({...draft,hook_seconds:Number(e.target.value)})}/></label>
            <label>{t('Closing CTA (seconds; 0 = off)','结尾行动提示（秒；0 为关闭）')}<input type="number" min={0} max={8} step={.5} value={draft.cta_seconds??0} onChange={e=>setDraft({...draft,cta_seconds:Number(e.target.value)})}/></label>
          </div>
          <small>{t('These overlays are rendered into this version. Existing master captions stay unchanged. On short cuts, the opening title takes priority over an overlapping CTA.','这些文字将渲染到此版本中，原成片字幕保持不变。短视频中若时间重叠，优先显示开场标题。')}</small>
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
              <strong>{t('Scene','场景')} {i+1}</strong>
              <button type="button" disabled={i===0} onClick={()=>setDraft({...draft,segments:[draft.segments[i],...draft.segments.filter((_,j)=>j!==i)]})}>{t('Use as opening','设为开场')}</button>
              <button type="button" disabled={i===0} onClick={()=>{const next=[...draft.segments];[next[i-1],next[i]]=[next[i],next[i-1]];setDraft({...draft,segments:next})}}>{t('Move earlier','前移')}</button>
              <button type="button" disabled={i===draft.segments.length-1} onClick={()=>{const next=[...draft.segments];[next[i+1],next[i]]=[next[i],next[i+1]];setDraft({...draft,segments:next})}}>{t('Move later','后移')}</button>
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
