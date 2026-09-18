import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';
export type RenderSummaryData={slow_motion_scenes?:number[];revision:number;source_duration:number;output_duration:number;removed_seconds:number;removed_ranges:number[][];near_original:boolean;captions:number;music:boolean;normalize:boolean;global_operations:string[];pending_proposals:Record<string,number>;clips:{id:string;start:number;end:number;source_start:number;source_end:number;operations:string[]}[]};
const stamp=(n:number)=>`${Math.floor(n/60)}:${(n%60).toFixed(1).padStart(4,'0')}`;
export function RenderSummary({data,lang,onReviewProposals}:{data:RenderSummaryData;lang:Lang;onReviewProposals?:()=>void}){
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
 const names:Record<string,string>={motion:w('Движение камеры','Camera motion','镜头运动'),reframe:w('Кадрирование','Reframe','重新构图'),fade:w('Затухание','Fade','淡化'),crossfade:w('Наплыв','Cross dissolve','叠化'),zoom:w('Зум-переход','Zoom transition','缩放转场'),wipe:w('Шторка','Wipe','擦除'),circle:w('Круговая маска','Circle mask','圆形遮罩'),title:w('Текст','Text overlay','文字叠加'),graphic:w('Графическая вставка','Graphic insert','图形插入'),broll:w('Видеовставка','B-roll','补充镜头'),sound_effects:w('Звуковые эффекты','Sound effects','音效')};
 const pending=Object.values(data.pending_proposals).reduce((a,b)=>a+b,0);
 return <div className="render-summary">
 <p>{w('Сводка сохранённого монтажа относительно исходника.','Saved edit compared with the source footage.','已保存剪辑与原片的对比。')}</p>
 {data.near_original&&<div className="error-box" role="status"><strong>{w('Видео будет почти идентично исходнику','The video will look almost identical to the source','视频画面将与原片几乎相同')}</strong><p>{w('По настройкам плана заметных визуальных изменений мало или нет. Звук может отличаться.','The plan contains few or no visible changes. Audio may differ.','计划中明显的视觉变化很少或没有，音频可能不同。')}</p></div>}
 <h3>{w('Длительность и монтаж','Duration and editing','时长与剪辑')}</h3>
 {Boolean(data.slow_motion_scenes?.length)&&<p className="ws-delivery-warning">{w('Медленное движение камеры: сцены','Slow camera movement: scenes','缓慢镜头运动：场景')} {data.slow_motion_scenes?.join(', ')}. {w('Эффект растянут более чем на 12 секунд. Измените длительность движения в «Эффектах», если нужен заметный акцент.','The move lasts over 12 seconds. Adjust movement duration in Effects for a more noticeable accent.','运动持续超过 12 秒。如需更明显的强调，请在效果中调整运动时长。')}</p>}
 <p>{stamp(data.source_duration)} → <strong>{stamp(data.output_duration)}</strong> · {w('по плану, до округления кадров','planned, before frame rounding','计划时长，未进行帧取整')}</p>
 <p>{data.global_operations.includes('reorder')?w('Порядок сцен изменён / есть возврат к более раннему фрагменту.','Scenes reordered / earlier footage revisited.','已调整镜头顺序或回到前面的片段。'):w('Хронологический порядок сохранён.','Chronological order preserved.','保留时间顺序。')}</p>
 <p>{w('Вырезано из исходника','Removed from source','从原片删除')}: {data.removed_seconds.toFixed(1)} s</p>
 {data.removed_ranges.length>0&&<p>{data.removed_ranges.map(([a,b])=>`${stamp(a)}–${stamp(b)}`).join(' · ')}</p>}
 <details open><summary>{w('Сцены и эффекты','Scenes and effects','镜头与效果')} ({data.clips.length})</summary><p>{w('Сначала таймкод в новом видео, затем диапазон исходника.','Output time first, then the source range.','先显示新视频时间，再显示原片范围。')}</p><ol>{data.clips.map((c,i)=><li key={c.id||i}><strong>{stamp(c.start)}–{stamp(c.end)}</strong> ← {stamp(c.source_start)}–{stamp(c.source_end)}<p>{c.operations.length?c.operations.map(op=>names[op]||op).join(' · '):w('Без дополнительных эффектов','No added effects','无附加效果')}</p></li>)}</ol></details>
 <h3>{w('Звук и субтитры','Audio and captions','音频与字幕')}</h3>
 <p>{w('Звук исходника. Отдельная версия с новой озвучкой сюда не переносится.','Source audio. A separately dubbed version is not applied to this render.','使用原片音频，独立配音版本不会用于此次制作。')}</p>
 <ul><li>{w('Фоновая музыка','Background music','背景音乐')}: {data.music?w('добавлена','added','已添加'):w('не добавлена','not added','未添加')}</li><li>{w('Нормализация громкости','Audio normalization','音量标准化')}: {data.normalize?w('включена','on','开启'):w('выключена','off','关闭')}</li><li>{w('Добавляемые субтитры','Added captions','添加的字幕')}: {data.captions||w('выключены','off','关闭')}</li></ul>
 <h3>{w('Не войдёт в видео','Not included in this video','不会包含在视频中')}</h3>
 {pending>0&&onReviewProposals&&<button onClick={onReviewProposals}>{w('Открыть предложения AI','Open AI proposals','打开 AI 建议')}</button>}
 <p>{pending?`${w('Неприменённые предложения AI','Unapplied AI proposals','未应用的 AI 建议')}: ${pending}. ${w('Включая устаревшие: сначала примените нужное предложение в редакторе, проверьте и сохраните монтаж.','Including older proposals: apply the desired proposal in the editor, review it and save the edit first.','包括旧建议：请先在编辑器中应用所需建议，审核并保存剪辑。')}`:w('Нет готовых неприменённых предложений AI.','No ready unapplied AI proposals.','没有待应用的 AI 建议。')}</p>
 </div>;
}
