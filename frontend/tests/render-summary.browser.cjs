const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const seed=require('./fixtures/workspace.cjs');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:390,height:844}});
 await page.addInitScript(()=>localStorage.setItem('lumen_language','ru'));
 let mode='error',writes=0;
 const pid=seed.project.id;
 await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;
 if(route.request().method()!=='GET'){writes++;return route.fulfill({json:{ok:true}})}
 if(path.endsWith('/summary')){
 if(mode==='error')return route.fulfill({status:503,json:{}});
 return route.fulfill({json:{revision:mode==='stale'?99:1,source_duration:162.1,output_duration:160.5,removed_seconds:1.6,removed_ranges:[[160.5,162.1]],near_original:true,captions:0,music:false,normalize:true,global_operations:['trim','normalize'],pending_proposals:{creative:3},clips:[{id:'one',start:0,end:160.5,source_start:0,source_end:160.5,operations:[]}]}});
 }
 let json=[];
 if(path==='/api/session')json={email:'test@example.test'};
 else if(path==='/api/projects')json=[seed.project];
 else if(path===`/api/projects/${pid}`)json=seed.project;
 else if(path===`/api/studio/projects/${pid}`)json=seed.studio;
 else if(path.endsWith('/manual'))json=seed.manual;
 else if(path.endsWith('/dubbing'))json=seed.dubbing;
 return route.fulfill({json});});
 await page.goto((process.env.WORKSPACE_URL||'http://127.0.0.1:5192')+'/#project/'+pid);
 const open=page.getByRole('button',{name:'Проверить и создать версию',exact:true});
 await open.click();
 const confirm=page.getByRole('button',{name:'Создать видео с этими изменениями',exact:true});
 await page.getByRole('button',{name:'Повторить',exact:true}).waitFor();assert(await confirm.isDisabled());
 mode='stale';await page.getByRole('button',{name:'Повторить',exact:true}).click();
 await page.getByText(/Монтаж изменился. Закройте/).waitFor();assert(await confirm.isDisabled());
 await page.getByRole('button',{name:'Вернуться к редактированию',exact:true}).click();
 mode='ok';await open.click();await page.getByText('Видео будет почти идентично исходнику',{exact:true}).waitFor();
 assert(await confirm.isEnabled());assert.equal(writes,0);
 assert(await page.locator('dialog[open]').evaluate(el=>el.scrollWidth<=el.clientWidth));
 await page.screenshot({path:'/tmp/lumen-render-summary-mobile.png'});
 console.log('PASS summary error, stale revision, retry, near-original warning, mobile overflow, no accidental render');
 }finally{await browser.close()}})().catch(e=>{console.error(e.message.split('Call log:')[0]);process.exit(1)});
