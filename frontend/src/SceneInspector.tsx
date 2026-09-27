import {useEffect,useRef} from 'react';
import {ChevronLeft,ChevronRight,Lock,ZoomIn,Blend,Frame} from 'lucide-react';
import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';
type Scene={start:number;end:number;text:string;approved?:boolean;locked?:boolean};
export function SceneInspector({clips,selected,onSelect,lang}:{clips:Scene[];selected:number;onSelect:(i:number)=>void;lang:Lang}){
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z),clip=clips[selected]||clips[0];
 const list=useRef<HTMLDivElement>(null);
 const stamp=(v:number)=>`${Math.floor(v/60)}:${(v%60).toFixed(1).padStart(4,'0')}`;
 const seconds=(c:Scene)=>`${(c.end-c.start).toFixed(1)} ${w('сек','sec','秒')}`;
 const title=w('Сцена {n} из {total}','Scene {n} of {total}','镜头 {n}/{total}').replaceAll('{n}',String(selected+1)).replaceAll('{total}',String(clips.length));
 const step=(delta:number,focus=false)=>{const next=selected+delta;if(next<0||next>=clips.length)return;onSelect(next);if(focus)requestAnimationFrame(()=>document.getElementById(`montage-scene-${next}`)?.focus())};
 useEffect(()=>{
  const box=list.current,row=box?.querySelector<HTMLElement>('[aria-selected="true"]');
  if(!box||!row)return;
  const boxTop=box.getBoundingClientRect().top,rowBox=row.getBoundingClientRect();
  if(rowBox.top<boxTop)box.scrollTop-=boxTop-rowBox.top;
  else if(rowBox.bottom>boxTop+box.clientHeight)box.scrollTop+=rowBox.bottom-(boxTop+box.clientHeight);
 },[selected,clips.length]);
 const flags=(c:Scene)=><span className="scene-flags"><em className={c.approved===false?'scene-flag out':'scene-flag in'}>{c.approved===false?w('Не в ролике','Out of the cut','不进成片'):w('В ролике','In the cut','在成片中')}</em>{c.locked&&<em className="scene-flag frozen"><Lock size={12} aria-hidden="true"/>{w('Тайминг заморожен','Timing frozen','时间已冻结')}</em>}</span>;
 return <header className="scene-picker">
  <div className="scene-picker-top">
   <div>
    <p className="scene-picker-kicker">{w('Выбранная сцена','Selected scene','所选场景')}</p>
    <p className="scene-picker-range"><span>{stamp(clip.start)} — {stamp(clip.end)}</span><span>{seconds(clip)}</span></p>
   </div>
   {flags(clip)}
  </div>
  <div className="scene-picker-nav">
   <button type="button" className="scene-step" aria-label={w('Предыдущая сцена','Previous scene','上一个镜头')} disabled={selected===0} onClick={()=>step(-1)}><ChevronLeft size={20}/></button>
   <p>{title}</p>
   <button type="button" className="scene-step" aria-label={w('Следующая сцена','Next scene','下一个镜头')} disabled={selected>=clips.length-1} onClick={()=>step(1)}><ChevronRight size={20}/></button>
  </div>
  <div className="scene-strip" role="listbox" aria-label={w('Сцены','Scenes','场景')} aria-activedescendant={`montage-scene-${selected}`} tabIndex={0} ref={list} onKeyDown={e=>{if(e.key==='ArrowDown'||e.key==='ArrowRight'){e.preventDefault();step(1,true)}else if(e.key==='ArrowUp'||e.key==='ArrowLeft'){e.preventDefault();step(-1,true)}}}>
   {clips.map((c,i)=><button key={i} id={`montage-scene-${i}`} type="button" role="option" data-scene={i} aria-selected={selected===i} tabIndex={-1} onClick={()=>onSelect(i)}>
    <span className="scene-strip-num">{i+1}</span>
    <span className="scene-strip-copy"><strong>{stamp(c.start)} — {stamp(c.end)}</strong><small>{seconds(c)}</small></span>
    {flags(c)}
   </button>)}
  </div>
 </header>;
}
export function EffectPresets({lang,duration,motionSeconds,first,zoom,zoomEnd,x,y,xEnd,yEnd,transition,onChange}:{lang:Lang;duration:number;motionSeconds?:number|null;first:boolean;zoom:number;zoomEnd?:number|null;x:number;y:number;xEnd?:number|null;yEnd?:number|null;transition?:string;onChange:(value:{motion_seconds?:number;zoom?:number;zoom_end?:number;x_end?:number;y_end?:number;transition?:'crossfade'|'cut'})=>void}){
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
 const items=[{id:'push',Icon:ZoomIn,title:w('Плавное приближение','Gentle zoom','缓慢放大'),detail:w('1× → 1,2×','1× → 1.2×','1× → 1.2×'),active:zoom===1&&zoomEnd===1.2&&(motionSeconds??duration)===Math.min(4,duration),patch:{zoom:1,zoom_end:1.2,motion_seconds:Math.min(4,duration)}},
 {id:'dissolve',Icon:Blend,title:w('Растворение','Cross dissolve','叠化'),detail:first?w('Со второй сцены','From scene 2','从第二个镜头开始'):w('Мягкий переход','Soft transition','柔和转场'),active:!first&&transition==='crossfade',patch:{transition:'crossfade' as const}},
 {id:'still',Icon:Frame,title:w('Без движения','No motion','静止画面'),detail:w('Исходный кадр','Original framing','原始构图'),active:zoom===1&&(zoomEnd??zoom)===1&&(xEnd??x)===x&&(yEnd??y)===y&&(!transition||transition==='cut'),patch:{zoom:1,zoom_end:1,x_end:x,y_end:y,transition:'cut' as const}}];
 return <section className="inspector-presets"><h3>{w('Быстрые эффекты','Quick effects','快捷效果')}</h3><div className="ws-effect-presets">{items.map(({id,Icon,title,detail,active,patch})=><button key={id} type="button" aria-label={title} aria-pressed={active} disabled={id==='dissolve'&&first} onClick={()=>onChange(patch)}><span className={'preset-art preset-'+id}><Icon size={24}/></span><strong>{title}</strong><small>{detail}{id==='push'?` · ${Math.min(4,duration).toFixed(1)} s`:''}</small></button>)}</div></section>;
}
