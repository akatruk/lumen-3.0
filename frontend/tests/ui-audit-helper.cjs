const fixture=require('./fixtures/ui-audit.cjs');
const assert=require('node:assert/strict');
module.exports=async function setup(browser){
 const data=fixture(),writes=[],errors=[],unknown=[],pid=data.project.id,root=`/api/studio/projects/${pid}`;
 data.finalMusic={master_id:data.project.result.render_id,final_id:'master',music:null,title:'',voice_id:'',jobs:[]};
 const page=await browser.newPage({viewport:{width:1440,height:1000},permissions:['clipboard-read','clipboard-write']});page.setDefaultTimeout(7000);
 page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 await page.addInitScript(()=>localStorage.setItem('lumen_language','en'));
 const text={en:'A useful improvement',zh:'改进'};let offset=0;let uploadConfig=null;
 function revised(){data.manual.revision++;data.studio.revision=data.manual.revision;}
 await page.route('**/api/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname,method=req.method();let json=[];
  if(path.includes('/media/')||path.endsWith('/media')||path.endsWith('/video.mp4'))return route.fulfill(process.env.WORKSPACE_MEDIA?{path:process.env.WORKSPACE_MEDIA,contentType:'video/mp4'}:{status:204});
  if(method!=='GET'){
   const body=req.headers()['content-type']?.includes('json')?req.postDataJSON():null;writes.push({path,method,body});
   if(path===root+'/final-music'){const id='f'.repeat(32);const voice=data.dubbing.versions.find(v=>v.id===data.dubbing.final_version_id);const v={id,master_id:data.project.result.render_id,kind:'mix',status:'ready',created:1800000000,language:voice?.language||'',voice:voice?.voice||'',source_voice:voice?.id||'',music:data.manual.edit.music,music_title:'QA music',stale:false};data.dubbing.final_version_id=id;data.dubbing.final_version=v;data.dubbing.versions.push(v);data.finalMusic={master_id:v.master_id,final_id:id,music:v.music,title:v.music?'QA music':'',voice_id:v.source_voice,jobs:[{id,status:'ready',error:null}]};return route.fulfill({json:{id}})}
   if(path===root+'/dubbing/final'){data.dubbing.final_version_id=body.version_id;return route.fulfill({json:{final_version_id:body.version_id}})}
   if(path===root+'/manual'&&method==='PUT'){data.manual.edit=body.edit;revised();return route.fulfill({json:data.manual})}
   if(path===root+'/manual/from-plan')return route.fulfill({json:{...data.manual,edit:{...data.manual.edit,clips:[{...data.manual.edit.clips[0],start:0,end:2},{...data.manual.edit.clips[1],start:4,end:12}]}}});
   if(path===root+'/manual/beat-preview')return route.fulfill({json:{revision:data.manual.revision,edit:data.manual.edit,changes:[],skipped:[]}});
   if(path.endsWith('/rhythm')){data.assets[0].metadata.rhythm={version:1,accents:[0,2,4,6,8],bpm:120,regularity:.9};return route.fulfill({json:data.assets[0].metadata.rhythm})}
   if(path.endsWith('/favorite')){data.soundtracks[0].favorite=body.favorite;return route.fulfill({json:{ok:true}})}
   if(path.includes('/soundtracks/'))return route.fulfill({json:data.assets[0]});
   if(path===root+'/timeline-proposals'){data.proposals=[{id:'proposal',target:body.clip_id,revision:data.manual.revision,status:'ready',instruction:body.instruction,result:{reason:text,clip:{...data.manual.edit.clips[0],zoom_end:1.3}}}];return route.fulfill({json:{id:'proposal'}})}
   if(path.includes('/timeline-proposals/')&&path.endsWith('/accept')){data.manual.edit.clips[0]={...data.proposals[0].result.clip,approved:false};data.proposals[0].status='accepted';revised();return route.fulfill({json:{ok:true}})}
   if(path===root+'/music-plans'){data.musicPlans=[{id:'music',revision:data.manual.revision,status:'ready',result:{music:data.music,reason:text,emotional_curve:[text]}}];return route.fulfill({json:{id:'music'}})}
   if(path.includes('/music-plans/')&&path.endsWith('/accept')){data.manual.edit.music=data.music;data.musicPlans[0].status='accepted';revised();return route.fulfill({json:{revision:data.manual.revision}})}
   if(path===root+'/creative-plans'){data.creative=[{id:'creative',revision:data.manual.revision,status:'ready',result:{edit:data.manual.edit,reason:text,notes:[]}}];return route.fulfill({json:{id:'creative'}})}
   if(path.includes('/creative-plans/')&&path.endsWith('/accept')){data.creative[0].status='accepted';data.manual.edit.clips.forEach(c=>c.approved=false);revised();return route.fulfill({json:{ok:true}})}
   if(path===root+'/alternatives'){data.alternatives=[{id:'alternative',target:body.target,revision:data.studio.revision,status:'ready',instruction:body.instruction,proposal:{recommendation:data.studio.plan.recommendations[0],transfer:{fit:text}}}];return route.fulfill({json:{id:'alternative'}})}
   if(path.includes('/alternatives/')&&path.endsWith('/accept')){data.alternatives[0].status='accepted';revised();return route.fulfill({json:{ok:true}})}
   if(path===root+'/plan'){data.studio.decisions=body.decisions;revised();return route.fulfill({json:data.studio})}
   if(path===root+'/variants/review'){Object.assign(data.pack.result.variants[0],{review_status:body.approved?'approved':'needs_review',locked:body.locked});return route.fulfill({json:{ok:true}})}
   if(path===root+'/variants/edit'){Object.assign(data.pack.result.variants[0],body);return route.fulfill({json:{ok:true}})}
   if(path==='/api/douyin/search')return route.fulfill({json:data.search});
   if(path==='/api/studio/uploads'){offset=0;return route.fulfill({json:{id:'upload',offset:0,chunk_size:1024*1024}})}
   if(path==='/api/studio/uploads/upload'&&method==='PUT'){offset+=(req.postDataBuffer()?.length||0);return route.fulfill({json:{offset}})}
   if(path==='/api/studio/uploads/upload/complete'){uploadConfig=body;return route.fulfill({json:data.project})}
   if(path==='/api/studio/uploads/upload/asset'){uploadConfig=body;return route.fulfill({json:data.assets[0]})}
   return route.fulfill({json:{ok:true}});
  }
  if(path==='/api/session')json={email:'qa@example.test'};
  else if(path==='/api/projects')json=[{...data.project,metadata:JSON.stringify(data.project.metadata)}];
  else if(path===`/api/projects/${pid}`)json=data.project;
  else if(path===root)json=data.studio;
  else if(path.endsWith('/plan-summary'))json={revision:data.studio.revision,source_duration:12,output_duration:10,removed_seconds:2,removed_ranges:[[2,4]],near_original:true,captions:0,music:false,normalize:false,global_operations:['trim'],pending_proposals:{creative:0},clips:[{id:'a',start:0,end:2,source_start:0,source_end:2,operations:[]},{id:'b',start:2,end:10,source_start:4,source_end:12,operations:[]}]};
  else if(path.endsWith('/manual'))json=data.manual;
  else if(path.endsWith('/assets'))json=data.assets;
  else if(path.endsWith('/final-music'))json=data.finalMusic;
  else if(path.endsWith('/dubbing'))json=data.dubbing;
  else if(path==='/api/studio/soundtracks')json=data.soundtracks;
  else if(path.endsWith('/creative-plans'))json=data.creative;
  else if(path.endsWith('/music-plans'))json=data.musicPlans;
  else if(path.endsWith('/timeline-proposals'))json=data.proposals;
  else if(path.endsWith('/alternatives'))json=data.alternatives;
  else if(path.endsWith('/variants'))json=data.pack;
  else if(path.endsWith('/variants/history'))json=data.history;
  else if(path.endsWith('/variants/history/pack0'))json={...data.pack,package_id:'pack0'};
  else if(path.endsWith('/capabilities'))json={analysis:true,generation:true,analysis_model:'QA',generation_model:'QA'};
  else if(path.startsWith('/api/studio/uploads/completed'))json={};
  else if(path.endsWith('/stock/search'))json=[{id:'stock',title:'QA stock',description:'QA owned footage',artist:'QA',license:'CC0',license_url:'',source_url:'https://example.com',duration:12,height:426}];
  else if(path.endsWith('/stock/imports'))json=[{id:'import',result_id:'stock',status:'complete',asset_id:'2'.repeat(32),error:null}];
  else if(path.includes('/stock/'))json=[];
  else {unknown.push(path);json=[]}
  return route.fulfill({json});
 });
 const button=(name,scope=page)=>scope.getByRole('button',{name,exact:true});
 const tool=async name=>{await button(name,page.locator('.ws-tools')).click()};
 const expand=async()=>page.locator('.ws-inspector details').evaluateAll(els=>els.forEach(e=>e.open=true));
 const goto=async()=>{await page.goto((process.env.WORKSPACE_URL||'http://127.0.0.1:5192')+'/#project/'+pid);await page.locator('.ws-scenes button').first().waitFor()};
 const save=async()=>{await button('Save manual edits').click();await page.waitForFunction(()=>document.querySelector('.ws-footer')?.textContent.includes('Saved'));};
 const draft=async()=>JSON.parse(await page.evaluate(key=>sessionStorage.getItem(key),'lumen-manual-draft:'+pid)).edit;
 const finish=async()=>{assert.deepEqual(errors,[]);await page.close()};
 return {page,data,writes,errors,unknown,button,tool,expand,goto,save,draft,finish,uploadConfig:()=>uploadConfig};
};
