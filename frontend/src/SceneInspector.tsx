import {ChevronLeft,ChevronRight,ZoomIn,Blend,Frame} from 'lucide-react';
import type {Lang} from './types';
import {workspaceText} from './ProjectWorkspace';
type Scene={start:number;end:number;text:string;approved?:boolean;locked?:boolean};
export function SceneInspector({clips,selected,onSelect,lang}:{clips:Scene[];selected:number;onSelect:(i:number)=>void;lang:Lang}){
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z),clip=clips[selected]||clips[0];
 const stamp=(v:number)=>`${Math.floor(v/60)}:${(v%60).toFixed(1).padStart(4,'0')}`;
 return <header className="inspector-scene">
 <div className="inspector-scene-top"><span>{w('ВЫБРАННАЯ СЦЕНА','SELECTED SCENE','所选场景')}</span><span className={'inspector-status '+(clip.locked?'locked':clip.approved===false?'pending':'approved')}>{clip.locked?w('Закреплена','Locked','已锁定'):clip.approved===false?w('Нужна проверка','Needs review','待审核'):w('Проверена','Approved','已批准')}</span></div>
 <div className="inspector-scene-nav"><button type="button" aria-label={w('Предыдущая сцена','Previous scene','上一个镜头')} disabled={selected===0} onClick={()=>onSelect(selected-1)}><ChevronLeft size={17}/></button><select aria-label={w('Выбрать сцену','Select scene','选择镜头')} value={selected} onChange={e=>onSelect(Number(e.target.value))}>{clips.map((c,i)=><option key={i} value={i}>{`${String(i+1).padStart(2,'0')} · ${c.text||w('Сцена','Scene','镜头')+' '+(i+1)}`}</option>)}</select><button type="button" aria-label={w('Следующая сцена','Next scene','下一个镜头')} disabled={selected>=clips.length-1} onClick={()=>onSelect(selected+1)}><ChevronRight size={17}/></button></div>
 <div className="inspector-scene-meta"><span>{stamp(clip.start)} — {stamp(clip.end)}</span><span>{(clip.end-clip.start).toFixed(1)} {w('сек','sec','秒')} · {selected+1}/{clips.length}</span></div>
 </header>;
}
export function EffectPresets({lang,duration,motionSeconds,first,zoom,zoomEnd,x,y,xEnd,yEnd,transition,onChange}:{lang:Lang;duration:number;motionSeconds?:number|null;first:boolean;zoom:number;zoomEnd?:number|null;x:number;y:number;xEnd?:number|null;yEnd?:number|null;transition?:string;onChange:(value:{motion_seconds?:number;zoom?:number;zoom_end?:number;x_end?:number;y_end?:number;transition?:'crossfade'|'cut'})=>void}){
 const w=(r:string,e:string,z:string)=>workspaceText(lang,r,e,z);
 const items=[{id:'push',Icon:ZoomIn,title:w('Плавное приближение','Gentle zoom','缓慢放大'),detail:w('1× → 1,2×','1× → 1.2×','1× → 1.2×'),active:zoom===1&&zoomEnd===1.2&&(motionSeconds??duration)===Math.min(4,duration),patch:{zoom:1,zoom_end:1.2,motion_seconds:Math.min(4,duration)}},
 {id:'dissolve',Icon:Blend,title:w('Растворение','Cross dissolve','叠化'),detail:first?w('Со второй сцены','From scene 2','从第二个镜头开始'):w('Мягкий переход','Soft transition','柔和转场'),active:!first&&transition==='crossfade',patch:{transition:'crossfade' as const}},
 {id:'still',Icon:Frame,title:w('Без движения','No motion','静止画面'),detail:w('Исходный кадр','Original framing','原始构图'),active:zoom===1&&(zoomEnd??zoom)===1&&(xEnd??x)===x&&(yEnd??y)===y&&(!transition||transition==='cut'),patch:{zoom:1,zoom_end:1,x_end:x,y_end:y,transition:'cut' as const}}];
 return <section className="inspector-presets"><h3>{w('Быстрые эффекты','Quick effects','快捷效果')}</h3><div className="ws-effect-presets">{items.map(({id,Icon,title,detail,active,patch})=><button key={id} type="button" aria-label={title} aria-pressed={active} disabled={id==='dissolve'&&first} onClick={()=>onChange(patch)}><span className={'preset-art preset-'+id}><Icon size={24}/></span><strong>{title}</strong><small>{detail}{id==='push'?` · ${Math.min(4,duration).toFixed(1)} s`:''}</small></button>)}</div></section>;
}
