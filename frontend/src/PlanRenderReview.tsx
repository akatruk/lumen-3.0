import {useRef,useState} from 'react';
import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';
import {RenderSummary,type RenderSummaryData} from './RenderSummary';

/** The older cleanup route renders recommendations, not the saved manual timeline. */
export function PlanRenderReview({pid,revision,lang,disabled,onRender}:{pid:string;revision:number;lang:Lang;disabled:boolean;onRender:()=>Promise<void>}){
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
 const dialog=useRef<HTMLDialogElement>(null),opener=useRef<HTMLElement|null>(null),request=useRef(0);
 const [data,setData]=useState<RenderSummaryData|null>(null),[error,setError]=useState(false);
 async function load(){const id=++request.current;setData(null);setError(false);try{const r=await fetch(`/api/studio/projects/${pid}/plan-summary`);if(!r.ok)throw Error();const next=await r.json();if(id===request.current)setData(next)}catch{if(id===request.current)setError(true)}}
 return <><button className="primary" disabled={disabled} onClick={()=>{opener.current=document.activeElement as HTMLElement;dialog.current?.showModal();void load()}}>{w('Проверить и собрать утверждённый план','Review and render approved plan','审核并制作已批准计划')}</button>
 <dialog className="ws-versions" ref={dialog} onClose={()=>opener.current?.focus()}>
 <h2>{w('Что изменится в видео','What will change in this video','视频将有哪些变化')}</h2>
 <p className="error-box">{w('Этот режим использует только утверждённые базовые рекомендации. Ручные эффекты, музыка и монтаж из редактора не включаются. Чтобы собрать их, вернитесь на вкладку «Монтаж».','This mode uses approved cleanup recommendations only. Manual effects, music and the editor timeline are not included. To render those, return to Edit.','此模式仅使用已批准的基础建议，不包含手动效果、音乐或编辑器时间线。如需制作这些更改，请返回编辑。')}</p>
 {data?.revision===revision?<RenderSummary data={data} lang={lang}/>:<p role="status">{error?w('Не удалось загрузить сводку.','Could not load the summary.','无法加载摘要。'):data?w('План изменился. Закройте окно и обновите проект.','The plan changed. Close this dialog and refresh the project.','计划已更改，请关闭窗口并刷新项目。'):w('Загружаем план…','Loading the plan…','正在加载计划…')}</p>}
 {error&&<button onClick={()=>void load()}>{w('Повторить','Retry','重试')}</button>}
 <p>{w('AI-проверка качества резервирует до $0.50 в пределах бюджета проекта. Готовые версии сохраняются.','AI quality review reserves up to $0.50 within the project budget. Finished versions are preserved.','AI 质量审核最多预留 $0.50，受项目预算限制。保留已完成版本。')}</p>
 <div className="manual-actions"><button onClick={()=>dialog.current?.close()}>{w('Вернуться к редактированию','Back to editing','返回编辑')}</button><button className="primary" disabled={disabled||data?.revision!==revision} onClick={()=>{dialog.current?.close();void onRender()}}>{w('Создать видео с этими изменениями','Create video with these changes','按这些更改创建视频')}</button></div>
 </dialog></>;
}
