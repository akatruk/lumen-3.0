import { translate } from './locale';
import { useEffect, useId, useRef, useState } from 'react';
import { Languages, Volume2, Download } from 'lucide-react';
import type { Lang } from './types';
import { TaskProgress } from './TaskStatus';

type Language = 'ru' | 'en' | 'zh';
type Version = { id: string; master_id: string; language: Language; voice: string; kind: 'sample' | 'video'; status: string; progress: number; error: string | null; stale: boolean; result: { duration: number } | null };
type Catalog = { voices: { id: string; language: Language; name: string }[]; versions: Version[]; blocked_reason: string | null; needs_transcription?: boolean; busy: boolean; master_id: string; remaining_budget: number; max_cost: number; sample_max_cost: number };
const names: Record<Language, string> = { ru: 'Русский', en: 'English', zh: '中文' };
const active = (v: Version) => !['ready', 'failed'].includes(v.status);

export function Dubbing({ pid, lang, masterId, embedded=false, onPreview }: { pid: string; lang: Lang; masterId?: string; embedded?:boolean; onPreview?:(url:string,label:string)=>void }) {
  const t = (en: string, zh: string) => translate(lang, en, zh);
  const [open, setOpen] = useState(embedded);
  const [data, setData] = useState<Catalog | null>(null);
  const [language, setLanguage] = useState<Language>('ru');
  const [voice, setVoice] = useState('ru-male');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loadError, setLoadError] = useState(false);
  const submitting = useRef(false);
  const panelId = useId();
  const url = `/api/studio/projects/${pid}/dubbing`;
  function explain(code: string) {
    const messages: Record<string, [string, string]> = {
      dubbing_render_first: ['Render a Master first, then create its voiceover version.', '请先制作主版本，再创建配音版本。'],
      dubbing_no_speech: ['No transcribed speech is available in this cut. Music-only footage cannot be translated.', '此剪辑没有可用的语音转录。仅有音乐的视频无法翻译配音。'],
      dubbing_clipped_speech: ['A cut splits a spoken phrase. Adjust the cut to preserve the complete phrase, then render again.', '剪辑截断了一句话。请保留完整语句后重新制作。'],
      dubbing_overlapping_speech: ['Speech timestamps overlap. Correct the transcript timing before dubbing.', '语音时间重叠。请先修正转录时间。'],
      dubbing_transcript_too_long: ['This transcript is too long for one voiceover job. Use a shorter cut.', '转录内容过长，请使用较短的剪辑。'],
      dubbing_speech_too_long: ['A translated phrase could not fit without excessive speed. Your Master is unchanged. Try another voice.', '某句译文无法在合理语速下适配。主版本未变，请尝试其他声音。'],
      dubbing_translation_invalid: ['The translation service returned an incomplete result. You can retry; the Master is unchanged.', '翻译服务返回了不完整结果。可重试，主版本未变。'],
      provider_not_configured: ['Voice generation is not configured on this server yet.', '此服务器尚未配置语音生成。'],
      provider_credits_required: ['The voice provider needs credits. Contact the workspace administrator.', '语音服务余额不足，请联系管理员。'],
      budget_limit: ['Not enough project or workspace budget for this request.', '项目或工作区预算不足。'],
      master_changed: ['The Master changed. Reload this panel and create a version from the latest Master.', '主版本已更新，请重新打开面板并基于最新版本创建配音。'],
      job_already_running: ['Wait for the current project task to finish.', '请等待当前项目任务完成。'],
      worker_interrupted: ['Processing was interrupted. No automatic paid retry was made. You can try again.', '处理已中断，未自动重试付费请求，可手动重试。'],
      storage_full: ['The server needs more storage before creating another version.', '服务器存储不足，暂时无法创建新版本。'],
    };
    const message = messages[code];
    return message ? t(...message) : t('Voiceover could not finish. Your Master and previous versions are safe. Please try again.', '配音未完成。主版本和之前的版本均保留，请重试。');
  }
  useEffect(() => {
    if (!open) return;
    let alive = true;
    const controller = new AbortController();
    async function poll() {
      try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) throw Error();
        const next: Catalog = await response.json();
        if (alive) { setData(next); setLoadError(false); }
      } catch { if (alive) setLoadError(true); }
    }
    void poll();
    const timer = setInterval(poll, 4000);
    return () => { alive = false; controller.abort(); clearInterval(timer); };
  }, [url, open, masterId]);

  async function create(kind: Version['kind']) {
    if (submitting.current || !data) return;
    submitting.current = true; setBusy(true); setError('');
    try {
      const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        request_id: crypto.randomUUID().replaceAll('-', ''), master_id: kind === 'video' ? data.master_id : '',
        language, voice, kind, replace_audio: true,
      }) });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw Error(typeof body.detail === 'string' ? body.detail : 'dubbing_failed');
      }
      const next = await fetch(url);
      if (!next.ok) throw Error('dubbing_failed');
      setData(await next.json());
    } catch (e) { setError(e instanceof Error ? e.message : 'dubbing_failed'); }
    finally { submitting.current = false; setBusy(false); }
  }
  const file = (v: Version, name: string) => `${url}/${v.id}/files/${name}`;
  const running = data?.versions.find(active);
  const sample = data?.versions.find(v => v.kind === 'sample' && v.voice === voice && v.status === 'ready');
  const currentFailure = (['video', 'sample'] as const).map(kind => data?.versions.find(v => v.voice === voice && v.kind === kind && (kind === 'sample' || v.master_id === data.master_id))).find(v => v?.status === 'failed');
  const unavailable = busy || !!running || !!data?.busy || loadError;
  const stage = (status: string) => ({ queued: t('Queued', '已排队'), transcribing: t('Recognizing speech in the finished video', '正在识别成片语音'), translating: t('Translating speech', '正在翻译语音'), synthesizing: t('Generating voice', '正在生成语音'), muxing: t('Preparing dubbed video', '正在合成配音视频') })[status] || t('Processing', '正在处理');
  return <section className="dubbing-panel">
    {!embedded && <button type="button" className="secondary" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
      <Languages size={18} aria-hidden="true" /> {t('Change voiceover', '更换配音')}
    </button>}
    {open && <div id={panelId} className="director-card" role="region" aria-label={t('Change voiceover', '更换配音')}>
      <h3>{t('Create a translated voiceover', '创建翻译配音')}</h3>
      <p>{t('Choose a language and an AI voice. Create a separate version of the rendered Master; your original video stays available.', '选择语言和 AI 声音，基于已制作的主版本创建独立配音版本，原视频保持可用。')}</p>
      <p className="dubbing-notice">{t('This version replaces all original audio, including mixed music and background sounds. It does not clone the speaker or change lip movements. Existing text inside the picture stays unchanged.', '此版本会替换全部原音轨，包括混合的音乐与环境声。不克隆原说话者声音，也不改变口型。画面内原有文字保持不变。')}</p>
      {loadError && <p role="alert">{t('Could not refresh voiceover status. Reconnecting…', '无法刷新配音状态，正在重连…')}</p>}
      {!data ? <p role="status">{t('Loading voices…', '正在加载声音…')}</p> : <>
        <div className="manual-grid">
          <label>{t('Voiceover language', '配音语言')}<select value={language} disabled={busy} onChange={e => { const value = e.target.value as Language; setLanguage(value); setVoice(data.voices.find(v => v.language === value)?.id || ''); setError(''); }}>
            {Object.entries(names).map(([id, name]) => <option value={id} key={id}>{name}</option>)}
          </select></label>
          <label>{t('AI voice', 'AI 声音')}<select value={voice} disabled={busy} onChange={e => { setVoice(e.target.value); setError(''); }}>
            {data.voices.filter(v => v.language === language).map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select></label>
        </div>
        <button type="button" className="secondary" disabled={unavailable || !voice || data.blocked_reason === 'provider_not_configured' || (!sample && data.remaining_budget < data.sample_max_cost)} onClick={() => void create('sample')}>
          <Volume2 size={18} aria-hidden="true" /> {t('Preview voice', '试听声音')}
        </button>
        {sample && <audio key={sample.id} aria-label={t('Voice sample', '声音示例')} controls preload="none" src={file(sample, 'sample.mp3')} />}
        <p>{t('Sample reserves up to', '试听最多预留')} ${data.sample_max_cost.toFixed(2)} · {t('Full version reserves up to', '完整版本最多预留')} ${data.max_cost.toFixed(2)} · {t('Remaining project budget', '项目剩余预算')}: ${data.remaining_budget.toFixed(2)}</p>
        {data.needs_transcription && <p>{t('This cut crosses earlier transcript timestamps. Speech will be recognized again from the finished Master before translation.', '当前剪辑与原转录时间不匹配，将先重新识别成片语音再翻译。')}</p>}
        {data.blocked_reason && <p role="status">{explain(data.blocked_reason)}</p>}
        {data.remaining_budget < data.max_cost && <p>{explain('budget_limit')}</p>}
        <button type="button" className="primary" disabled={unavailable || !voice || !!data.blocked_reason || data.remaining_budget < data.max_cost} onClick={() => void create('video')}>
          {busy ? t('Submitting…', '正在提交…') : t('Create dubbed version', '创建配音版本')}
        </button>
        {running && <TaskProgress title={stage(running.status)} percent={running.progress} />}
        {!running && data.busy && <p role="status">{explain('job_already_running')}</p>}
        {error && <p role="alert">{explain(error)}</p>}
        {!running && currentFailure && <p role="alert">{explain(currentFailure.error || 'dubbing_failed')} {t('Use Preview voice or Create dubbed version to retry with the selected voice.', '可使用试听或创建配音版本按钮，以所选声音重试。')}</p>}
        {data.versions.filter(v => v.kind === 'video' && v.status === 'ready').map(v => <article className="dubbing-version" key={v.id}>
          <h4>{names[v.language]} · {data.voices.find(voice => voice.id === v.voice)?.name || v.voice}</h4>
          {v.stale && <p>{t('Created from an earlier Master. It is still available to play and download.', '基于较早的主版本创建，仍可播放和下载。')}</p>}
          <p>{t('AI voiceover — review pronunciation and timing before sharing.', 'AI 配音 — 分享前请检查发音和时序。')}</p>
          {onPreview?<button className="secondary" onClick={()=>onPreview(file(v,'video.mp4'),`${names[v.language]} · ${v.voice}`)}>{t('Play','播放')} · {names[v.language]}</button>:<video controls preload="none" src={file(v,'video.mp4')} aria-label={`${names[v.language]} ${t('dubbed version','配音版本')}`} />}
          <div className="dubbing-downloads"><a className="primary" href={file(v, 'video.mp4') + '?download=true'}><Download size={16} aria-hidden="true" /> {t('Download dubbed video', '下载配音视频')}</a>
          <a className="secondary" href={file(v, 'subtitles.vtt') + '?download=true'}>{t('Download translated subtitles', '下载译文字幕')}</a></div>
        </article>)}
      </>}
    </div>}
  </section>;
}
