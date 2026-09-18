import {forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import type {Music} from './MusicEditor';
import type {Lang} from './types';
import {workspaceText,useWorkspace} from './ProjectWorkspace';
type State={master_id:string;final_id:string;music:Music|null;title:string;voice_id:string;jobs:{id:string;status:string;error:string|null}[]};
export type FinalMusicHandle={apply:(revision?:number)=>Promise<void>};
const soundSettings=(v:Music|null)=>v?JSON.stringify([v.asset_id,v.source_start,v.gain_db,v.fade_in,v.fade_out,v.duck,v.loop_fade_ms||0,v.levels||[]]):'none';
export const FinalMusic=forwardRef<FinalMusicHandle,{pid:string;lang:Lang;music:Music|null;disabled:boolean;save:()=>Promise<number|null>}>(({pid,lang,music,disabled,save},ref)=>{
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z),workspace=useWorkspace();
 const [data,setData]=useState<State|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[loadError,setLoadError]=useState(false);
 const applying=useRef(false),identity=useRef<string|null>(null),url=`/api/studio/projects/${pid}/final-music`;
 const refresh=useRef(workspace?.refreshFinal);refresh.current=workspace?.refreshFinal;
 async function read(){const r=await fetch(url);if(!r.ok)throw Error('load_failed');const value=await r.json();if(typeof value.master_id!=='string'||!Array.isArray(value.jobs))throw Error('load_failed');return value as State}
 useEffect(()=>{let alive=true;async function poll(){try{const next=await read();if(!alive)return;const key=next.master_id+':'+next.final_id;if(identity.current!==null&&identity.current!==key)refresh.current?.();identity.current=key;setData(next);setLoadError(false)}catch{if(alive)setLoadError(true)}}void poll();const timer=setInterval(poll,2500);return()=>{alive=false;clearInterval(timer)}},[url]);
 async function apply(revision?:number){
  if(applying.current)return;applying.current=true;setBusy(true);setError('');
  try{
   const saved=revision??await save();if(saved===null)return;
   const current=await read();if(!current.master_id)throw Error('render_first');
   const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({request_id:crypto.randomUUID().replaceAll('-',''),revision:saved,master_id:current.master_id,final_id:current.final_id})});
   if(!r.ok){const e=await r.json();throw Error(typeof e.detail==='string'?e.detail:'mix_failed')}
   setData(await read());
  }catch(e){setError(e instanceof Error?e.message:'mix_failed')}finally{applying.current=false;setBusy(false)}
 }
 useImperativeHandle(ref,()=>({apply}));
 const pending=data?.jobs.some(j=>['queued','mixing'].includes(j.status));
 const applied=!!data&&soundSettings(data.music)===soundSettings(music);
 const failure=data?.jobs[0]?.status==='failed';
 return <section className="final-music-action" aria-label={w('Музыка в финальном видео','Music in final video','成片音乐')}>
 <p className="final-music-current" role="status"><strong>{w('Сейчас в финале: ','In the final video: ','当前成片：')}</strong>{!data?w('Проверяем…','Checking…','正在检查…'):data.music?data.title:w('без добавленной музыки','no added music','无新增音乐')}</p>
 <p>{w('Обновляет только музыку в готовом ролике. Выбранная озвучка и монтаж сохраняются. Без AI и платной генерации.','Updates only music in the finished video. Keeps the selected voiceover and picture edit. No AI or paid generation.','仅更新成片音乐，保留所选配音与画面剪辑。不使用 AI 或付费生成。')}</p>
 <button type="button" className="primary" disabled={disabled||busy||!!pending||loadError||!data?.master_id||applied} onClick={()=>void apply()}>{busy||pending?w('Обновляем финальный звук…','Updating final audio…','正在更新最终音频…'):applied?(music?w('Музыка уже в финальном видео','Music is in the final video','音乐已在成片中'):w('Добавленная музыка выключена','Added music is off','新增音乐已关闭')):music?w('Добавить музыку в финальное видео','Add music to final video','将音乐加入成片'):w('Убрать добавленную музыку из финала','Remove added music from final video','从成片移除新增音乐')}</button>
 {!data?.master_id&&!loadError&&<p>{w('Сначала создайте готовый ролик.','Create a finished video first.','请先制作成片。')}</p>}
 {loadError&&<p role="alert">{w('Не удалось проверить финальную версию. Повторяем подключение…','Could not check the final version. Reconnecting…','无法检查最终版本，正在重连…')}</p>}
 {(error||failure)&&<p role="alert">{error==='music_base_unavailable'?w('В старом монтаже музыка уже склеена со звуком. Создайте монтаж заново, чтобы заменять музыку отдельно.','This older render has music baked into its audio. Render the edit again to enable separate music replacement.','旧版成片的音乐已混入音轨。请重新渲染剪辑以单独替换音乐。'):w('Музыка не обновлена. Прежний финал сохранён. Дождитесь завершения других задач и повторите действие.','Music was not updated. The previous final is safe. Wait for other tasks to finish and retry.','音乐未更新，之前的成片仍保留。请等待其他任务完成后重试。')}</p>}
 </section>;
});
