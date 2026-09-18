// Real HTTP acceptance. No page.route, API stubs or intercepted mutations.
// The isolated Python bridge seeds synthetic media and deterministic AI output.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const seed=JSON.parse(fs.readFileSync(process.env.LUMEN_ACCEPTANCE_READY,'utf8'));
const origin=process.env.WORKSPACE_URL||'http://127.0.0.1:5193';
const report={passed:false,checks:[],errors:[]};
const output=process.env.LUMEN_ACCEPTANCE_REPORT||'/tmp/lumen-real-render-report.json';
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const safeError=e=>String(e.stack||e).replaceAll(seed.token,'[redacted]');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.addCookies([{name:'lumen_session',value:seed.token,url:origin}]);
 const page=await context.newPage();page.setDefaultTimeout(20000);
 page.on('pageerror',e=>report.errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400&&new URL(r.url()).pathname.startsWith('/api/'))console.error('HTTP',r.status(),new URL(r.url()).pathname)});
 page.on('dialog',d=>d.accept());
 await page.addInitScript(()=>localStorage.setItem('lumen_language','en'));
 const base=`/api/studio/projects/${seed.pid}`;
 const get=async url=>{const r=await context.request.get(origin+url,{maxRetries:2});assert(r.ok(),`${url}: ${r.status()}`);return r.json()};
 const button=(name,root=page)=>root.getByRole('button',{name,exact:true});
 const tool=name=>button(name,page.locator('.ws-tools')).click();
 const expand=()=>page.locator('.ws-inspector details').evaluateAll(els=>els.forEach(e=>e.open=true));
 const poll=async(fn,label)=>{const until=Date.now()+180000;while(Date.now()<until){if(await fn())return;await page.waitForTimeout(500)}throw Error('Timed out: '+label)};
 const save=async()=>{const old=(await get(base+'/manual')).revision;await button('Save manual edits').click();await poll(async()=> (await get(base+'/manual')).revision>old,'save');};
 async function verifyDelivery(label){
   const dub=await get(base+'/dubbing');
   assert.equal(dub.final_version.language,'ru');assert.equal(dub.final_version.delivery||dub.final_version.kind,'mix');
   const v=page.locator('.ws-ready-player video');
   await poll(async()=> (await v.getAttribute('src')||'').includes(dub.final_version_id),'player selected final');
   await v.evaluate(async el=>{el.muted=true;await el.play()});
   await poll(()=>v.evaluate(el=>el.currentTime>.25&&!el.error),'video playback');await v.evaluate(el=>el.pause());
   const link=page.getByRole('link',{name:'Download video',exact:true}).first();
   const href=await link.getAttribute('href');
   const response=await context.request.get(new URL(href,origin).href,{maxRetries:2});
   assert(response.ok());const bytes=await response.body();assert(bytes.length>10000);
   const immutable=await context.request.get(origin+base+'/final-music/'+dub.final_version_id+'/video.mp4',{maxRetries:2});
   assert(immutable.ok());assert.equal(hash(bytes),hash(await immutable.body()));
   const downloadEvent=page.waitForEvent('download');await link.click();const download=await downloadEvent;
   assert.equal(await download.failure(),null);assert.equal(hash(fs.readFileSync(await download.path())),hash(bytes));
   report.checks.push({label,master_id:dub.master_id,final_id:dub.final_version_id,download_sha256:hash(bytes),playback:true});
   console.log('PASS',label);
   return hash(bytes);
 }
 async function render(){
   await expand();await page.getByLabel('Review the finished video with AI and draft improvements if quality is low',{exact:true}).uncheck();
   const before=(await get(`/api/projects/${seed.pid}`)).result.render_id;
   await button('Review and create version').click();
   const dialog=page.locator('dialog[open]');
   for(const name of await dialog.getByRole('button',{name:/^Approve scene /}).allTextContents())await button(name.trim(),dialog).click();
   const refresh=button('Save and refresh summary',dialog);if(await refresh.count())await refresh.click();
   await button('Create video with these changes',dialog).click();
   await poll(async()=>{const p=await get(`/api/projects/${seed.pid}`);if(p.status==='failed')throw Error(JSON.stringify(p.error));return p.result?.render_id!==before&&['ready','complete','needs_review'].includes(p.status)},'new rendered Master');
   await page.reload();await button('Review and create version').waitFor();
 }
 try{
   await page.goto(origin+'/#project/'+seed.pid);await button('Review and create version').waitFor();
   await tool('Audio');await button('Add music to final video').click();
   await button('Music is in the final video').waitFor();await verifyDelivery('music applied to selected voice');
   await tool('Effects');await button('Gentle zoom').click();
   await page.locator('.manual-clip:visible').first().getByLabel('Approve',{exact:true}).check();
   await page.locator('.manual-clip:visible').first().getByLabel('Lock',{exact:true}).check();
   assert(await button('Gentle zoom').isDisabled());
   await page.locator('.manual-clip:visible').first().getByLabel('Lock',{exact:true}).uncheck();
   await save();await render();const first=await verifyDelivery('first manual render preserves voice and music');
   await tool('Effects');await page.getByRole('spinbutton',{name:'Camera movement duration, seconds',exact:true}).fill('2');
   await page.locator('.manual-clip:visible').first().getByLabel('Approve',{exact:true}).check();
   await tool('Subtitles');await page.getByLabel('Burn edited subtitles into the video',{exact:true}).check();
   await save();await render();const second=await verifyDelivery('second manual render preserves voice and music');
   assert.notEqual(first,second,'Changed motion and captions must produce a different MP4');
   assert((await get(`/api/projects/${seed.pid}`)).result.captions_enabled,'Enabled captions must reach the renderer');
   await page.reload();await button('Review and create version').waitFor();
   assert.equal(await verifyDelivery('reload keeps selected final and download'),second);
   await tool('Review');await expand();await button('Generate full Director Timeline').click();
   await poll(async()=> (await get(base+'/creative-plans')).some(x=>x.status==='ready'),'AI proposal ready');
   await button('Use this plan → Review shots').first().click();
   await button('Review and create version').waitFor();
   const manual=await get(base+'/manual');assert.equal(manual.edit.clips.length,2);assert(manual.edit.clips.every(c=>!c.approved));
   await render();await verifyDelivery('accepted AI plan rendered with selected voice and music');
   const final=await get(`/api/projects/${seed.pid}`);assert.deepEqual(final.result.timeline,[[4,8],[0,2]]);
   await page.screenshot({path:'/tmp/lumen-real-render-acceptance.png',fullPage:true});
   assert.deepEqual(report.errors,[]);report.passed=true;
 }catch(e){report.error=safeError(e);await page.screenshot({path:'/tmp/lumen-real-render-failure.png',fullPage:true});throw e}
 finally{fs.writeFileSync(output,JSON.stringify(report,null,2));await browser.close()}
 console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(safeError(e));process.exitCode=1});
