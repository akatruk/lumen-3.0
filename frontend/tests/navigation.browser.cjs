const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const assert=require('node:assert/strict');const setup=require('./ui-audit-helper.cjs');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});const results=[];
async function test(name,fn){const x=await setup(browser);try{await x.goto();await fn(x);assert.deepEqual(x.errors,[]);console.log('PASS',name);results.push({name,pass:true})}catch(e){console.log('FAIL',name,e.message.split('Call log:')[0]);results.push({name,pass:false,error:e.message.split('Call log:')[0]});await x.page.screenshot({path:'/tmp/lumen-nav-'+name.replaceAll(/[^a-z0-9]/gi,'-')+'.png'})}finally{await x.page.close()}}
try{
 await test('navigation project search and language persistence',async({page,button})=>{
 await page.locator('aside nav').getByRole('button',{name:/Your projects/}).click();const search=page.locator('.search input');await search.fill('nonexistent');assert.equal(await page.locator('.project-card').count(),0);await page.locator('.search button').click();await page.locator('.project-card').waitFor();await page.locator('.project-card').click();await page.locator('.ws-heading h1').waitFor();
 const language=page.locator('.topbar .locale-select select');assert.equal(await page.locator('.locale-select:visible').count(),1);for(const lang of ['ru','zh','en']){await language.selectOption(lang);assert.equal(await page.evaluate(()=>localStorage.getItem('lumen_language')),lang)}await page.reload();await page.locator('.ws-heading h1').waitFor();assert.equal(await language.inputValue(),'en');
 });
 await test('mobile navigation open close and workspace',async({page,button})=>{
 await page.setViewportSize({width:390,height:844});await page.locator('.topbar button').first().click();await button('Workspace',page.locator('aside nav')).click();await page.locator('.settings-page').waitFor();assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 });
 await test('new project search reference preview upload submit',async({page,button,writes,uploadConfig})=>{
 await button('New project',page.locator('aside')).click();await page.getByRole('textbox',{name:'Search Douyin',exact:true}).fill('travel');await button('Search Douyin').click();await button('Load more').click();assert.equal(await page.locator('.douyin-card').count(),1);await button('Add reference').click();assert(await button('Added').isDisabled());await button('Remove').click();await button('Add reference').click();
 await page.locator('input[type=file]').setInputFiles({name:'owned.mp4',mimeType:'video/mp4',buffer:Buffer.from('qa fixture')});await page.locator('input[name=title]').fill('QA project');await page.locator('textarea[name=script]').fill('QA travel narrative');await page.locator('input[name=audience]').fill('Travellers');await page.locator('input[name=tone]').fill('Clear');await page.locator('input[name=rights]').check();await button('Analyze & build my plan').click();await page.locator('.ws-heading h1').waitFor();assert(writes.some(w=>w.path.endsWith('/upload/complete')));assert.equal(uploadConfig().title,'QA project');
 });
 await test('visual effect plaque saves a look and compares the frame',async({page,button})=>{
 await button('Visual effects',page.locator('aside nav')).click();await page.getByRole('heading',{name:'Effect recipe'}).waitFor();await page.getByLabel('Starting look').selectOption('punch');await page.getByRole('switch',{name:'Blur',exact:true}).click();await button('Save').click();
 const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('lumen_effect_board')));assert.equal(saved.name,'punch');assert.equal(saved.effects.blur,true);assert.equal(saved.effects.glow,false);
 const compare=page.getByRole('slider',{name:'Compare'});await compare.fill('24');assert.equal(await compare.inputValue(),'24');
 });
 await test('guide mode and chapter seeking',async({page,button})=>{
 await page.route('**/tutorial/*.mp4',r=>r.fulfill({path:process.env.WORKSPACE_MEDIA,contentType:'video/mp4'}));await button('Video guide',page.locator('aside nav')).click();await page.locator('.tutorial-tabs button').first().click();assert.equal(await page.locator('.tutorial-tabs button').first().getAttribute('aria-pressed'),'true');await page.locator('.tutorial-tabs button').nth(1).click();await page.locator('.tutorial-chapters button').first().click();assert.equal(await page.locator('.tutorial-tabs button').nth(1).getAttribute('aria-pressed'),'true');
 });
 await test('logout failure is visible and does not crash',async({page,button})=>{
 await page.route('**/api/logout',r=>r.fulfill({status:503,json:{detail:'temporarily_unavailable'}}));await button('Sign out').click();await page.getByText('The request could not be completed. Please try again.').waitFor();assert.equal(await page.locator('.project-workspace').count(),1);
 });

 await test('missing project stops polling and returns to the library',async({page})=>{
  let hits=0;await page.route('**/api/projects/deadbeefdeadbeefdeadbeefdeadbeef',route=>{hits++;return route.fulfill({status:404,contentType:'application/json',body:JSON.stringify({detail:'not_found'})})});
  await page.goto((process.env.WORKSPACE_URL||'http://127.0.0.1:5192')+'/#project/deadbeefdeadbeefdeadbeefdeadbeef');
  await page.getByRole('heading',{name:'This project is not available.'}).waitFor();
  await page.waitForTimeout(4200);assert.equal(hits,1);assert.equal(await page.locator('.loading').count(),0);
  await page.getByRole('button',{name:'Back to projects'}).click();
  await page.waitForFunction(()=>location.hash==='#library');
 });
 await test('logout returns to email sign-in',async({page,button,writes})=>{
 await button('Sign out').click();await page.locator('.auth-form').waitFor();assert.equal(await page.getByRole('button',{name:/Continue with Google/}).count(),0);await page.getByLabel('Email address').waitFor();await page.getByLabel('Password').waitFor();assert(writes.some(w=>w.path==='/api/logout'));
 });
}finally{await browser.close();require('fs').writeFileSync('/tmp/lumen-nav-audit.json',JSON.stringify(results,null,2))}if(results.some(r=>!r.pass))process.exitCode=1})();
