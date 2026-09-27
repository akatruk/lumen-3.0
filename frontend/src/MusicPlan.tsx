import {contentLanguage} from './locale';
import {useEffect, useState} from 'react';
import type {Asset} from './MediaLibrary';
import type {Music} from './MusicEditor';
import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';
import {StatusBadge} from './TaskStatus';
import {MusicBedList, MusicCandidateList, type BedTrack} from './MusicBedList';
import {bedKeyForAsset, projectAssetForTrack, toggleCandidate} from './musicBed';

type Text = {en: string; zh: string};
type Plan = {id: string; revision: number; status: string; result: null | {music: Music | null; reason: Text; emotional_curve: Text[]}};
const freshMusic = (assetId: string): Music => ({asset_id: assetId, source_start: 0, gain_db: -18, fade_in: 1, fade_out: 2, duck: true});

export function MusicPlan({pid, revision, assets, lang, suggestDisabled, onApplied, currentMusic, onUploadMusic, onUse, onAssetsChanged}:{onUploadMusic:()=>void; onUse:(music:Music|null)=>void; onAssetsChanged:()=>Promise<void>; currentMusic?:Music|null; pid:string; revision:number; assets:Asset[]; lang:Lang; suggestDisabled:boolean; onApplied:(revision:number)=>Promise<void>}) {
  const w = (ru: string, en: string, zh: string) => workspaceText(lang, ru, en, zh);
  const url = `/api/studio/projects/${pid}/music-plans`;
  const [tracks, setTracks] = useState<BedTrack[]>([]);
  const [tab, setTab] = useState<'curated' | 'uploaded'>('curated');
  const [picked, setPicked] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [chosen, setChosen] = useState<string[]>([]);
  const [busyKey, setBusyKey] = useState('');
  const [saving, setSaving] = useState('');
  const [direction, setDirection] = useState('');
  const [items, setItems] = useState<Plan[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'select' | 'mix_only'>('select');
  const derived = bedKeyForAsset(assets.find(asset => asset.id === currentMusic?.asset_id));
  const selectedKey = picked ?? derived;
  const visible = tracks.filter(track => track.origin === tab);
  const selectedTrack = tracks.find(track => track.key === selectedKey);
  const pending = items.some(item => item.status === 'queued');

  async function loadPlans() {
    const response = await fetch(url);
    if (response.ok) setItems(await response.json());
  }
  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const response = await fetch(url);
        if (response.ok && active) setItems(await response.json());
      } catch { /* keep the last plan */ }
    }
    void poll();
    const timer = setInterval(poll, 4000);
    return () => { active = false; clearInterval(timer); };
  }, [url]);
  useEffect(() => { setPicked(null); }, [currentMusic?.asset_id]);
  useEffect(() => {
    let active = true;
    async function loadTracks() {
      try {
        const response = await fetch('/api/studio/soundtracks');
        if (!response.ok) throw Error('load_failed');
        const rows = await response.json() as BedTrack[];
        if (active) {
          setTracks(rows.filter(row => row.origin === 'curated' || row.origin === 'uploaded'));
          setLoadError(false);
        }
      } catch {
        if (active) setLoadError(true);
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadTracks();
    return () => { active = false; };
  }, [pid, assets.length]);

  async function ensure(track: BedTrack) {
    const existing = projectAssetForTrack(track.key, assets);
    if (existing) return existing;
    const response = await fetch(`/api/studio/projects/${pid}/soundtracks/${encodeURIComponent(track.key)}`, {method: 'POST'});
    if (!response.ok) {
      let detail = '';
      try { detail = String((await response.json()).detail || ''); } catch { /* ignore */ }
      throw Error(detail || 'add_failed');
    }
    const body = await response.json() as {id: string};
    await onAssetsChanged();
    return body.id;
  }
  async function choose(key: string) {
    const track = tracks.find(item => item.key === key);
    if (!track || !track.available || saving) return;
    setPicked(key);
    setSaving(key);
    setError('');
    try {
      const id = await ensure(track);
      if (currentMusic?.asset_id === id && !currentMusic.locked) {
        setPicked(null);
        return;
      }
      onUse(currentMusic?.asset_id === id ? {...currentMusic, locked: false} : freshMusic(id));
    } catch (caught) {
      setPicked(null);
      const detail = caught instanceof Error ? caught.message : '';
      setError(detail === 'asset_limit' ? w('В проекте уже 20 материалов.', 'This project already has 20 assets.', '项目已有 20 个素材。') : w('Не удалось выбрать композицию. Попробуйте ещё раз.', 'Could not select that track. Try again.', '无法选择该曲目，请重试。'));
    } finally {
      setSaving('');
    }
  }
  async function toggle(key: string, on: boolean) {
    const track = tracks.find(item => item.key === key);
    if (!track) return;
    const existing = projectAssetForTrack(track.key, assets);
    if (existing) {
      setChosen(ids => toggleCandidate(ids, existing, on));
      return;
    }
    if (!on) return;
    setBusyKey(key);
    setError('');
    try {
      const id = await ensure(track);
      setChosen(ids => toggleCandidate(ids, id, true));
    } catch (caught) {
      const detail = caught instanceof Error ? caught.message : '';
      setError(detail === 'asset_limit' ? w('В проекте уже 20 материалов.', 'This project already has 20 assets.', '项目已有 20 个素材。') : w('Не удалось отметить композицию. Попробуйте ещё раз.', 'Could not check that track. Try again.', '无法勾选该曲目，请重试。'));
    } finally {
      setBusyKey('');
    }
  }
  async function act(id?: string) {
    setBusy(true);
    setError('');
    try {
      const response = await fetch(url + (id ? `/${id}/accept` : ''), {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(id ? {revision} : {revision, asset_ids: mode === 'mix_only' ? [] : chosen, direction, mode})});
      if (!response.ok) throw Error('plan_failed');
      const body = await response.json();
      await loadPlans();
      if (id) await onApplied(body.revision);
    } catch {
      setError(w('Сохраните последнюю правку, разблокируйте музыку и дождитесь завершения текущей задачи.', 'Save the latest edit, unlock music and wait for running work to finish.', '请保存最新剪辑、解锁音乐并等待当前任务完成。'));
    } finally {
      setBusy(false);
    }
  }

  return <section className="music-bed" aria-label={w('Музыка проекта', 'Project music', '项目音乐')}>
    <h3>{w('Музыка проекта', 'Project music', '项目音乐')}</h3>
    <p>{w('Выберите композицию из подборки или из загруженных. Отметка сразу показывает выбор и назначает её музыкой проекта. Кнопка «Добавить музыку в финальное видео» ниже обновляет ролик без AI и без оплаты.', 'Choose a track from the licensed collection or from your uploads. The mark shows your choice immediately and sets it as this project’s music. Add music to final video below updates the film with no AI and no charge.', '从授权曲库或已上传曲目中选择。标记会立即显示选择，并将其设为本项目音乐。下方「将音乐加入成片」会更新视频，无需 AI，也不收费。')}</p>
    <p className="music-bed-status" role="status">{selectedTrack ? <>{w('Выбрано: ', 'Selected: ', '已选择：')}<strong>{selectedTrack.title}</strong></> : currentMusic ? w('Выбранная композиция сохранена в проекте.', 'A saved track is already chosen for this project.', '本项目已有选定曲目。') : w('Музыка не выбрана', 'No music selected', '未选择音乐')}</p>
    <div className="music-bed-switch" role="group" aria-label={w('Раздел композиций', 'Track section', '曲目分类')}>
      <button type="button" aria-pressed={tab === 'curated'} onClick={() => setTab('curated')}>{w('Подборка', 'Collection', '精选')}</button>
      <button type="button" aria-pressed={tab === 'uploaded'} onClick={() => setTab('uploaded')}>{w('Загруженные', 'Uploaded', '已上传')}</button>
    </div>
    {loading && <p role="status">{w('Загружаю композиции…', 'Loading tracks…', '正在加载曲目…')}</p>}
    {loadError && <p role="alert">{w('Не удалось загрузить подборку. Обновите страницу.', 'Could not load the collection. Refresh the page.', '无法加载曲库，请刷新页面。')}</p>}
    {!loading && !loadError && <MusicBedList lang={lang} tracks={visible} selectedKey={selectedKey} group={`music-bed-${pid}`} onSelect={key => void choose(key)}/>}
    <div className="music-bed-actions">
      <button type="button" className="secondary" aria-pressed={!currentMusic && !picked} onClick={() => { setPicked(''); onUse(null); }}>{w('Без музыки', 'No music', '无音乐')}</button>
      <button type="button" className="secondary" onClick={onUploadMusic}>{w('Загрузить музыку', 'Upload music', '上传音乐')}</button>
    </div>
    {error && <p role="alert">{error}</p>}
    <details className="music-ai">
      <summary>{w('Сравнить с AI', 'Compare with AI', '用 AI 比较')}</summary>
      <p className="music-ai-explainer">{w('Необязательно. Отметьте до трёх композиций — галочки только выбирают кандидатов и сразу показывают отметку. Ролик не меняется, пока вы не примените предложение. Подбор — до $0.50.', 'Optional. Check up to three tracks. The boxes only choose candidates and show the check immediately. The video stays unchanged until you apply a proposal. Comparison costs up to $0.50.', '可选。勾选最多三首曲目。勾选只选择候选并立即显示。在应用建议前，视频不会改变。比较费用最高 $0.50。')}</p>
      <label>{w('Что должен сделать AI?', 'What should AI do?', '希望 AI 做什么？')}<select disabled={suggestDisabled || busy || pending} value={mode} onChange={event => setMode(event.target.value as 'select' | 'mix_only')}><option value="select">{w('Сравнить отмеченные композиции', 'Compare the checked tracks', '比较已勾选的曲目')}</option><option value="mix_only" disabled={!currentMusic}>{w('Улучшить текущий микс — оставить композицию и начало', 'Improve the current mix — keep the track and start', '改善当前混音 — 保留曲目与起点')}</option></select></label>
      {mode === 'mix_only' && <p>{w('Оставляет сохранённую композицию и точку старта. AI может предложить громкость, затухания и приглушение. Применяйте после просмотра.', 'Keeps the saved track and start point. AI may suggest volume, fades and ducking. Apply after review.', '保留已保存的曲目和起点。AI 可建议音量、淡入淡出和压低配乐。请审核后应用。')}</p>}
      {mode === 'select' && <MusicCandidateList lang={lang} tracks={tracks} chosenIds={chosen} busyKey={busyKey} assetIdFor={key => projectAssetForTrack(key, assets)} onToggle={(key, on) => void toggle(key, on)}/>}
      <label>{w('Музыкальное направление', 'Musical direction', '配乐方向')}<textarea value={direction} maxLength={1200} onChange={event => setDirection(event.target.value)}/></label>
      {suggestDisabled && <p>{w('Запуск сравнения ждёт сохранения правок, разблокировки музыки или окончания текущей задачи. Выбор композиции выше от этого не зависит.', 'Starting a comparison waits until edits are saved, music is unlocked, or the current task finishes. Choosing a track above does not wait for that.', '开始比较需先保存剪辑、解锁音乐或等待当前任务结束。上方选择曲目不受此限制。')}</p>}
      <button type="button" className="primary" disabled={suggestDisabled || busy || pending || (mode === 'select' ? chosen.length === 0 : !currentMusic)} onClick={() => void act()}>{mode === 'mix_only' ? w('Предложить улучшения микса', 'Suggest mix improvements', '推荐混音改进') : w('Предложить музыку', 'Suggest a soundtrack', '推荐配乐')}</button>
      {items.slice(0, 1).map(item => <article key={item.id}><StatusBadge status={item.status}>{item.status === 'queued' ? w('Слушаем и готовим предложение…', 'Listening and planning…', '正在试听并规划…') : item.status === 'failed' ? w('Подбор не выполнен, правка сохранена', 'Music planning failed; your edit is preserved', '配乐规划失败，原剪辑保留') : item.status === 'accepted' ? w('Музыка применена к сохранённому плану', 'Music applied to the saved plan', '配乐已应用到保存的计划') : w('Предложение музыки', 'Soundtrack proposal', '配乐建议')}</StatusBadge>{item.result && <><p>{item.result.reason[contentLanguage(lang)]}</p>{item.result.emotional_curve.map((point, index) => <p key={index}>{point[contentLanguage(lang)]}</p>)}{item.result.music ? <><audio controls preload="none" src={`/api/studio/projects/${pid}/assets/${item.result.music.asset_id}/media`}/><p>{w('Это исходная композиция. Предложенный микс слышно после применения.', 'Preview is the source track. The proposed mix is heard after you apply it.', '此为原曲试听。应用后可听到建议混音。')}</p>{item.status === 'ready' && <button type="button" className="primary" disabled={suggestDisabled || busy || pending || item.revision !== revision} onClick={() => void act(item.id)}>{w('Применить и обновить финал', 'Apply and update final video', '应用并更新成片')}</button>}</> : <p>{w('Подходящая композиция не найдена.', 'No suitable track found.', '未找到合适曲目。')}</p>}</>}</article>)}
    </details>
  </section>;
}
