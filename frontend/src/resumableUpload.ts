export async function uploadVideo(file:File,config:Record<string,unknown>,signal:AbortSignal,onProgress:(n:number,info?:{bytes:number;total:number;mbps:number})=>void){
 const assetProject=typeof config.asset_project_id==='string'?config.asset_project_id:'';
 const key='lumen-upload:'+JSON.stringify([file.name,file.size,file.lastModified,...(assetProject?[assetProject]:[])]);
 let saved:{token:string;requestId:string}|null=null;
 try{saved=JSON.parse(sessionStorage.getItem(key)||'null')}catch{}
 if(!saved){saved={token:crypto.randomUUID().replaceAll('-',''),requestId:String(config.request_id)};sessionStorage.setItem(key,JSON.stringify(saved))}
 config={...config,request_id:saved.requestId};
 async function api(path:string,init:RequestInit={},timeout=120000){
  const controller=new AbortController();const abort=()=>controller.abort();signal.addEventListener('abort',abort,{once:true});if(signal.aborted)abort();
  const timer=timeout>0?setTimeout(abort,timeout):null;
  try{
   const r=await fetch('/api/studio/uploads'+path,{...init,signal:controller.signal});
   const data=await r.json().catch(()=>({}));
   if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:r.status===401?'unauthorized':r.status===413?'upload_too_large':r.status===400?'upload_interrupted':'upload_http_'+r.status);
   return data;
  }catch(e){if(signal.aborted)throw new Error('upload_cancelled');if(e instanceof Error&&e.name==='AbortError')throw new Error('upload_timeout');if(e instanceof TypeError)throw new Error('upload_interrupted');throw e}
  finally{if(timer!==null)clearTimeout(timer);signal.removeEventListener('abort',abort)}
 }
 const completed=await api((assetProject?'/completed-asset/':'/completed/')+saved.requestId);
 if(completed.id){sessionStorage.removeItem(key);return completed}
 let state=await api('',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({size:file.size,token:saved.token})});
 const started=performance.now(),initialOffset=state.offset;
 const progress=()=>onProgress(Math.floor(100*state.offset/file.size),{bytes:state.offset,total:file.size,mbps:(state.offset-initialOffset)/Math.max(.001,(performance.now()-started)/1000)/1048576});
 let failures=0;
 let chunkBytes=256*1024;
 while(state.offset<file.size){
  progress();
  try{
   const chunkStarted=performance.now();
   const chunk=file.slice(state.offset,Math.min(file.size,state.offset+Math.min(chunkBytes,state.chunk_size||1024*1024)));
   const next=await api('/'+state.id+'?offset='+state.offset,{method:'PUT',body:chunk,headers:{'Content-Type':'application/octet-stream'}},0);
   state.offset=next.offset;failures=0;
   const seconds=(performance.now()-chunkStarted)/1000;
   if(seconds<3)chunkBytes=Math.min(4*1024*1024,chunkBytes*2);
   else if(seconds>15)chunkBytes=Math.max(256*1024,Math.floor(chunkBytes/2));
  }catch(e){
   const code=e instanceof Error?e.message:'';
   if(!['upload_timeout','upload_interrupted','upload_offset_changed','upload_http_408','upload_http_502','upload_http_503','upload_http_504'].includes(code)||++failures>=3)throw e;
   chunkBytes=256*1024;
   // The previous chunk may have arrived even if its response was lost.
   state=await api('/'+state.id);
  }
 }
 progress();
 let result;
 for(let attempt=0;attempt<2;attempt++){
  try{result=await api('/'+state.id+(assetProject?'/asset':'/complete'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(config)},120000);break}
  catch(e){const code=e instanceof Error?e.message:'';if(attempt||!['upload_timeout','upload_interrupted','upload_http_502','upload_http_503','upload_http_504'].includes(code))throw e}
 }
 sessionStorage.removeItem(key);
 return result;
}
