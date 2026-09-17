import { translate } from './locale';
import type {Lang} from './types';
export type Style={structure:string;pacing:string;presenter_percent:number;visuals:string};
export const defaultStyle:Style={structure:'preserve',pacing:'balanced',presenter_percent:60,visuals:'balanced'};
export function CreatorStyle({value,onChange,lang}:{value:Style;onChange:(v:Style)=>void;lang:Lang}){
 const t=(en: string, zh: string) => translate(lang, en, zh);
 return <fieldset><legend>{t('Editing style','剪辑风格')}</legend>
 <label>{t('Story structure','叙事结构')}<select value={value.structure} onChange={e=>onChange({...value,structure:e.target.value})}>
 <option value="preserve">{t('Preserve chronology','保留原有顺序')}</option>
 <option value="hook_proof_takeaway">{t('Hook → evidence → takeaway','开场吸引 → 证据 → 总结')}</option>
 <option value="problem_solution">{t('Problem → solution → next step','问题 → 解决方案 → 下一步')}</option>
 <option value="comparison">{t('Compare → evidence → conclusion','对比 → 证据 → 结论')}</option></select></label>
 <label>{t('Pacing','节奏')}<select value={value.pacing} onChange={e=>onChange({...value,pacing:e.target.value})}>
 <option value="calm">{t('Calm · aim for 6–12 s shots','舒缓 · 目标镜头 6–12 秒')}</option>
 <option value="balanced">{t('Balanced · aim for 3–7 s shots','均衡 · 目标镜头 3–7 秒')}</option>
 <option value="dynamic">{t('Dynamic · aim for 1.5–4 s shots','明快 · 目标镜头 1.5–4 秒')}</option></select></label>
 <label>{t('Presenter screen time target (%)','人物出镜目标（%）')}<input type="number" min="0" max="100" step="1" value={value.presenter_percent} onChange={e=>onChange({...value,presenter_percent:Math.max(0,Math.min(100,Number(e.target.value)))})}/></label>
 <label>{t('Visual support','辅助画面')}<select value={value.visuals} onChange={e=>onChange({...value,visuals:e.target.value})}>
 <option value="minimal">{t('Minimal','简洁')}</option><option value="balanced">{t('Balanced','均衡')}</option><option value="illustrated">{t('More B-roll and factual graphics','更多补充镜头和事实图表')}</option></select></label>
 <p>{t('Targets guide the proposed timeline. Available footage and complete speech take priority; review the measured result before applying.','目标用于指导时间线方案。可用素材与完整语句优先，请审核实际结果后再应用。')}</p>
 </fieldset>
}
