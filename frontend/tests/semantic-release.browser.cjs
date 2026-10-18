// Current Create Video lifecycle; real API, worker, renderer, playback and download.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),assert=require('assert/strict'),crypto=require('crypto');
const origin=process.env.WORKSPACE_URL,ready=JSON.parse(fs.readFileSync(process.env.RELEASE_READY));
const report={passed:false,checks:[]};const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.addCookies([{name:'lumen_session',value:ready.token,url:origin}]);
 const page=await context.newPage();page.setDefaultTimeout(25000);
 page.on('response',r=>{if(r.status()>=400)console.error('HTTP',r.status(),new URL(r.url()).pathname)});
 await page.addInitScript(()=>localStorage.setItem('lumen_language','en'));
 const get=async url=>{const r=await context.request.get(origin+url);assert(r.ok(),url+': '+r.status());return r.json()};
 const poll=async(fn,label)=>{const end=Date.now()+600000;while(Date.now()<end){if(await fn())return;await page.waitForTimeout(500)}throw Error('timeout '+label)};
 try{
  await page.goto(origin+'/#studio');console.log('studio loaded');await page.screenshot({path:process.env.RELEASE_SCREENSHOT,fullPage:true});
  await page.locator('input[type=file]').first().setInputFiles(process.env.RELEASE_SOURCE);console.log('file selected');
  await page.getByLabel('Output language',{exact:true}).selectOption('zh');
  await page.getByRole('button',{name:'Create project',exact:true}).click();console.log('upload submitted');await page.waitForTimeout(1500);await page.screenshot({path:process.env.RELEASE_SCREENSHOT,fullPage:true});
  await poll(async()=>/project\//.test(page.url()),'project navigation');
  const pid=page.url().split('project/')[1].split(/[?&#]/)[0];report.pid=pid;
  await page.getByRole('button',{name:'Create video',exact:true}).waitFor();
  async function render(previous){
   await page.getByRole('button',{name:'Create video',exact:true}).click();
   await poll(async()=>{const p=await get('/api/projects/'+pid);if(p.status==='failed')throw Error(JSON.stringify(p.error));return p.result?.render_id&&p.result.render_id!==previous&&p.status==='complete'},'render');
   await page.reload();await page.getByRole('button',{name:'Create video',exact:true}).waitFor();
   const p=await get('/api/projects/'+pid);assert.equal(p.result.directorMode,'semantic_openrouter');
   const player=page.locator('.ws-ready-player video').first();
   await player.waitFor();await player.evaluate(async v=>{v.muted=true;await v.play()});
   await poll(()=>player.evaluate(v=>v.currentTime>.2&&!v.error),'playback');await player.evaluate(v=>v.pause());
   const link=page.getByRole('link',{name:'Download video',exact:true}).first();
   const href=await link.getAttribute('href'),r=await context.request.get(new URL(href,origin).href);assert(r.ok());const body=await r.body();
   const playback=await context.request.get(new URL(await player.getAttribute('src'),origin).href);assert(playback.ok());assert.equal(hash(body),hash(await playback.body()));
   const wait=page.waitForEvent('download');await link.click();const download=await wait;assert.equal(await download.failure(),null);assert.equal(hash(fs.readFileSync(await download.path())),hash(body));
   report.checks.push({render:p.result.render_id,mode:p.result.directorMode,download_sha256:hash(body),playback:true});return p.result.render_id;
  }
  const first=await render(null);await render(first);report.passed=true;
  await page.screenshot({path:process.env.RELEASE_SCREENSHOT,fullPage:true});
 }catch(e){await page.screenshot({path:process.env.RELEASE_SCREENSHOT,fullPage:true});report.error=String(e.stack||e).replaceAll(ready.token,'[redacted]');throw e}
 finally{fs.writeFileSync(process.env.RELEASE_REPORT,JSON.stringify(report,null,2));await browser.close()}
})().catch(e=>{console.error(String(e).replaceAll(ready.token,'[redacted]'));process.exitCode=1});
