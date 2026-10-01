import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';

export type EffectPickData={
  id:'punch'|'grade'|'vignette'|'glow'|'card_motion'|'intensity'|'depth'|'motion'|'density';
  clips:Record<string,{zoom?:number;zoom_end?:number;shade?:number;glow_amount?:number}>;
  edit:{card_motion?:number;animation_intensity?:number;animation_depth?:number;animation_motion?:number;animation_density?:number};
};

export function EffectPick({lang,pick,error,busy,note,onAccept,onRetry}:{lang:Lang;pick:EffectPickData|null;error:string;busy:boolean;note:string;onAccept:()=>void;onRetry:()=>void}){
  const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
  const title:Record<EffectPickData['id'],string>={
    punch:w('Плавный наезд на всю картинку','A slow push across the whole picture','整段画面缓慢推近'),
    grade:w('Теплее и контрастнее','A warmer, clearer grade','更暖、更清晰的调色'),
    vignette:w('Лёгкая виньетка по краям','A light vignette at the edges','边缘轻微暗角'),
    glow:w('Чуть яснее детали','A light clarity lift','细节稍微更清晰'),
    card_motion:w('Анимация на части ролика','Animation for part of the video','成片中的一段动画'),
    intensity:w('Ниже интенсивность','Lower intensity','更低的强度'),
    depth:w('Ниже интенсивность','Lower intensity','更低的强度'),
    motion:w('Меньше движения','Less motion','更少的运动'),
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
    `На ${pick.edit.card_motion??70}% длины ведущий в кружке, слова становятся графикой — это ${Math.round((pick.edit.card_motion??70)*60/100)} секунд на каждую минуту.`,
    `Animation will cover ${pick.edit.card_motion??70}% of the video — ${Math.round((pick.edit.card_motion??70)*60/100)} seconds of each minute.`,
    `动画将占成片的 ${pick.edit.card_motion??70}%，即每分钟 ${Math.round((pick.edit.card_motion??70)*60/100)} 秒。`,
  ):pick?.id==='intensity'||pick?.id==='depth'?w(
    `Интенсивность станет ${pick.edit.animation_depth??pick.edit.animation_intensity??50}%.`,
    `Intensity becomes ${pick.edit.animation_depth??pick.edit.animation_intensity??50}%.`,
    `强度变为 ${pick.edit.animation_depth??pick.edit.animation_intensity??50}%。`,
  ):pick?.id==='motion'?w(
    `Движение станет ${pick.edit.animation_motion??50}%.`,
    `Motion becomes ${pick.edit.animation_motion??50}%.`,
    `运动变为 ${pick.edit.animation_motion??50}%。`,
  ):pick?.id==='density'?w(
    `Плотность станет ${pick.edit.animation_density??60}% слоёв.`,
    `Density becomes ${pick.edit.animation_density??60}% of the layers.`,
    `密度变为图层的 ${pick.edit.animation_density??60}%。`,
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
