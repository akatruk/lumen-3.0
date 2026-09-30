import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';

export type EffectPickData={
  id:'punch'|'grade'|'vignette'|'glow'|'card_motion'|'intensity'|'density';
  clips:Record<string,{zoom?:number;zoom_end?:number;shade?:number;glow_amount?:number}>;
  edit:{card_motion?:number;animation_intensity?:number;animation_density?:number};
};

export function EffectPick({lang,pick,error,busy,note,onAccept,onRetry}:{lang:Lang;pick:EffectPickData|null;error:string;busy:boolean;note:string;onAccept:()=>void;onRetry:()=>void}){
  const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
  const title:Record<EffectPickData['id'],string>={
    punch:w('Плавный наезд на всю картинку','A slow push across the whole picture','整段画面缓慢推近'),
    grade:w('Теплее и контрастнее','A warmer, clearer grade','更暖、更清晰的调色'),
    vignette:w('Лёгкая виньетка по краям','A light vignette at the edges','边缘轻微暗角'),
    glow:w('Чуть яснее детали','A light clarity lift','细节稍微更清晰'),
    card_motion:w('Короче анимация в ролике','A shorter share of the video','成片里更短的动画'),
    intensity:w('Слабее вход карточек','A quieter card entrance','卡片入场更轻'),
    density:w('Меньше графических слоёв','Fewer graphic layers','更少图形层'),
  };
  const patches=Object.values(pick?.clips||{});
  const zoomEnd=patches.map(row=>row.zoom_end).filter((value):value is number=>typeof value==='number');
  const detail=pick?.id==='punch'&&zoomEnd.length?w(
    `От ${patches[0]?.zoom??1}× до ${zoomEnd[zoomEnd.length-1]}× на всей картинке. Следующая сборка применит наезд.`,
    `From ${patches[0]?.zoom??1}× to ${zoomEnd[zoomEnd.length-1]}× across the picture. The next render applies the push.`,
    `从 ${patches[0]?.zoom??1}× 推到 ${zoomEnd[zoomEnd.length-1]}×，覆盖整段画面。下次生成会应用这个推近。`,
  ):pick?.id==='grade'?w(
    'Цвет и контраст меняются на кадрах, которые попадут в ролик. Следующая сборка применит эту коррекцию.',
    'Color and contrast change on the frames that reach the video. The next render applies this grade.',
    '进入成片的画面会改变色彩和对比度。下次生成会应用这个调色。',
  ):pick?.id==='vignette'?w(
    'Края кадра темнеют. Следующая сборка применит виньетку.',
    'The frame edges darken. The next render applies the vignette.',
    '画面边缘会变暗。下次生成会应用这个暗角。',
  ):pick?.id==='glow'?w(
    'Детали становятся чуть яснее. Следующая сборка применит это.',
    'Detail gets a little clearer. The next render applies it.',
    '细节会稍微更清晰。下次生成会应用这个效果。',
  ):pick?.id==='card_motion'?w(
    `Графика полного размера останется на ${pick.edit.card_motion??70}% длины ролика. Следующая сборка перепишет промпт Hypit.`,
    `Full-size graphics stay for ${pick.edit.card_motion??70}% of the video. The next render rewrites the Hypit prompt.`,
    `完整尺寸的图形会保留成片长度的 ${pick.edit.card_motion??70}%。下次生成会改写 Hypit 提示。`,
  ):pick?.id==='intensity'?w(
    `Интенсивность входа станет ${pick.edit.animation_intensity??50}%. Размер плашек не меняется.`,
    `Entrance intensity becomes ${pick.edit.animation_intensity??50}%. Card size stays the same.`,
    `入场强度变为 ${pick.edit.animation_intensity??50}%。卡片尺寸不变。`,
  ):pick?.id==='density'?w(
    `В этом отрезке останется ${pick.edit.animation_density??60}% графических слоёв. Размер плашек не меняется.`,
    `${pick.edit.animation_density??60}% of the graphic layers stay in that span. Card size stays the same.`,
    `这段时间保留 ${pick.edit.animation_density??60}% 的图形层。卡片尺寸不变。`,
  ):'';
  return <section className="effect-pick" aria-label={w('Подбор эффекта','Effect pick','效果建议')}>
    <h3>{w('Подбор эффекта','Effect pick','效果建议')}</h3>
    {busy&&!pick&&<p role="status">{w('Смотрю текущую картинку…','Looking at the current picture…','正在查看当前画面…')}</p>}
    {error&&<p role="alert">{error}</p>}
    {pick&&<div>
      <strong>{title[pick.id]}</strong>
      <p>{detail}</p>
      <div className="manual-actions">
        <button type="button" disabled={busy} onClick={onAccept}>{w('Применить к ролику','Use this look','采用这个效果')}</button>
        <button type="button" className="secondary" disabled={busy} onClick={onRetry}>{w('Подобрать снова','Pick again','重新建议')}</button>
      </div>
    </div>}
    {note&&<p role="status">{note}</p>}
  </section>;
}
