import {RenderSummary,type RenderSummaryData} from './RenderSummary';
import {createPortal} from 'react-dom';
import {useWorkspace, workspaceText} from './ProjectWorkspace';
import type {ReactNode} from 'react';
import {SoundtrackLibrary} from './SoundtrackLibrary';
import { translate, contentLanguage } from './locale';
import {reviseDecision} from './decisionReview';
import {MusicPlan} from './MusicPlan';
import {BeatPreview} from './BeatPreview';
import {StockLibrary} from './StockLibrary';
import {MusicEditor,type Music} from './MusicEditor';
import {SoundEffectEditor,type SoundEffect} from './SoundEffectEditor';
import {MediaLibrary,AssetPlacement,type Asset,type ExternalBroll,type MediaLibraryHandle} from './MediaLibrary';
import {CutawayEditor,type Cutaway} from './CutawayEditor';
import {VisualCardEditor,type VisualCard} from './VisualCardEditor';
import {TimelineRegenerate} from './TimelineRegenerate';
import {TimelineTracks} from './TimelineTracks';
import { useEffect, useRef, useState } from "react";
import type { Lang, ContentLang } from "./types";
type Clip = {
  audio_fade_ms?: number;
  external_broll?:ExternalBroll|null;
  cutaway?:Cutaway|null;
  sound_effects?:SoundEffect[];
  card?:VisualCard|null;
  id?: string; approved?: boolean; locked?: boolean;
  shot_type?: 'presenter'|'close_up'|'medium'|'broll'|'document'|'archive'|'news';
  zoom_end?: number|null; x_end?: number|null; y_end?: number|null;
  transition?: 'cut'|'fade'|'crossfade'|'zoom'|'wipe'|'circle';
  start: number;
  end: number;
  zoom: number;
  x: number;
  y: number;
  text: string;
};
type Caption = {
  emphasis_en?:string[];
  emphasis_zh?:string[];
  start: number;
  end: number;
  original: string;
  en: string;
  zh: string;
};
export type Edit = {
  music?:Music|null;
  clips: Clip[];
  captions: Caption[];
  subtitles: boolean;
  normalize: boolean;
  font_size: "small" | "medium" | "large";
  position: "top" | "bottom";
  color: "white" | "yellow";
};
export function ManualEditor({
  pid,
  lang,
  outputLanguage,
  hasAudio=true,
  duration,
  ratio,
  disabled,
  onSaved,
  voiceover,
  serverRevision,
  onDirtyChange,
}: {
  pid: string;
  lang: Lang;
  outputLanguage: ContentLang;
  hasAudio?:boolean;
  duration: number;
  ratio: number;
  disabled: boolean;
  onSaved: () => Promise<void>;
  voiceover?:ReactNode;
  serverRevision?:number;
  onDirtyChange?:(dirty:boolean)=>void;
}) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const workspace=useWorkspace();
  const task=workspace?.task||'edit';
  const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
  const portal=(node:ReactNode,target:HTMLElement|null|undefined)=>target?createPortal(node,target):node;
  const [renderSummary,setRenderSummary]=useState<RenderSummaryData|null>(null);
  const [summaryError,setSummaryError]=useState(false);
  const summaryRequest=useRef(0);
  async function loadRenderSummary(){
    const request=++summaryRequest.current;
    setRenderSummary(null);setSummaryError(false);
    try{const r=await fetch(base+'/summary');if(!r.ok)throw Error();const data=await r.json();if(request===summaryRequest.current)setRenderSummary(data)}
    catch{if(request===summaryRequest.current)setSummaryError(true)}
  }
  const reviewDialog=useRef<HTMLDialogElement>(null);
  const reviewOpener=useRef<HTMLElement|null>(null);
  const mediaLibrary = useRef<MediaLibraryHandle>(null);
  const [edit, setEdit] = useState<Edit | null>(null),
    [revision, setRevision] = useState(0),
    [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(0),
    [before, setBefore] = useState(false),
    [time, setTime] = useState(0);
  const [matchRequest,setMatchRequest]=useState<{clipId:string;assetIds:string[];instruction:string;nonce:number}|null>(null);
  const [qualityReview,setQualityReview]=useState(true);
  const video = useRef<HTMLVideoElement>(null),
    pending = useRef<number | null>(null);
  const base = `/api/studio/projects/${pid}/manual`;
  const [assets,setAssets]=useState<Asset[]>([]);
  async function loadAssets(){const r=await fetch(`/api/studio/projects/${pid}/assets`);if(r.ok)setAssets(await r.json())}
  useEffect(()=>{void loadAssets()},[pid]);
  const draftKey = `lumen-manual-draft:${pid}`;
  async function load() {
    setError("");
    try {
      const r = await fetch(base);
      if (!r.ok) throw Error();
      const data = await r.json();
      let draft = null;
      try {
        draft = JSON.parse(sessionStorage.getItem(draftKey) || "null");
      } catch {}
      setEdit(draft?.edit || data.edit);
      setRevision(draft?.revision || data.revision);
      setDirty(!!draft || !data.saved);
      setSelected(0);
    } catch {
      setError(t("Could not load manual edits.", "无法加载手动剪辑。"));
    }
  }
  useEffect(() => {
    void load();
  }, [pid]);
  useEffect(() => {
    if (dirty && edit) {
      try {
        sessionStorage.setItem(draftKey, JSON.stringify({ edit, revision }));
      } catch {}
    }
  }, [edit, dirty, revision, draftKey]);
  useEffect(() => {
    if (!dirty) return;
    const f = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", f);
    return () => window.removeEventListener("beforeunload", f);
  }, [dirty]);
  useEffect(() => {
    const start = edit?.clips[selected]?.start;
    if (start === undefined) return;
    pending.current = start;
    if (video.current?.readyState && video.current.readyState >= 1) {
      video.current.pause();
      video.current.currentTime = start;
      pending.current = null;
    }
    setTime(start);
  }, [selected, edit?.clips[selected]?.start]);
  useEffect(()=>{if(workspace&&!workspace.draftActive)video.current?.pause()},[workspace?.draftActive]);
  useEffect(()=>{onDirtyChange?.(dirty)},[dirty,onDirtyChange]);
  useEffect(()=>{if(edit&&!dirty&&serverRevision!==undefined&&serverRevision!==revision)void load()},[serverRevision]);
  const blocked = disabled || busy;
  function change(p: Partial<Edit>) {
    setEdit((e) => (e ? { ...e, ...p } : e));
    setDirty(true);
    workspace?.showDraft();
  }
  function clipChange(i: number, p: Partial<Clip>) {
    if (edit)
      change({
        clips: edit.clips.map((c, j) => (i === j ? reviseDecision(c,p) : c)),
      });
  }
  function captionChange(i: number, p: Partial<Caption>) {
    if (edit)
      change({
        captions: edit.captions.map((c, j) => (i === j ? { ...c, ...p } : c)),
      });
  }
  async function act(render = false) {
    if (!edit) return;
    setBusy(true);
    setError("");
    try {
      const r = await fetch(base + (render ? "/render" : ""), {
        method: render ? "POST" : "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(render ? { revision,quality_review:qualityReview } : { revision, edit }),
      });
      if (!r.ok) {
        const d = await r.json();
        throw Error(
          d.detail === "plan_changed"
            ? t(
                "The plan changed. Reload saved edits before continuing.",
                "计划已更新，请重新加载已保存的剪辑。",
              )
            : t(
                "Check time ranges, subtitle text and whether another job is running.",
                "请检查时间范围、字幕文字，以及是否有任务正在运行。",
              ),
        );
      }
      if (!render) {
        const d = await r.json();
        setRevision(d.revision);
        setEdit(d.edit);
        setDirty(false);
        sessionStorage.removeItem(draftKey);
      }
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function preview() {
    if (!edit || !video.current) return;
    const start = edit.clips[selected].start;
    pending.current = start;
    if (video.current.readyState >= 1) {
      video.current.currentTime = start;
      pending.current = null;
    }
    setTime(start);
    void video.current.play().catch(() => {});
  }
  if (!edit)
    return (
      <section className="director-card">
        <h3>{t("Manual editor", "手动剪辑")}</h3>
        <p role="status">{error || t("Loading editor…", "正在加载编辑器…")}</p>
        <button onClick={() => void load()}>{t("Reload", "重新加载")}</button>
      </section>
    );
  const clip = edit.clips[selected] || edit.clips[0];
  const progress=Math.max(0,Math.min(1,(time-clip.start)/(clip.end-clip.start)));
  const frameZoom=clip.zoom+((clip.zoom_end??clip.zoom)-clip.zoom)*progress;
  const frameX=clip.x+((clip.x_end??clip.x)-clip.x)*progress;
  const frameY=clip.y+((clip.y_end??clip.y)-clip.y)*progress;
  const activeCaption = edit.captions.find((c) => time >= c.start && time < c.end);
  const subtitle = edit.subtitles
    ? activeCaption?.[outputLanguage] || activeCaption?.original || ""
    : "";
  const invalidMilestones=edit.clips.some(c=>c.card?.kind==='timeline'&&((c.card.milestones?.length||0)<2||(c.card.milestones||[]).some(m=>!m.when.en.trim()||!m.when.zh.trim()||!m.label.en.trim()||!m.label.zh.trim())));
  const invalidAnimation=edit.clips.some(c=>c.card?.animation==='grow'&&(!['bar_chart','ranking'].includes(c.card.kind)||!Number.isFinite(c.card.animation_seconds??.6)||(c.card.animation_seconds??.6)<.2||(c.card.animation_seconds??.6)>2||(c.card.animation_seconds??.6)>c.card.end-c.card.start-.15));
  const invalidEmphasis=edit.captions.some(c=>[...(c.emphasis_en||[]),...(c.emphasis_zh||[])].some(s=>!s.trim()||s.length>48)||(c.emphasis_en?.length||0)>8||(c.emphasis_zh?.length||0)>8);
  const invalidData=edit.clips.some(c=>c.card&&['bar_chart','ranking'].includes(c.card.kind)&&((c.card.items?.length||0)<2||(c.card.items||[]).some(v=>!v.label.en.trim()||!v.label.zh.trim()||!Number.isFinite(v.value)||v.value<0||v.value>1e12)));
  const invalidCard=edit.clips.some(c=>c.card&&(c.card.start<0||c.card.end>c.end-c.start||c.card.end-c.card.start<.5||![c.card.start,c.card.end].every(Number.isFinite)||[c.card.title,c.card.primary,c.card.source,...(c.card.kind==='comparison'?[c.card.secondary]:[])].some(v=>!v?.en.trim()||!v?.zh.trim())));
  const invalidCutaway=edit.clips.some(c=>c.cutaway&&(![c.cutaway.start,c.cutaway.end,c.cutaway.source_start].every(Number.isFinite)||c.cutaway.start<0||c.cutaway.end>c.end-c.start||c.cutaway.end-c.cutaway.start<.08||c.cutaway.source_start<0||c.cutaway.source_start+c.cutaway.end-c.cutaway.start>duration));
  const invalidAsset=edit.clips.some(c=>{const v=c.external_broll;if(!v)return false;const a=assets.find(x=>x.id===v.asset_id);return !a||!!c.cutaway||![v.start,v.end,v.source_start].every(Number.isFinite)||v.start<0||v.end>c.end-c.start||v.end-v.start<.08||v.source_start<0||v.source_start+v.end-v.start>a.metadata.duration});
  const invalidSound=edit.clips.some(c=>(c.sound_effects||[]).some(e=>![e.at,e.gain_db].every(Number.isFinite)||e.at<0||e.at+({chime:.6,click:.08,whoosh:.4}[e.kind])>c.end-c.start||e.gain_db < -36||e.gain_db > -12));
  const invalidMusic=(edit.music?.levels||[]).some((p,i,points)=>!Number.isFinite(p.at)||!Number.isFinite(p.gain_db)||p.at<0||p.at>840||p.gain_db< -40||p.gain_db> -6||(i===0?p.at!==0:p.at<=points[i-1].at));
  const invalidMap=edit.clips.some(c=>c.card?.kind==='map'&&(!(c.card.locations||[]).length||(c.card.locations||[]).some(p=>!p.label.en.trim()||!p.label.zh.trim()||!Number.isFinite(p.latitude)||!Number.isFinite(p.longitude)||Math.abs(p.latitude)>90||Math.abs(p.longitude)>180)));
  const unapprovedCount = edit.clips.filter(c=>c.approved===false).length;
  const invalid = invalidMusic || invalidMap || invalidEmphasis || invalidAnimation || invalidMilestones || invalidData || invalidSound || invalidAsset || invalidCutaway || invalidCard ||
    edit.clips.some(
      (c) =>
        !Number.isFinite(c.start) ||
        !Number.isFinite(c.end) ||
        c.start < 0 ||
        c.end > duration ||
        c.end - c.start < 0.08 ||
        !Number.isFinite(c.zoom) || c.zoom < 1 || c.zoom > 3 ||
        !Number.isFinite(c.x) || c.x < 0 || c.x > 1 ||
        !Number.isFinite(c.y) || c.y < 0 || c.y > 1,
    ) ||
    edit.captions.some(
      (c) => c.start < 0 || c.end > duration || c.end <= c.start,
    ) ||
    (edit.subtitles && !edit.captions.length);
  return (
    <section
      className="director-card manual-editor"
      aria-label={t("Manual editor", "手动剪辑")}
    >
      <details className="ws-editor-help"><summary>{w("Как работает редактор","How editing works","编辑器说明")}</summary>
      <p>
        {t(
          "Build a separate manual cut from your footage. Its clip order and settings replace the AI edits for this render; the AI plan remains available. Saving is free. Rendering uses no AI calls and requires your visual review.",
          "使用自有素材制作手动版本。本次制作使用下方片段顺序和设置，替代 AI 改动；AI 计划仍然保留。保存免费，制作不调用 AI，需要您亲自检查成片。",
        )}
      </p>
      <div hidden={task!=="edit"}>
      <button className="secondary" disabled={blocked||dirty||edit.clips.some(c=>c.locked)} onClick={async()=>{setBusy(true);setError('');try{const r=await fetch(base+'/from-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision})});if(!r.ok)throw Error(t('Save or reload the latest plan first.','请先保存或重新加载最新计划。'));const data=await r.json();setEdit(data.edit);setDirty(true);setSelected(0);}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>{t('Build timeline from approved AI edits','根据已批准的 AI 改动建立时间线')}</button>
      </div>
      </details>
      <div hidden={task!=="audio"}>{voiceover}
      <SoundtrackLibrary pid={pid} lang={lang} full={assets.length>=20} onChanged={loadAssets}/>
      </div>
      <div hidden={task!=="materials"}>
      <MediaLibrary ref={mediaLibrary} pid={pid} lang={lang} assets={assets} onChanged={loadAssets}/>
      </div>
      <div hidden={task!=="audio"}>
      <MusicPlan onUploadMusic={()=>{workspace?.setTask('materials');requestAnimationFrame(()=>mediaLibrary.current?.openMusicUpload())}} currentMusic={edit.music} pid={pid} revision={revision} assets={assets.filter(a=>a.metadata.kind==='music')} lang={lang} disabled={blocked||dirty||!!edit.music?.locked} onApplied={async()=>{sessionStorage.removeItem(draftKey);await load();await onSaved()}}/>
      </div>
      <div hidden={task!=="materials"}>
      <StockLibrary onMatch={ids=>{if(!clip.id||blocked||dirty||clip.locked)return;setMatchRequest({clipId:clip.id,assetIds:ids,instruction:t('Choose a visually relevant sampled moment for this scene and its narration. Preserve original speech. If none fits, propose no replacement.','为当前场景与旁白选择视觉相关的样本片段，保留原声。如无合适素材，请勿替换。'),nonce:Date.now()})}} pid={pid} lang={lang} onChanged={loadAssets} assets={assets} revision={revision} scene={{id:clip.id,label:`${selected+1} · ${clip.start.toFixed(1)}–${clip.end.toFixed(1)}s`,context:[clip.text,...edit.captions.filter(c=>c.end>clip.start&&c.start<clip.end).map(c=>c[contentLanguage(lang)]||c.original)].filter(Boolean).join(' ').slice(0,1000),disabled:blocked||dirty||!!clip.locked}} onPlace={id=>{const asset=assets.find(a=>a.id===id);if(!asset||blocked||clip.locked)return;const length=Math.min(clip.end-clip.start,asset.metadata.duration,4);if(length<=0)return;clipChange(selected,{external_broll:{asset_id:id,start:0,end:length,source_start:0},cutaway:null,approved:false});}}/>
      </div>
      <div hidden={task!=="audio"}>
      {edit.music&&<BeatPreview pid={pid} revision={revision} lang={lang} disabled={blocked||dirty} onPreview={value=>{setEdit(value);setDirty(true)}}/>}
      <MusicEditor pid={pid} onAnalyzed={loadAssets} firstCut={edit.clips.filter(c=>c.approved!==false).length>1?(()=>{const c=edit.clips.find(c=>c.approved!==false)!;return c.end-c.start})():null} value={edit.music||null} assets={assets.filter(a=>a.metadata.kind==='music')} lang={lang} disabled={blocked} onChange={music=>change({music})}/>
      </div>
      {portal(<section className="ws-scene-list"><div className="ws-scene-heading"><h3>{w('Сцены','Scenes','场景')} <small>{edit.clips.length}</small></h3><span>{w('Выберите сцену для редактирования','Select a scene to edit','选择场景进行编辑')}</span></div><div className="ws-scenes">{edit.clips.map((c,i)=><button key={c.id||i} aria-pressed={selected===i} onClick={()=>{setSelected(i);workspace?.showDraft();if(task==='review')workspace?.setTask('edit')}}><span>{String(i+1).padStart(2,'0')}</span><strong>{c.text||`${w('Сцена','Scene','场景')} ${i+1}`}</strong><small>{c.start.toFixed(1)}–{c.end.toFixed(1)}s · {c.approved===false?w('Нужна проверка','Review needed','待审核'):w('Проверено','Approved','已批准')}</small></button>)}</div><details><summary>{w('Дорожки таймлайна','Timeline tracks','时间轴轨道')}</summary>      <TimelineTracks hasAudio={hasAudio} key={pid} musicAsset={assets.find(a=>a.id===edit.music?.asset_id)} music={edit.music} clips={edit.clips} captions={edit.captions} subtitles={edit.subtitles} lang={lang} onSelect={i=>{setSelected(i);workspace?.showDraft()}} />
</details></section>,workspace?.scenesTarget)}
      <div hidden={task!=='edit'&&task!=='effects'}>
      <details open>
        <summary>
          {task==='effects'?w('Эффекты выбранной сцены','Selected scene effects','所选场景效果'):w('Настройки выбранной сцены','Selected scene settings','所选场景设置')}
        </summary>
        <fieldset disabled={blocked} className="director-fieldset">
          {edit.clips.map((c, i) => (
            <article className="manual-clip" hidden={!!workspace&&selected!==i} key={c.id||i}>
              <details className="ws-scene-options"><summary>{w('Порядок и удаление сцены','Reorder or remove scene','调整顺序或删除场景')} · {i+1}</summary><div className="manual-actions">
                <strong>
                  {t("Clip", "片段")} {i + 1}
                </strong>
                <button
                  disabled={!i||c.locked||edit.clips[i-1]?.locked}
                  onClick={() => {
                    const clips = [...edit.clips];
                    [clips[i - 1], clips[i]] = [clips[i], clips[i - 1]];
                    change({ clips });
                    setSelected(i - 1);
                  }}
                >
                  {t("Move up", "前移")}
                </button>
                <button
                  disabled={i === edit.clips.length - 1||c.locked||edit.clips[i+1]?.locked}
                  onClick={() => {
                    const clips = [...edit.clips];
                    [clips[i + 1], clips[i]] = [clips[i], clips[i + 1]];
                    change({ clips });
                    setSelected(i + 1);
                  }}
                >
                  {t("Move down", "后移")}
                </button>
                <button
                  disabled={edit.clips.length === 1||c.locked}
                  onClick={() => {
                    change({ clips: edit.clips.filter((_, j) => i !== j) });
                    setSelected(0);
                  }}
                >
                  {t("Remove clip", "移除片段")}
                </button>
                <button
                  aria-pressed={selected === i}
                  onClick={() => {
                    setSelected(i);
                    video.current?.pause();
                    setTime(c.start);
                  }}
                >
                  {t("Inspect", "查看")}
                </button>
              </div>
              </details><p className="muted">{w('Изменения снимают подтверждение сцены.','Changes clear this scene’s approval.','修改后需要重新批准场景。')}</p><div className="manual-actions"><label><input type="checkbox" checked={c.approved!==false} disabled={c.locked} onChange={e=>clipChange(i,{approved:e.target.checked})}/>{t('Approve','批准')}</label><label><input type="checkbox" checked={!!c.locked} disabled={c.approved===false} onChange={e=>clipChange(i,{locked:e.target.checked})}/>{t('Lock','锁定')}</label></div>
              <fieldset className="director-fieldset" disabled={c.locked}>
              {task==='effects'&&<div className="ws-effect-presets"><button type="button" onClick={()=>clipChange(i,{zoom:1,zoom_end:1.2})}>{w('Плавное приближение','Gentle zoom','缓慢放大')}</button><button type="button" onClick={()=>clipChange(i,{transition:'crossfade'})}>{w('Растворение','Cross dissolve','叠化')}</button><button type="button" onClick={()=>clipChange(i,{zoom:1,zoom_end:1,transition:'cut'})}>{w('Без движения','No motion','静止画面')}</button></div>}
              <details><summary>{w('Роль сцены и края звука','Scene role and audio edges','场景用途与声音边缘')}</summary><label>{t('Shot role','镜头用途')}<select value={c.shot_type||'presenter'} onChange={e=>clipChange(i,{shot_type:e.target.value as Clip['shot_type']})}>{[['presenter',t('Presenter','人物讲解')],['close_up',t('Close-up','特写')],['medium',t('Medium shot','中景')],['broll',t('B-roll / cutaway','补充镜头')],['document',t('Document','文档')],['archive',t('Archival footage','档案影像')],['news',t('News clip','新闻片段')]].map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
              <label>{t('Source audio edge smoothing','原声边缘平滑')}<select value={c.audio_fade_ms||0} onChange={e=>clipChange(i,{audio_fade_ms:Number(e.target.value)})}>{[0,10,30,60,100].map(ms=><option key={ms} value={ms}>{ms?`${ms} ms`:t('Off — preserve original audio','关闭 — 保留原声')}</option>)}</select></label>
              <small>{t('Short fades at both clip edges reduce clicks. They affect the whole source mix, including speech; they do not restore a broken musical phrase. Timing is unchanged.','片段首尾短淡化可减少爆音。它影响包括人声在内的全部原声，不能修复被截断的音乐乐句。时间轴不变。')}</small>
              </details><div className="manual-grid">
                {(["start", "end", "zoom", "x", "y"] as const).map((key) => (
                  <label key={key}>
                    {
                      {
                        start: t("Source start (s)", "原片开始（秒）"),
                        end: t("Source end (s)", "原片结束（秒）"),
                        zoom: t("Zoom (1–3×)", "缩放（1–3 倍）"),
                        x: t("Crop horizontal (0–1)", "水平位置（0–1）"),
                        y: t("Crop vertical (0–1)", "垂直位置（0–1）"),
                      }[key]
                    }
                    <input
                      type={key === 'start' || key === 'end' ? 'number' : 'range'}
                      step={key === "start" || key === "end" ? 0.1 : 0.05}
                      min={key === "zoom" ? 1 : 0}
                      max={
                        key === "zoom"
                          ? 3
                          : key === "x" || key === "y"
                            ? 1
                            : duration
                      }
                      value={c[key]}
                      onChange={(e) =>
                        clipChange(i, { [key]: Number(e.target.value) })
                      }
                    />
                  </label>
                ))}
              </div>
              <label>
                {t("Text overlay for this clip", "此片段的叠加文字")}
                <input
                  maxLength={160}
                  value={c.text}
                  onChange={(e) => clipChange(i, { text: e.target.value })}
                />
              </label>
              <details><summary>{w('Вставки, звук и карточки','Cutaways, sound and cards','补充镜头、声音与卡片')}</summary>
              <AssetPlacement value={c.external_broll||null} assets={assets.filter(a=>a.metadata.kind!=='music')} duration={c.end-c.start} lang={lang} onChange={external_broll=>clipChange(i,{external_broll,...(external_broll?{cutaway:null}:{})})}/>
              <CutawayEditor value={c.cutaway||null} duration={c.end-c.start} sourceDuration={duration} pid={pid} lang={lang} onChange={cutaway=>clipChange(i,{cutaway,...(cutaway?{external_broll:null}:{})})}/>
              <SoundEffectEditor effects={c.sound_effects||[]} duration={c.end-c.start} lang={lang} onChange={sound_effects=>clipChange(i,{sound_effects})}/>
              <VisualCardEditor card={c.card||null} duration={c.end-c.start} lang={lang} onChange={card=>clipChange(i,{card})}/>
              </details>
              <details open={task==='effects'}><summary>{t('Camera motion: end framing','镜头运动：结束构图')}</summary><p>{t('The camera moves smoothly from the initial framing above to these end values. Matching values keep the camera still.','镜头从上方初始构图平滑移动至下方结束构图。数值相同则保持静止。')}</p><div className="manual-grid">{(['zoom_end','x_end','y_end'] as const).map((key,j)=><label key={key}>{[t('End zoom','结束缩放'),t('End horizontal position','结束水平位置'),t('End vertical position','结束垂直位置')][j]}<input type="range" min={j===0?1:0} max={j===0?3:1} step="0.05" value={c[key]??[c.zoom,c.x,c.y][j]} onChange={e=>clipChange(i,{[key]:Number(e.target.value)})}/><output>{(c[key]??[c.zoom,c.x,c.y][j]).toFixed(2)}</output></label>)}</div></details>
              <label>{t('Transition','转场')}<select value={c.transition||'cut'} onChange={e=>clipChange(i,{transition:e.target.value as Clip['transition']})}><option value="cut">{t('Straight cut','直接切换')}</option><option value="crossfade">{t('Cross dissolve','叠化')}</option><option value="zoom">{t('Zoom transition','缩放转场')}</option><option value="wipe">{t('Wipe left','向左擦除')}</option><option value="circle">{t('Circle mask','圆形遮罩')}</option><option value="fade">{t('Fade through black','淡入淡出至黑场')}</option></select></label>
              </fieldset>
            </article>
          ))}
          <button
            disabled={edit.clips.length >= 40}
            onClick={() => {
              change({
                clips: [
                  ...edit.clips,
                  {
                    id: crypto.randomUUID(), approved:false,locked:false,
                    start: 0,
                    end: duration,
                    zoom: 1,
                    x: 0.5,
                    y: 0.5,
                    text: "",
                  },
                ],
              });
              setSelected(edit.clips.length);
            }}
          >
            {t("Add clip from source", "添加原片片段")}
          </button>
        </fieldset>
        <p>
          {t(
            "Times refer to the original footage. Repeated ranges repeat that footage; omitted ranges are cut. Check that cuts preserve complete speech.",
            "时间对应原片。重复范围会重复播放，未选范围会被剪掉。请确保剪切不截断讲话。",
          )}
        </p>
      </details>
      <TimelineRegenerate matchRequest={matchRequest} assets={assets.filter(a=>a.metadata.kind!=='music')} pid={pid} revision={revision} clipId={clip.id} locked={clip.locked} disabled={blocked||dirty} lang={lang} onApplied={async()=>{sessionStorage.removeItem(draftKey);await load();await onSaved()}} />
      </div>
      {portal(<div className="manual-preview">
        <div className="manual-actions">
          <strong>
            {t("Clip draft preview", "片段草稿预览")} {selected + 1}
          </strong>
          <button aria-pressed={before} onClick={() => setBefore(true)}>
            {t("Before", "原片")}
          </button>
          <button aria-pressed={!before} onClick={() => setBefore(false)}>
            {t("After", "修改后")}
          </button>
          <button onClick={preview} disabled={invalid}>
            {t("Play selected range", "播放选定范围")}
          </button>
        </div>
        <div className="manual-screen" style={{ aspectRatio: ratio }}>
          <video
            ref={video}
            playsInline
            controls
            preload="metadata"
            src={`/api/projects/${pid}/media/source`}
            style={{
              transform: before ? "none" : `scale(${frameZoom})`,
              transformOrigin: `${frameX * 100}% ${frameY * 100}%`,
            }}
            onLoadedMetadata={() => {
              if (pending.current !== null && video.current) {
                video.current.currentTime = pending.current;
                pending.current = null;
              }
            }}
            onTimeUpdate={() => {
              if (video.current) {
                setTime(video.current.currentTime);
                if (video.current.currentTime >= clip.end)
                  video.current.pause();
              }
            }}
          />
          {!before && clip.text && (
            <span
              className="manual-overlay"
              style={{ top: "15%", fontSize: `calc(100cqw / ${ratio} * .035)` }}
            >
              {clip.text}
            </span>
          )}
          {!before && subtitle && (
            <span
              className="manual-overlay"
              style={{
                [edit.position === "top" ? "top" : "bottom"]: "15%",
                color: edit.color === "yellow" ? "#ffff00" : "white",
                fontSize: `calc(100cqw / ${ratio} * ${{ small: 0.026, medium: 0.035, large: 0.045 }[edit.font_size]})`,
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
        <button onClick={() => video.current?.pause()}>
          {t("Pause", "暂停")}
        </button>
        <small>
          {t(
            "Draft preview approximates crop and text. Sound is original. Render the manual cut to inspect exact subtitles, audio and all transitions.",
            "草稿近似显示裁剪和文字，声音为原片。请制作手动版本以准确检查字幕、声音和所有衔接。",
          )}
        </small>
      </div>,workspace?.previewTarget)}
      <div hidden={task!=='subtitles'}>
      <section className="ws-source-text"><h3>{w('Надписи в исходнике','Text in the original footage','原片中的文字')}</h3><p>{w('Если текст уже записан в изображение, переключатель субтитров его не уберёт. Загрузите исходник без текста или измените кадрирование.','Text already embedded in the picture cannot be switched off. Use a clean source or adjust the crop.','已嵌入画面的文字无法关闭，请使用无字幕原片或调整裁剪。')}</p><button onClick={()=>workspace?.setTask('edit')}>{w('Настроить кадр','Adjust framing','调整构图')}</button></section>
      <details open>
        <summary>
          {t("2. Edit subtitles and styling", "2. 编辑字幕和样式")}
        </summary>
        <p>{t('Output subtitle language: ', '成片字幕语言：')}{outputLanguage === 'zh' ? '中文' : 'English'}</p>
        <fieldset disabled={blocked} className="director-fieldset">
          <label>
            <input
              type="checkbox"
              checked={edit.subtitles}
              onChange={(e) => change({ subtitles: e.target.checked })}
            />
            {t(
              " Burn edited subtitles into the video",
              " 将编辑后的字幕写入视频",
            )}
          </label>
          <p>
            {t(
              "Existing subtitles inside the original picture cannot be removed here.",
              "此处不能移除原片画面中已有的字幕。",
            )}
          </p>
          <div className="manual-grid">
            <label>
              {t("Size", "字号")}
              <select
                value={edit.font_size}
                onChange={(e) =>
                  change({ font_size: e.target.value as Edit["font_size"] })
                }
              >
                {(["small", "medium", "large"] as const).map((s, i) => (
                  <option key={s} value={s}>
                    {[t("Small", "小"), t("Medium", "中"), t("Large", "大")][i]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("Position", "位置")}
              <select
                value={edit.position}
                onChange={(e) =>
                  change({ position: e.target.value as Edit["position"] })
                }
              >
                <option value="bottom">{t("Bottom", "底部")}</option>
                <option value="top">{t("Top", "顶部")}</option>
              </select>
            </label>
            <label>
              {t("Color", "颜色")}
              <select
                value={edit.color}
                onChange={(e) =>
                  change({ color: e.target.value as Edit["color"] })
                }
              >
                <option value="white">{t("White", "白色")}</option>
                <option value="yellow">{t("Yellow", "黄色")}</option>
              </select>
            </label>
          </div>
          {edit.captions.map((c, i) => (
            <div className="manual-caption" key={i}>
              <strong>{i + 1}</strong>
              <div className="manual-grid">
                <label>
                  {t("Start (s)", "开始（秒）")}
                  <input
                    type="number"
                    step="0.1"
                    min={0}
                    max={duration}
                    value={c.start}
                    onChange={(e) =>
                      captionChange(i, { start: Number(e.target.value) })
                    }
                  />
                </label>
                <label>
                  {t("End (s)", "结束（秒）")}
                  <input
                    type="number"
                    step="0.1"
                    min={0}
                    max={duration}
                    value={c.end}
                    onChange={(e) =>
                      captionChange(i, { end: Number(e.target.value) })
                    }
                  />
                </label>
              </div>
              <label>
                English
                <textarea
                  maxLength={300}
                  value={c.en}
                  onChange={(e) => captionChange(i, { en: e.target.value })}
                />
              </label>
              <label>
                中文
                <textarea
                  maxLength={300}
                  value={c.zh}
                  onChange={(e) => captionChange(i, { zh: e.target.value })}
                />
              </label>
              {(['en','zh'] as const).map(l=><label key={l}>{t('Highlight words (comma-separated, up to 8)','强调词（逗号分隔，最多 8 个）')} · {l}<input maxLength={391} value={(c[`emphasis_${l}`]||[]).join(',')} onChange={e=>captionChange(i,{[`emphasis_${l}`]:e.target.value.split(/[,，]/)})} onBlur={e=>captionChange(i,{[`emphasis_${l}`]:e.target.value.split(/[,，]/).map(x=>x.trim()).filter(Boolean)})}/></label>)}
              <button
                onClick={() =>
                  change({ captions: edit.captions.filter((_, j) => j !== i) })
                }
              >
                {t("Remove subtitle", "删除字幕")}
              </button>
            </div>
          ))}
          <button
            disabled={edit.captions.length >= 160}
            onClick={() =>
              change({
                captions: [
                  ...edit.captions,
                  {
                    start: 0,
                    end: Math.min(3, duration),
                    original: "",
                    en: "",
                    zh: "",
                  },
                ],
              })
            }
          >
            {t("Add subtitle", "添加字幕")}
          </button>
        </fieldset>
      </details>
      <details><summary>{w('Расшифровка — не слой видео','Transcript — not a video layer','转录文本 — 不显示在视频中')}</summary>{edit.captions.map((c,i)=><p key={i}><small>{c.start.toFixed(1)}s</small> {c.original}</p>)}</details>
      </div>
      <div hidden={task!=='audio'}>
      <fieldset disabled={blocked} className="director-fieldset">
        <label>
          <input
            type="checkbox"
            checked={edit.normalize}
            onChange={(e) => change({ normalize: e.target.checked })}
          />
          {t(" Normalize overall audio loudness", " 统一整体音量")}
        </label>
        <p>
          {t(
            "This adjusts the mixed audio track, not the separate voice/music balance.",
            "此操作调整混合音轨的整体音量，不单独调整人声与音乐的比例。",
          )}
        </p>
      </fieldset>
      </div>
      {error && <p role="alert">{error}</p>}
      {invalidMusic&&<p role="alert">{t('Music points must start at 0, increase in time and stay between -40 and -6 dB.','音乐节点须从 0 秒开始，时间递增，音量介于 -40 至 -6 dB。')}</p>}
      {invalid && (
        <p role="alert">
          {t(
            "Check clip/subtitle/card/B-roll/sound ranges and fill all card fields in both languages. Enabled subtitles need at least one entry.",
            "请检查片段、字幕、卡片及补充镜头时间范围，并填写卡片的中英文内容。开启字幕时至少需要一条字幕。",
          )}
        </p>
      )}
      <details className="ws-render-options"><summary>{w("Проверка качества и стоимость","Quality review and cost","质量审核与费用")}</summary>
      <label><input type="checkbox" checked={qualityReview} disabled={blocked} onChange={e=>setQualityReview(e.target.checked)}/>{t('Review the finished video with AI and draft improvements if quality is low','使用 AI 复核成片，质量不足时生成改进草案')}</label>
      <p>{t('Review reserves up to $0.50, plus up to two $0.50 planning attempts if a revision is needed, within your project budget. New decisions require review; your finished video is preserved.','复核预留最多 $0.50；需要改进时最多再进行两次各 $0.50 的规划，受项目预算限制。新决策需审核，原成片保留。')}</p>
      </details>
      <p role="status">{blocked?t('Wait for the current task to finish.','请等待当前任务完成。'):invalid?t('Correct the validation errors above before saving or rendering.','请先修正上述校验错误再保存或制作。'):unapprovedCount>0?`${t('Shots awaiting approval','待批准镜头')}: ${unapprovedCount}. ${t('Approve each shot, then save your edits.','请逐个批准镜头，然后保存剪辑。')}`:dirty?t('Save your edits to enable rendering.','保存剪辑后即可制作。'):t('All shots approved and saved. Ready to render.','所有镜头已批准并保存，可以制作。')}</p>
      {task!=="review" && portal(<div className="manual-actions ws-edit-actions">
        <span role="status">
          {blocked?w('Дождитесь завершения задачи','Wait for the current task','请等待当前任务完成'):invalid?w('Исправьте ошибки настроек','Correct the settings errors','请修正设置错误'):unapprovedCount>0?`${w('Сцен для проверки','Scenes to review','待审核场景')}: ${unapprovedCount}`:dirty?t("Unsaved manual edits", "手动剪辑尚未保存"):t("Saved state", "已保存状态")}
        </span>
        <button
          disabled={blocked}
          onClick={() => {
            if (
              !dirty ||
              window.confirm(
                t("Discard unsaved manual edits?", "放弃未保存的手动剪辑？"),
              )
            ) {
              sessionStorage.removeItem(draftKey);
              void load();
            }
          }}
        >
          {w("Отменить правки","Discard edits","放弃更改")}
        </button>
        <button
          className="secondary"
          disabled={blocked || invalid || !dirty}
          onClick={() => void act()}
        >
          {t("Save manual edits", "保存手动剪辑")}
        </button>
        <button
          className="primary"
          disabled={blocked || invalid || dirty || unapprovedCount > 0}
          onClick={() => {reviewOpener.current=document.activeElement as HTMLElement;reviewDialog.current?.showModal();void loadRenderSummary()}}
        >
          {w("Проверить и создать версию","Review and create version","审核并创建版本")}
        </button>
      </div>,workspace?.actionsTarget)}
      <dialog className="ws-versions" ref={reviewDialog} onClose={()=>reviewOpener.current?.focus()}><h2>{w('Что изменится в видео','What will change in this video','视频将有哪些变化')}</h2>{renderSummary?.revision===revision?<RenderSummary data={renderSummary} lang={lang}/>:<div role="status"><p>{summaryError?w('Не удалось загрузить сводку. Попробуйте ещё раз.','Could not load the summary. Try again.','无法加载摘要，请重试。'):renderSummary?w('Монтаж изменился. Закройте окно и обновите редактор перед созданием видео.','The edit changed. Close this dialog and reload the editor before rendering.','剪辑已更改，请关闭窗口并刷新编辑器。'):w('Загружаем сохранённый план…','Loading the saved plan…','正在加载已保存的计划…')}</p>{summaryError&&<button onClick={()=>void loadRenderSummary()}>{w('Повторить','Retry','重试')}</button>}</div>}<p>{w('Готовая версия останется доступна. Новый ролик использует сохранённые настройки монтажа.','Your finished version stays available. The new video uses your saved edit settings.','已完成版本仍保留，新视频将使用已保存的剪辑设置。')}</p><p>{qualityReview?w('Включена платная AI-проверка: до $0.50 за проверку и до двух попыток улучшения по $0.50 в пределах бюджета проекта.','AI review is enabled: up to $0.50 for review and up to two $0.50 improvement attempts within the project budget.','已启用 AI 审核：审核最多 $0.50，改进最多两次、每次 $0.50，受项目预算限制。'):w('AI-проверка выключена. Монтаж не вызывает AI.','AI review is off. Rendering makes no AI calls.','AI 审核已关闭，制作不调用 AI。')}</p><div className="manual-actions"><button onClick={()=>reviewDialog.current?.close()}>{w('Вернуться к редактированию','Back to editing','返回编辑')}</button><button className="primary" disabled={blocked||invalid||dirty||unapprovedCount>0||renderSummary?.revision!==revision} onClick={()=>{reviewDialog.current?.close();void act(true)}}>{w('Создать видео с этими изменениями','Create video with these changes','按这些更改创建视频')}</button></div></dialog>
    </section>
  );
}
