import {useEffect,useState,type ReactNode} from 'react';
import type {Lang} from './types';
export function statusTone(status:string){
 if(['failed','error','rejected'].includes(status))return 'error';
 if(['complete','completed','successful','success','passed','approved','accepted','uploaded'].includes(status))return 'success';
 if(['queued','running','uploading','analyzing','rendering','processing','checking'].includes(status))return 'active';
 if(['ready','needs_review','paused','unavailable','manual_review_required'].includes(status))return 'warning';
 return 'neutral';
}
export function StatusBadge({status,children}:{status:string;children:ReactNode}){
 const tone=statusTone(status);
 return <span className={`task-status task-status--${tone}`}><span className="task-status-icon" aria-hidden="true">{tone==='success'?'✓':tone==='error'?'!':tone==='active'?'':tone==='warning'?'!':'·'}</span>{children}</span>
}
export function TaskProgress({title,percent,detail}:{title:string;percent?:number;detail?:string}){
 const value=percent===undefined?undefined:Math.max(0,Math.min(100,percent));
 return <div className="task-progress" role="status" aria-live="polite"><div className="task-progress-heading"><StatusBadge status="processing">{title}</StatusBadge>{value!==undefined&&<strong>{value}%</strong>}</div><div className={`task-progress-track ${value===undefined?'is-indeterminate':''}`} role="progressbar" aria-label={title} aria-valuemin={0} aria-valuemax={100} aria-valuenow={value}><i style={value===undefined?undefined:{width:`${value}%`}}/></div>{detail&&<p>{detail}</p>}</div>
}
export function UploadProgress({percent,lang,bytes,total,mbps}:{percent:number;lang:Lang;bytes?:number;total?:number;mbps?:number}){
 const t=(en:string,zh:string)=>lang==='zh'?zh:en;
 const [lastChange,setLastChange]=useState(Date.now()),[now,setNow]=useState(Date.now());
 useEffect(()=>{setLastChange(Date.now())},[percent,bytes]);
 useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[]);
 const checking=percent>=100;const waiting=!checking&&now-lastChange>20000;
 const size=bytes!==undefined&&total!==undefined?`${(bytes/1048576).toFixed(1)} / ${(total/1048576).toFixed(1)} MB`:'';
 return <div className="upload-status"><TaskProgress title={checking?t('Upload received · checking video','上传已接收 · 正在检查视频'):t('Uploading video','正在上传视频')} percent={checking?undefined:percent} detail={checking?t('All bytes received. Preparing the next step…','文件已接收完毕，正在准备下一步…'):[size,mbps&&mbps>0?`${mbps.toFixed(1)} MB/s`:'',t('Confirmed saved on server','服务器已确认保存')].filter(Boolean).join(' · ')}/>{waiting&&<p className="upload-wait"><StatusBadge status="paused">{t('Waiting for server confirmation','正在等待服务器确认')}</StatusBadge><span>{t('No new saved bytes for','距上次保存已过')} {Math.max(0,Math.floor((now-lastChange)/1000))}s. {t('You can pause and resume without losing saved chunks.','可暂停后继续，已保存的部分不会丢失。')}</span></p>}</div>
}
