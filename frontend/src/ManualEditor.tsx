import {EffectPick,type EffectPickData} from './SceneInspector';
import {RenderSummary,type RenderSummaryData} from './RenderSummary';
import {createPortal} from 'react-dom';
import {useWorkspace, workspaceText} from './ProjectWorkspace';
import type {ReactNode} from 'react';
import {SoundtrackLibrary} from './SoundtrackLibrary';
import { translate, contentLanguage } from './locale';
import {reviseDecision} from './decisionReview';
import {MusicPlan} from './MusicPlan';
import {FinalMusic,type FinalMusicHandle} from './FinalMusic';
import {BeatPreview} from './BeatPreview';
import {StockLibrary} from './StockLibrary';
import {MusicEditor,type Music} from './MusicEditor';
import type {SoundEffect} from './SoundEffectEditor';
import {MediaLibrary,AssetPlacement,type Asset,type ExternalBroll,type MediaLibraryHandle} from './MediaLibrary';
import type {Cutaway} from './CutawayEditor';
import type {VisualCard} from './VisualCardEditor';
import {TimelineRegenerate} from './TimelineRegenerate';
import {TimelineTracks} from './TimelineTracks';
import {ClipLayerTracks} from './ClipLayerTracks';
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
  motion_seconds?:number|null;
  zoom_end?: number|null; x_end?: number|null; y_end?: number|null;
  transition?: 'cut'|'fade'|'crossfade'|'zoom'|'wipe'|'wipe-up'|'wipe-down'|'circle'|'diagtl'|'diagtr'|'diagbl'|'diagbr';
  transition_seconds?: number|null;
  start: number;
  end: number;
  zoom: number;
  x: number;
  y: number;
  enhance?: boolean;
  speed?: number;
  speed_end?: number | null;
  blur?: number;
  glow?: boolean;
  glow_amount?: number;
  shadow?: boolean;
  shade?: number;
  split?: boolean;
  stabilize?: boolean;
  shake_rx?: number;
  cutout?: boolean;
  kinetic?: boolean;
  mask?: boolean;
  track?: boolean;
  exposure?: number;
  key_side?: 'left'|'right'|'top'|null;
  key_amount?: number;
  fill_side?: 'left'|'right'|'bottom'|null;
  fill_amount?: number;
  rim_amount?: number;
  progress?: number;
  graphic?: boolean;
  bars?: number[];
  lower?: boolean;
  icon?: boolean;
  mark?: number;
  effect_at?: number;
  effect_end?: number;
  title_in?: number;
  title_out?: number;
  title_x?: number | null;
  kinetic_at?: number[];
  progress_at?: number;
  progress_end?: number;
  still?: number | null;
  screen?: number | null;
  bezel?: number;
  diagram?: number;
  art?: string;
  picture_insert?: {start:number;end:number;at?:number}|null;
  panel?: number | null;
  plate?: string;
  grade?: {brightness:number;contrast:number;saturation:number;gamma:number;rs:number;gs:number;bs:number}|null;
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
  voice_cleanup?: boolean;
  picture_quality?: boolean;
  presentation_share?: number;
  presentation_prompt?: string;
  presentation?: {kind:'window'|'mini';start:number;end:number;title:{en:string;zh:string;ru:string};body?:{en:string;zh:string;ru:string}|null;x:number;y:number}[];
  card_motion?: number;
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
  const [delivery,setDelivery]=useState<{render_id?:string;picture_pending:boolean|null;rendered_scenes:number|null;unapproved_scenes:number;separate_audio:boolean}|null>(null);
  const summaryRequest=useRef(0);
  async function loadRenderSummary(){
    const request=++summaryRequest.current;
    setRenderSummary(null);setSummaryError(false);
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),12000);
    try{const r=await fetch(base+'/summary',{signal:controller.signal});if(!r.ok)throw Error();const data=await r.json();if(request===summaryRequest.current)setRenderSummary(data)}
    catch{if(request===summaryRequest.current)setSummaryError(true)}
    finally{clearTimeout(timer)}
  }
  const reviewDialog=useRef<HTMLDialogElement>(null);
  const reviewOpener=useRef<HTMLElement|null>(null);
  const mediaLibrary = useRef<MediaLibraryHandle>(null);
  const [edit, setEdit] = useState<Edit | null>(null),
    [revision, setRevision] = useState(0),
    [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [playError, setPlayError] = useState(""),
    [selected, setSelected] = useState(0),
    [before, setBefore] = useState(false),
    [time, setTime] = useState(0);
  const [matchRequest,setMatchRequest]=useState<{clipId:string;assetIds:string[];instruction:string;nonce:number}|null>(null);
  const [qualityReview,setQualityReview]=useState(true);
  const video = useRef<HTMLVideoElement>(null),
    pending = useRef<number | null>(null),
    editRef = useRef<Edit | null>(null),
    revisionRef = useRef(0),
    shareTicket = useRef(0),
    shareTimer = useRef<number | undefined>(undefined),
    motionTimer = useRef<number | undefined>(undefined);
  const [shareNote, setShareNote] = useState("");
  const [cardNote, setCardNote] = useState("");
  const [effectPick, setEffectPick] = useState<EffectPickData | null>(null);
  const [effectError, setEffectError] = useState("");
  const [effectNote, setEffectNote] = useState("");
  const [effectBusy, setEffectBusy] = useState(false);
  const effectTicket = useRef(0);
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
      setDelivery(data.delivery||null);
      setEdit(draft?.edit || data.edit);
      revisionRef.current = data.revision;
      setRevision(data.revision);
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
  useEffect(()=>{let live=true;fetch(base).then(r=>r.ok?r.json():null).then(data=>{if(live)setDelivery(data?.delivery||null)}).catch(()=>{if(live)setDelivery(null)});return()=>{live=false}},[pid,revision,workspace?.renderId,workspace?.finalAudioId]);
  useEffect(()=>{
    if (!edit || serverRevision===undefined || serverRevision===revision) return;
    if (!dirty) { void load(); return; }
    revisionRef.current = serverRevision;
    setRevision(serverRevision);
  },[serverRevision, dirty, edit, revision]);
  const blocked = disabled || busy;
  editRef.current = edit;
  revisionRef.current = revision;
  function presentationMessage(detail: unknown) {
    return detail === "presentation_needs_context"
      ? w(
          "Сначала нужен текст речи или сцены. Скан не нашёл, о чём говорить в анимации.",
          "The scan needs speech or scene text before it can place animation.",
          "扫描需要语音或场景文字，才能安排动画。",
        )
      : detail === "plan_changed"
        ? t("The plan changed. Reload saved edits before continuing.", "计划已更新，请重新加载已保存的剪辑。")
        : detail === "job_already_running"
          ? w("Дождитесь завершения текущей задачи.", "Wait for the current task to finish.", "请等待当前任务完成。")
          : t("Check time ranges, subtitle text and whether another job is running.", "请检查时间范围、字幕文字，以及是否有任务正在运行。");
  }
  function change(p: Partial<Edit>, preview = true) {
    setEdit((e) => (e ? { ...e, ...p } : e));
    setDirty(true);
    if(preview)workspace?.showDraft();
  }
  function clipChange(i: number, p: Partial<Clip>) {
    if (edit)
      change({
        clips: edit.clips.map((c, j) => (i === j ? reviseDecision(c,p) : c)),
      });
  }
  const framingField = (c: Clip, i: number, key: "start" | "end" | "zoom") => (
    <label key={key} className={key === "start" || key === "end" ? "inspector-time" : "inspector-slider"}>
      {{
        start: t("Source start (s)", "原片开始（秒）"),
        end: t("Source end (s)", "原片结束（秒）"),
        zoom: t("Zoom (1–3×)", "缩放（1–3 倍）"),
      }[key]}
      <input
        type={key === "start" || key === "end" ? "number" : "range"}
        step={key === "start" || key === "end" ? 0.1 : 0.05}
        min={key === "zoom" ? 1 : 0}
        max={key === "zoom" ? 3 : duration}
        value={c[key]}
        onChange={(e) => clipChange(i, { [key]: Number(e.target.value) })}
      />
      {key !== "start" && key !== "end" && <output>{c[key].toFixed(2)}{key === "zoom" ? "×" : ""}</output>}
    </label>
  );
  function captionChange(i: number, p: Partial<Caption>) {
    if (edit)
      change({
        captions: edit.captions.map((c, j) => (i === j ? { ...c, ...p } : c)),
      });
  }
  const finalMusic = useRef<FinalMusicHandle>(null);
  async function act(render = false) {
    if (!edit) return null;
    let savedRevision=revisionRef.current || revision;
    setBusy(true);
    setError("");
    try {
      let rev = savedRevision;
      let r: Response | null = null;
      let detail: unknown;
      for (let attempt = 0; attempt < 2; attempt++) {
        r = await fetch(base + (render ? "/render" : ""), {
          method: render ? "POST" : "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(render ? { revision: rev, quality_review: qualityReview } : { revision: rev, edit }),
        });
        if (r.ok) break;
        const d = await r.json().catch(() => ({}));
        detail = d.detail;
        if (detail !== "plan_changed" || render || attempt > 0) break;
        const fresh = await fetch(base);
        if (!fresh.ok) break;
        const current = await fresh.json();
        rev = current.revision;
        revisionRef.current = current.revision;
        setRevision(current.revision);
      }
      if (!r || !r.ok) {
        throw Error(
          detail === "plan_changed"
            ? t(
                "The plan changed. Reload saved edits before continuing.",
                "计划已更新，请重新加载已保存的剪辑。",
              )
            : detail === "presentation_needs_context"
              ? w(
                  "Сначала нужен текст речи или сцены. Скан не нашёл, о чём говорить в анимации.",
                  "The scan needs speech or scene text before it can place animation.",
                  "扫描需要语音或场景文字，才能安排动画。",
                )
            : t(
                "Check time ranges, subtitle text and whether another job is running.",
                "请检查时间范围、字幕文字，以及是否有任务正在运行。",
              ),
        );
      }
      if (!render) {
        const d = await r.json();
        savedRevision=d.revision;
        setRevision(d.revision);
        setEdit(d.edit);
        setDirty(false);
        sessionStorage.removeItem(draftKey);
      }
      await onSaved();
      return savedRevision;
    } catch (e) {
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  function setCardMotion(value: number) {
    const motion = Math.max(0, Math.min(100, Math.round(value / 5) * 5));
    const current = editRef.current;
    if (!current || (current.card_motion ?? 100) === motion) return;
    const next = { ...current, card_motion: motion };
    editRef.current = next;
    setEdit(next);
    setDirty(true);
    setCardNote("");
    window.clearTimeout(motionTimer.current);
    motionTimer.current = window.setTimeout(() => { void saveCardMotion(motion); }, 250);
  }
  async function saveCardMotion(motion: number) {
    const current = editRef.current;
    if (!current || (current.card_motion ?? 100) !== motion) return;
    setCardNote(w("Сохраняю уровень карточек…", "Saving the card level…", "正在保存卡片动画…"));
    try {
      const save = await fetch(base, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: revisionRef.current, edit: current }),
      });
      const stored = await save.json().catch(() => ({}));
      if ((editRef.current?.card_motion ?? 100) !== motion) return;
      if (!save.ok || !stored.edit) throw Error(presentationMessage(stored.detail));
      editRef.current = stored.edit;
      revisionRef.current = stored.revision;
      setEdit(stored.edit);
      setRevision(stored.revision);
      setDirty(false);
      sessionStorage.removeItem(draftKey);
      setCardNote(w(
        "Уровень сохранён. Соберите видео заново, чтобы увидеть его в ролике.",
        "Saved. Create the video again to see it in the picture.",
        "已保存。请重新生成视频后在画面中查看。",
      ));
      await onSaved();
    } catch (e) {
      if ((editRef.current?.card_motion ?? 100) !== motion) return;
      setCardNote((e as Error).message);
    }
  }
  function effectMessage(detail: unknown) {
    return detail === "no_open_picture"
      ? w("Нет открытого фрагмента, который попадёт в ролик.", "There is no open piece the render will use.", "没有会进入成片的开放片段。")
      : detail === "effect_unavailable"
        ? w("Для этой картинки уже включены эффекты, которые меняют ролик.", "This picture already has effects the render will use.", "这个画面已经有会改变成片的效果。")
        : detail === "plan_changed"
          ? t("The plan changed. Reload saved edits before continuing.", "计划已更新，请重新加载已保存的剪辑。")
          : w("Не удалось подобрать эффект. Повторите.", "Could not pick an effect. Try again.", "无法建议效果，请重试。");
  }
  async function loadEffect() {
    const current = editRef.current;
    if (!current) return;
    const ticket = ++effectTicket.current;
    setEffectBusy(true);
    setEffectError("");
    try {
      const response = await fetch(`${base}/effect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: revisionRef.current, edit: current }),
      });
      const data = await response.json().catch(() => ({}));
      if (ticket !== effectTicket.current) return;
      if (!response.ok || !data?.id) throw Error(effectMessage(data?.detail));
      setEffectPick(data);
      setEffectNote("");
    } catch (e) {
      if (ticket !== effectTicket.current) return;
      setEffectPick(null);
      setEffectError((e as Error).message);
    } finally {
      if (ticket === effectTicket.current) setEffectBusy(false);
    }
  }
  async function acceptEffect() {
    const current = editRef.current;
    const pick = effectPick;
    if (!current || !pick) return;
    const clips = current.clips.map((clip) => {
      const patch = pick.clips?.[clip.id || ""] as Partial<Clip> | undefined;
      return patch ? { ...clip, ...patch } : clip;
    });
    const next = { ...current, clips, ...(pick.edit?.card_motion != null ? { card_motion: pick.edit.card_motion } : {}) };
    editRef.current = next;
    setEdit(next);
    setEffectBusy(true);
    setEffectError("");
    setEffectNote(w("Сохраняю эффект…", "Saving the look…", "正在保存效果…"));
    try {
      const save = await fetch(base, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: revisionRef.current, edit: next }),
      });
      const stored = await save.json().catch(() => ({}));
      if (!save.ok || !stored.edit) throw Error(effectMessage(stored.detail));
      editRef.current = stored.edit;
      revisionRef.current = stored.revision;
      setEdit(stored.edit);
      setRevision(stored.revision);
      setDirty(false);
      sessionStorage.removeItem(draftKey);
      setEffectNote(w(
        "Образ сохранён. Соберите видео заново, чтобы увидеть его в ролике.",
        "Look saved. Create the video again to see it.",
        "效果已保存。请重新生成视频后在画面中查看。",
      ));
      await onSaved();
    } catch (e) {
      setEffectError((e as Error).message);
      setEffectNote("");
    } finally {
      setEffectBusy(false);
    }
  }
  useEffect(() => {
    if (task !== "effects" || !edit) return;
    void loadEffect();
  }, [task, pid, Boolean(edit)]);
  function setPresentationShare(value: number) {
    const share = Math.max(0, Math.min(100, Math.round(value / 5) * 5));
    const current = editRef.current;
    if (!current || share === (current.presentation_share || 0)) return;
    const next = { ...current, presentation_share: share, ...(share === 0 ? { presentation: [] } : {}) };
    editRef.current = next;
    setEdit(next);
    setDirty(true);
    setShareNote("");
    const ticket = ++shareTicket.current;
    window.clearTimeout(shareTimer.current);
    shareTimer.current = window.setTimeout(() => { void commitPresentationShare(share, ticket); }, 200);
  }
  async function commitPresentationShare(share: number, ticket: number) {
    const current = editRef.current;
    if (!current || ticket !== shareTicket.current || (current.presentation_share || 0) !== share) return;
    setShareNote(w("Сохраняю долю в проект…", "Saving this share to the project…", "正在把比例保存到项目…"));
    try {
      let planned: Edit = { ...current, presentation_share: share, ...(share === 0 ? { presentation: [] } : {}) };
      if (share > 0) {
        const scanned = await fetch(base + "/presentation", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ revision: revisionRef.current, edit: planned }),
        });
        const data = await scanned.json().catch(() => ({}));
        if (ticket !== shareTicket.current) return;
        if (!scanned.ok || !data.edit) throw Error(presentationMessage(data.detail));
        const latest = editRef.current;
        planned = !latest || (latest.presentation_share || 0) !== share
          ? data.edit
          : { ...data.edit, ...latest, presentation: data.edit.presentation, presentation_share: share };
      }
      const save = await fetch(base, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ revision: revisionRef.current, edit: planned }),
      });
      const stored = await save.json().catch(() => ({}));
      if (ticket !== shareTicket.current) return;
      if (!save.ok || !stored.edit) throw Error(presentationMessage(stored.detail));
      editRef.current = stored.edit;
      revisionRef.current = stored.revision;
      setEdit(stored.edit);
      setRevision(stored.revision);
      setDirty(false);
      sessionStorage.removeItem(draftKey);
      setShareNote(w(
        "Доля сохранена в проект. Соберите видео заново, чтобы увидеть её в ролике.",
        "Saved to this project. Create the video again to see it in the picture.",
        "比例已保存到项目。请重新生成视频后在画面中查看。",
      ));
      workspace?.showDraft();
      await onSaved();
    } catch (e) {
      if (ticket !== shareTicket.current) return;
      setShareNote((e as Error).message);
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
    setPlayError("");
    void video.current.play().catch(() => {
      setPlayError(t("Could not play this preview.", "无法播放此预览。"));
    });
  }
  if (!edit)
    return (
      <section className="director-card">
        <h3>{t("Manual editor", "手动剪辑")}</h3>
        <p role="status">{error || t("Loading editor…", "正在加载编辑器…")}</p>
        <button onClick={() => void load()}>{t("Reload", "重新加载")}</button>
      </section>
    );
  function openReview(){reviewOpener.current=document.activeElement as HTMLElement;reviewDialog.current?.showModal();if(!dirty)void loadRenderSummary()}
  const clip = edit.clips[selected] || edit.clips[0];
  const progress=Math.max(0,Math.min(1,(time-clip.start)/Math.min(clip.end-clip.start,clip.motion_seconds||clip.end-clip.start)));
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
        c.end > duration + 0.05 ||
        c.end - c.start < 0.08 ||
        (c.motion_seconds!=null&&(!Number.isFinite(c.motion_seconds)||c.motion_seconds<.08||c.motion_seconds>840)) ||
        !Number.isFinite(c.zoom) || c.zoom < 1 || c.zoom > 3 ||
        !Number.isFinite(c.x) || c.x < 0 || c.x > 1 ||
        !Number.isFinite(c.y) || c.y < 0 || c.y > 1,
    ) ||
    edit.captions.some(
      (c) => c.start < 0 || c.end > duration + 0.05 || c.end <= c.start,
    ) ||
    (edit.subtitles && (!edit.captions.length || edit.captions.some(c=>![c.en,c.zh,c.original].some(text=>text.trim()))));
  return (
    <section
      className="director-card manual-editor"
      aria-label={t("Manual editor", "手动剪辑")}
    >
      <div hidden={task!=="audio"}>
      <MusicPlan onUploadMusic={()=>{workspace?.setTask('materials');requestAnimationFrame(()=>mediaLibrary.current?.openMusicUpload())}} onUse={music=>change({music},false)} onAssetsChanged={loadAssets} currentMusic={edit.music} pid={pid} revision={revision} assets={assets.filter(a=>a.metadata.kind==='music')} lang={lang} suggestDisabled={blocked||dirty||!!edit.music?.locked} onApplied={async nextRevision=>{sessionStorage.removeItem(draftKey);await load();await onSaved();await finalMusic.current?.apply(nextRevision)}}/>
      <MusicEditor delivery={<FinalMusic ref={finalMusic} pid={pid} lang={lang} music={edit.music||null} disabled={blocked||invalid} save={()=>act(false)}/>} pid={pid} onAnalyzed={loadAssets} firstCut={edit.clips.filter(c=>c.approved!==false).length>1?(()=>{const c=edit.clips.find(c=>c.approved!==false)!;return c.end-c.start})():null} value={edit.music||null} assets={assets.filter(a=>a.metadata.kind==='music')} lang={lang} disabled={blocked} onChange={music=>change({music},false)}/>
      {edit.music&&<BeatPreview pid={pid} revision={revision} lang={lang} disabled={blocked||dirty} onPreview={value=>{setEdit(value);setDirty(true)}}/>}
      <div className="scene-choices">
        <label className="scene-choice">
          <input type="checkbox" checked={!!edit.voice_cleanup} disabled={blocked} onChange={e=>change({voice_cleanup:e.target.checked})} />
          <span>
            <strong>{w('Убрать лишние звуки из основной речи','Remove extra sound from the main speech','去除主语音中的多余声音')}</strong>
            <small>{w('Шипение, гул и посторонние звуки уходят из речи. Музыка добавляется позже и остаётся.','Hiss, rumble, and other extra sounds leave the speech. Music is mixed in afterwards and stays.','嘶声、低频杂音和其他多余声音会从语音中去掉。音乐随后混入并保留。')}</small>
          </span>
        </label>
      </div>
      <details className="audio-voiceover"><summary>{w('Озвучка и язык','Voiceover and language','配音与语言')}</summary>{voiceover}</details>
      <details className="audio-library"><summary>{w('Библиотека музыки','Music library','音乐库')}</summary><SoundtrackLibrary pid={pid} lang={lang} full={assets.length>=20} onChanged={loadAssets}/></details>
      </div>
      <div hidden={task!=="materials"}>
      <MediaLibrary ref={mediaLibrary} pid={pid} lang={lang} assets={assets} onChanged={loadAssets}/>
      </div>
      <div hidden={task!=="materials"}>
      <StockLibrary onMatch={ids=>{if(!clip.id||blocked||dirty||clip.locked)return;workspace?.setTask('effects');setMatchRequest({clipId:clip.id,assetIds:ids,instruction:t('Choose a visually relevant sampled moment for this scene and its narration. Preserve original speech. If none fits, propose no replacement.','为当前场景与旁白选择视觉相关的样本片段，保留原声。如无合适素材，请勿替换。'),nonce:Date.now()})}} pid={pid} lang={lang} onChanged={loadAssets} assets={assets} revision={revision} scene={{id:clip.id,label:`${selected+1} · ${clip.start.toFixed(1)}–${clip.end.toFixed(1)}s`,context:[clip.text,...edit.captions.filter(c=>c.end>clip.start&&c.start<clip.end).map(c=>c[contentLanguage(lang)]||c.original)].filter(Boolean).join(' ').slice(0,1000),disabled:blocked||dirty||!!clip.locked}} onPlace={id=>{const asset=assets.find(a=>a.id===id);if(!asset||blocked||clip.locked)return;const length=Math.min(clip.end-clip.start,asset.metadata.duration,4);if(length<=0)return;clipChange(selected,{external_broll:{asset_id:id,start:0,end:length,source_start:0},cutaway:null,approved:false});}}/>
      </div>
      {portal(<section className="ws-scene-list"><details><summary>{w('Дорожки таймлайна','Timeline tracks','时间轴轨道')}</summary>      <TimelineTracks hasAudio={hasAudio} key={pid} musicAsset={assets.find(a=>a.id===edit.music?.asset_id)} music={edit.music} clips={edit.clips} captions={edit.captions} subtitles={edit.subtitles} lang={lang} onSelect={i=>{setSelected(i);workspace?.showDraft()}} />
</details></section>,workspace?.scenesTarget)}
      <div hidden={task!=='edit'&&task!=='effects'}>
      {task==='effects'&&<section className="presentation-share" aria-label={w('Анимация карточек','Card animation','卡片动画')}>
        <label className="inspector-slider">
          {w('Анимация карточек, %','Card animation, %','卡片动画，%')}
          <input type="range" min={0} max={100} step={5} value={edit.card_motion??100} aria-label={w('Анимация карточек, %','Card animation, %','卡片动画，%')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={edit.card_motion??100} aria-valuetext={`${edit.card_motion??100}%`} onChange={e=>setCardMotion(Number(e.target.value))} />
          <output>{edit.card_motion??100}%</output>
        </label>
        {cardNote&&<p role="status">{cardNote}</p>}
        <small>{w('0% убирает карточки. 100% оставляет их на всю длину и с полным появлением. Промежуточное значение укорачивает карточки и смягчает движение. Соберите ролик заново.','0% removes the cards. 100% keeps them for their full length, with the full entrance. A value between shortens the cards and softens the motion. Create the video again.','0% 会去掉卡片。100% 会保留完整时长和完整入场。中间值会缩短卡片并减弱动作。请重新生成视频。')}</small>
      </section>}
      {task==='effects'&&<EffectPick lang={lang} pick={effectPick} error={effectError} busy={effectBusy} note={effectNote} onAccept={()=>void acceptEffect()} onRetry={()=>void loadEffect()}/>}
      {task==='effects'&&<section className="presentation-share" aria-label={w('Промпт Hypit','Hypit prompt','Hypit 提示')}>
        <label className="inspector-slider">
          {w('Промпт Hypit, %','Hypit prompt, %','Hypit 提示比例')}
          <input type="range" min={0} max={100} step={5} value={edit.presentation_share||0} aria-label={w('Промпт Hypit, %','Hypit prompt, %','Hypit 提示比例')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={edit.presentation_share||0} aria-valuetext={`${edit.presentation_share||0}%`} onChange={e=>setPresentationShare(Number(e.target.value))} />
          <output>{edit.presentation_share||0}%</output>
        </label>
        {shareNote&&<p role="status">{shareNote}</p>}
        {(edit.presentation_share||0)>0&&<p className="presentation-prompt">{w(
          `Промпт Hypit: использовать фреймворк Hypit на ${edit.presentation_share}% готового видео. Движущиеся 3D-окна и мини-презентации ставятся на отсканированную речь.`,
          `Hypit prompt: use the Hypit framework on ${edit.presentation_share}% of the finished video. Moving 3D windows and mini presentations sit on the scanned speech.`,
          `Hypit 提示：在成片的 ${edit.presentation_share}% 上使用 Hypit 框架。移动的 3D 窗口和迷你演示落在扫描到的讲话上。`,
        )}</p>}
        <small>{w('Шаг 5%. Число становится процентом в промпте Hypit: фреймворк занимает графикой именно эту долю ролика. Скан сначала читает речь. Слова на экране идут на языке озвучки, а если её нет — на языке проекта.','Steps of 5%. The number becomes the percentage in the Hypit prompt: the framework covers exactly that share of the video with graphics. The scan reads the speech first. On-screen words follow the voiceover language, or the project language when there is no voiceover.','步长为 5%。这个数字会写入 Hypit 提示的百分比：框架只用图形覆盖成片的这一比例。扫描会先读取语音。画面文字跟随配音语言；没有配音时使用项目语言。')}</small>
        {(edit.presentation||[]).length>0&&<p role="status">{w('Скан поставил','The scan placed','扫描已放置')} {(edit.presentation||[]).filter(b=>b.kind==='window').length} {w('окон','windows','个窗口')} · {(edit.presentation||[]).filter(b=>b.kind==='mini').length} {w('мини-презентаций','mini presentations','个迷你演示')} · {(edit.presentation||[]).reduce((sum,b)=>sum+b.end-b.start,0).toFixed(1)} {w('с','s','秒')}</p>}
        {(edit.presentation||[]).length>0&&<ol>{(edit.presentation||[]).map((beat,index)=>{const line=lang==='zh'?beat.title.zh:lang==='ru'?beat.title.ru:beat.title.en;return <li key={index}>{beat.kind==='mini'?w('Мини-презентация','Mini presentation','迷你演示'):w('3D-окно','3D window','3D 窗口')} · {beat.start.toFixed(1)}–{beat.end.toFixed(1)} {w('с','s','秒')} · {line}</li>})}</ol>}
      </section>}
      <section className="inspector-scene-controls">
        <fieldset disabled={blocked} className="director-fieldset">
          {edit.clips.map((c, i) => (
            <article className="manual-clip" hidden={!!workspace&&selected!==i} key={c.id||i}>
<p className="inspector-review-hint">{w('Изменения снимают подтверждение сцены.','Changes clear this scene’s approval.','修改后需要重新批准场景。')}</p>
              <div className="scene-choices">
                <label className="scene-choice">
                  <input type="checkbox" checked={c.approved!==false} disabled={c.locked} aria-label={w('Включить в ролик','Include in the cut','纳入成片')} aria-describedby={`scene-include-${c.id||i}`} title={c.locked?w('Снимите заморозку тайминга, чтобы исключить сцену','Unfreeze timing before leaving this scene out','取消冻结后才能移出成片'):undefined} onChange={e=>clipChange(i,{approved:e.target.checked})}/>
                  <span><strong>{w('Включить в ролик','Include in the cut','纳入成片')}</strong><small id={`scene-include-${c.id||i}`}>{w('Сцена входит в финальное видео.','This scene is part of the finished video.','此场景会进入成片。')}</small></span>
                </label>
                <label className="scene-choice">
                  <input type="checkbox" checked={!!c.locked} disabled={c.approved===false} aria-label={w('Заморозить тайминг','Freeze timing','冻结时间')} aria-describedby={`scene-freeze-${c.id||i}`} title={c.approved===false?w('Сначала включите сцену в ролик','Include the scene in the cut first','请先将场景纳入成片'):undefined} onChange={e=>clipChange(i,{locked:e.target.checked})}/>
                  <span><strong>{w('Заморозить тайминг','Freeze timing','冻结时间')}</strong><small id={`scene-freeze-${c.id||i}`}>{w('Начало и конец этой сцены не меняются.','The start and end of this scene stay fixed.','此场景的起止时间保持不变。')}</small></span>
                </label>
              </div>
              <fieldset className="director-fieldset" disabled={c.locked}>
              <div className="scene-timing">
                <p className="scene-timing-title">{w('Время и приближение этой сцены','Timing and zoom for this scene','此场景的时间与缩放')}</p>
                <div className="manual-grid ws-framing-grid">{(["start","end","zoom"] as const).map(key=>framingField(c,i,key))}</div>
              </div>
              <section className="inspector-transition"><label>{t('Transition','转场')}<select value={c.transition||'cut'} onChange={e=>clipChange(i,{transition:e.target.value as Clip['transition']})}><option value="cut">{t('Straight cut','直接切换')}</option><option value="crossfade" disabled={i===0}>{t('Cross dissolve','叠化')}</option><option value="fade">{t('Fade through black','淡入淡出至黑场')}</option></select></label>{i===0&&<small>{w('У первой сцены нет входящего перехода. Можно использовать затухание через чёрный.','The first scene has no incoming transition. You can use a fade through black.','第一个镜头没有入场转场，可以使用黑场淡入淡出。')}</small>}{c.transition&&!['cut','crossfade','fade'].includes(c.transition)&&<small>{w('Этот переход уже выбран AI и останется в ролике.','This transition was chosen by AI and stays in the video.','此转场由 AI 选择，会保留在成片中。')}</small>}</section>
              <ClipLayerTracks clip={c} lang={lang} playhead={selected===i?time-c.start:null}/>
              <details className="inspector-text"><summary>{w('Текст на сцене','Scene text','镜头文字')}{c.text&&<span className="inspector-dot"/>}</summary><label>
                {t("Text overlay for this clip", "此片段的叠加文字")}
                <input
                  maxLength={160}
                  value={c.text}
                  onChange={(e) => clipChange(i, { text: e.target.value })}
                />
              </label>
              </details>
              <div className="inspector-inserts">
              <AssetPlacement value={c.external_broll||null} assets={assets.filter(a=>a.metadata.kind!=='music')} duration={c.end-c.start} lang={lang} onChange={external_broll=>clipChange(i,{external_broll,...(external_broll?{cutaway:null}:{})})}/>
              {(!!c.sound_effects?.length||!!c.card||!!c.cutaway)&&<p>{w('Карточки, звуковые акценты и перебивки из своего ролика задаёт AI.','Cards, sound accents and cutaways from this video are chosen by AI.','卡片、音效和原片切出由 AI 决定。')}{!!c.sound_effects?.length&&<button type="button" onClick={()=>clipChange(i,{sound_effects:[]})}>{w('Убрать звуковые акценты','Remove sound accents','移除音效')}</button>}{!!c.card&&<button type="button" onClick={()=>clipChange(i,{card:null})}>{w('Убрать карточку','Remove visual insert','移除视觉插入')}</button>}{!!c.cutaway&&<button type="button" onClick={()=>clipChange(i,{cutaway:null})}>{w('Убрать перебивку','Remove cutaway','移除补充镜头')}</button>}</p>}
              </div>

              </fieldset>
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
                    workspace?.showDraft();
                    pending.current=c.start;
                    if(video.current){
                      video.current.pause();
                      video.current.currentTime=c.start;
                      if(video.current.readyState>=1)pending.current=null;
                    }
                    setTime(c.start);
                  }}
                >
                  {t("Inspect", "查看")}
                </button>
              </div>
              </details>
            </article>
          ))}
        </fieldset>
        <p>
          {t(
            "Times refer to the original footage. Repeated ranges repeat that footage; omitted ranges are cut. Check that cuts preserve complete speech.",
            "时间对应原片。重复范围会重复播放，未选范围会被剪掉。请确保剪切不截断讲话。",
          )}
        </p>
      </section>
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
        {playError && <p role="alert">{playError}</p>}
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
      <details className="ws-editor-help"><summary>{w("Как работает редактор","How editing works","编辑器说明")}</summary>
      <p>
        {t(
          "Timing, zoom, subtitles and scene order here override the AI plan for this render. Crop, wipes, charts, sound accents and extra clips stay with AI. Saving is free.",
          "这里的时间、缩放、字幕和场景顺序会覆盖本次 AI 计划。裁剪、擦除、图表、音效和额外片段仍由 AI 决定。保存免费。",
        )}
      </p>
      <div hidden={task!=="edit"}>
      <button className="secondary" disabled={blocked||dirty||edit.clips.some(c=>c.locked)} onClick={async()=>{setBusy(true);setError('');try{const r=await fetch(base+'/from-plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision})});if(!r.ok)throw Error(t('Save or reload the latest plan first.','请先保存或重新加载最新计划。'));const data=await r.json();setEdit(data.edit);setDirty(true);setSelected(0);}catch(e){setError((e as Error).message)}finally{setBusy(false)}}}>{t('Build timeline from approved AI edits','根据已批准的 AI 改动建立时间线')}</button>
      </div>
      </details>
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
      {workspace?.deliveryTarget&&portal(<>
        {(dirty||delivery?.picture_pending)&&<div className="ws-delivery-warning" role="status"><strong>{w('Правки ещё не в финальном видео','Edits are not in the final video yet','更改尚未包含在最终视频中')}</strong><p>{dirty?w('Есть несохранённый черновик. Финальное видео остаётся прежним до создания новой версии.','There is an unsaved draft. The final video stays unchanged until you create a new version.','存在未保存草稿，创建新版本前最终视频保持不变。'):w('Сохранённое изображение отличается от готового видео. Сохранение настроек не запускает рендер.','The saved picture edit differs from the finished video. Saving settings does not render it.','已保存画面剪辑与成片不同。')}</p>{delivery?.separate_audio&&<p>{w('Озвучка или музыка обновлены отдельно; это не применяет монтаж изображения.','Voiceover or music was updated separately; that does not apply picture edits.','配音或音乐已单独更新，但不会应用画面剪辑。')}</p>}<button onClick={openReview}>{w('Проверить правки и создать версию','Review edits and create a version','审核更改并创建版本')}</button></div>}
      </>,workspace.deliveryTarget)}
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
          onClick={openReview}
        >
          {w("Проверить и создать версию","Review and create version","审核并创建版本")}
        </button>
      </div>,workspace?.actionsTarget)}
      <dialog className="ws-versions" ref={reviewDialog} onClose={()=>reviewOpener.current?.focus()}><h2>{w('Что изменится в видео','What will change in this video','视频将有哪些变化')}</h2>
      {blocked&&<p role="status">{w('Дождитесь завершения текущей задачи.','Wait for the current task to finish.','请等待当前任务完成。')}</p>}
      {error&&<p role="alert">{error}</p>}
      {invalid&&<p role="alert">{t('Check clip/subtitle/card/B-roll/sound ranges and fill all card fields in both languages. Enabled subtitles need at least one entry.','请检查片段、字幕、卡片及补充镜头时间范围，并填写卡片的中英文内容。开启字幕时至少需要一条字幕。')}</p>}
      {unapprovedCount>0&&<section className="review-preflight"><h3>{w('Подтвердите сцены перед созданием видео','Approve scenes before creating the video','创建视频前请批准场景')}</h3>
        {edit.clips.map((c,i)=>c.approved===false&&<div key={c.id||i} className="review-scene">
          <strong>{w('Сцена','Scene','场景')} {i+1} · {c.start.toFixed(1)}–{c.end.toFixed(1)}s</strong>
          {c.text&&<p>{c.text}</p>}
          <div className="manual-actions"><button onClick={()=>{reviewDialog.current?.close();setSelected(i);workspace?.setTask('edit');workspace?.showDraft();pending.current=c.start;setTime(c.start);if(video.current)video.current.currentTime=c.start;}}>{w('Посмотреть сцену','Inspect scene','查看场景')}</button>
          <button disabled={blocked||!!c.locked} onClick={()=>clipChange(i,{approved:true})}>{w('Подтвердить сцену','Approve scene','批准场景')} {i+1}</button></div>
        </div>)}
      </section>}
      {dirty?<section className="review-preflight"><p>{w('Есть несохранённые изменения. Сохраните их, чтобы проверить точный состав новой версии. Видео пока не создаётся.','There are unsaved changes. Save them to review exactly what the new version will contain. This does not create a video.','存在未保存更改。保存后查看新版本的准确内容，此操作不会创建视频。')}</p><button disabled={blocked||invalid} onClick={async()=>{if(await act(false)!==null)await loadRenderSummary()}}>{w('Сохранить и обновить сводку','Save and refresh summary','保存并更新摘要')}</button></section>:renderSummary?.revision===revision?<RenderSummary data={renderSummary} lang={lang} onReviewProposals={workspace?()=>{reviewDialog.current?.close();workspace.setTask('review')}:undefined}/>:<div role="status"><p>{summaryError?w('Не удалось загрузить сводку. Попробуйте ещё раз.','Could not load the summary. Try again.','无法加载摘要，请重试。'):renderSummary?w('Монтаж изменился. Закройте окно и обновите редактор перед созданием видео.','The edit changed. Close this dialog and reload the editor before rendering.','剪辑已更改，请关闭窗口并刷新编辑器。'):w('Загружаем сохранённый план…','Loading the saved plan…','正在加载已保存的计划…')}</p>{summaryError&&<button onClick={()=>void loadRenderSummary()}>{w('Повторить','Retry','重试')}</button>}</div>}<p>{w('Готовая версия останется доступна. Новый ролик использует сохранённые настройки монтажа.','Your finished version stays available. The new video uses your saved edit settings.','已完成版本仍保留，新视频将使用已保存的剪辑设置。')}</p><p>{qualityReview?w('Включена платная AI-проверка: до $0.50 за проверку и до двух попыток улучшения по $0.50 в пределах бюджета проекта.','AI review is enabled: up to $0.50 for review and up to two $0.50 improvement attempts within the project budget.','已启用 AI 审核：审核最多 $0.50，改进最多两次、每次 $0.50，受项目预算限制。'):w('AI-проверка выключена. Монтаж не вызывает AI.','AI review is off. Rendering makes no AI calls.','AI 审核已关闭，制作不调用 AI。')}</p><div className="manual-actions"><button onClick={()=>reviewDialog.current?.close()}>{w('Вернуться к редактированию','Back to editing','返回编辑')}</button><button className="primary" disabled={blocked||invalid||dirty||unapprovedCount>0||!!renderSummary?.voiceover?.error||renderSummary?.revision!==revision} onClick={()=>{reviewDialog.current?.close();void act(true)}}>{w('Создать видео с этими изменениями','Create video with these changes','按这些更改创建视频')}</button></div></dialog>
    </section>
  );
}
