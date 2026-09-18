const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const setup=require('./ui-audit-helper.cjs');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true}),results=[];
async function test(name,fn){if(process.env.UI_AUDIT_MATCH&&!name.includes(process.env.UI_AUDIT_MATCH))return;const x=await setup(browser);try{await x.goto();await fn(x);assert.deepEqual(x.errors,[]);results.push({name,pass:true});console.log('PASS',name)}catch(e){results.push({name,pass:false,error:e.message.split('Call log:')[0]});console.log('FAIL',name,e.message.split('Call log:')[0]);await x.page.screenshot({path:'/tmp/lumen-qa-'+name.replaceAll(/[^a-z0-9]/gi,'-')+'.png'})}finally{await x.page.close()}}
try{
await test('scene selection and inspect seeks source',async({page,button,expand})=>{
 await page.locator('.ws-scenes button').nth(1).click();await expand();const v=page.locator('.manual-screen video');await v.evaluate(el=>{let at=9;Object.defineProperty(el,'currentTime',{configurable:true,get:()=>at,set:v=>{at=v}})});
 await button('Inspect',page.locator('.manual-clip:visible').first()).click();assert.equal(await v.evaluate(el=>Math.round(el.currentTime)),6);
});
await test('scene reorder add remove and locked controls',async({page,button,expand,draft})=>{
 await expand();const clip=page.locator('.manual-clip:visible').first();await button('Move down',clip).click();assert.equal((await draft()).clips[1].id,'one');await button('Move up',page.locator('.manual-clip:visible').first()).click();assert.equal((await draft()).clips[0].id,'one');
 await page.locator('.manual-clip:visible').first().getByLabel('Lock',{exact:true}).check();assert(await page.getByLabel('Source end (s)',{exact:true}).first().isDisabled());await page.locator('.manual-clip:visible').first().getByLabel('Lock',{exact:true}).uncheck();
 await button('Add clip from source').click();assert.equal(await page.locator('.ws-scenes button').count(),3);await expand();await button('Remove clip',page.locator('.manual-clip:visible').first()).click();assert.equal(await page.locator('.ws-scenes button').count(),2);
});
await test('draft preview before after play pause',async({page,button,tool,draft})=>{
 await tool('Effects');await button('Gentle zoom').click();assert.equal((await draft()).clips[0].zoom_end,1.2);assert.equal((await draft()).clips[0].approved,false);
 await button('Before').click();assert.equal(await page.locator('.manual-screen video').evaluate(e=>e.style.transform),'none');await button('After').click();await button('Play selected range').click();await page.waitForFunction(()=>document.querySelector('.manual-screen video').currentTime>.1);await button('Pause').click();assert(await page.locator('.manual-screen video').evaluate(e=>e.paused));await button('No motion').click();assert.equal((await draft()).clips[0].zoom_end,1);
});
await test('inspector scene navigation presets and lock',async({page,button,tool,draft})=>{
 await tool('Effects');const scene=page.getByRole('combobox',{name:'Select scene',exact:true});
 assert(await button('Previous scene').isDisabled());await button('Next scene').click();assert.equal(await scene.inputValue(),'1');assert(await button('Next scene').isDisabled());
 await button('Cross dissolve',page.locator('.manual-clip:visible')).click();assert.equal((await draft()).clips[1].transition,'crossfade');
 await scene.selectOption('0');const clip=page.locator('.manual-clip:visible');await clip.getByRole('slider',{name:/^End horizontal position/}).focus();await page.keyboard.press('End');await button('No motion').click();const c=(await draft()).clips[0];assert.equal(c.x_end,c.x);
 await clip.getByLabel('Approve',{exact:true}).check();await clip.getByLabel('Lock',{exact:true}).check();assert(await button('Gentle zoom').isDisabled());
 await button('Next scene').click();assert.equal(await scene.inputValue(),'1');await button('Previous scene').click();assert.equal(await scene.inputValue(),'0');
});
await test('first scene cannot use incoming dissolve',async({page,button,tool})=>{await tool('Effects');assert(await button('Cross dissolve',page.locator('.ws-effect-presets').first()).isDisabled());});
await test('save discard reload and approval',async({page,button,tool,save,data})=>{
 await tool('Effects');await button('Gentle zoom').click();await page.locator('.manual-clip:visible').first().getByLabel('Approve',{exact:true}).check();await save();assert.equal(data.manual.edit.clips[0].zoom_end,1.2);await page.locator('.manual-clip:visible .inspector-text > summary').click();await page.getByLabel('Text overlay for this clip',{exact:true}).first().fill('QA draft');await button('Discard edits').click();await page.waitForFunction(()=>document.querySelector('.ws-footer')?.textContent.includes('Saved'));assert.equal(await page.getByLabel('Text overlay for this clip',{exact:true}).first().inputValue(),'');
});
await test('captions styles add remove and empty validation',async({page,button,tool,draft})=>{
 await tool('Subtitles');await page.getByRole('combobox',{name:/^Size/}).selectOption('large');await page.getByRole('combobox',{name:/^Position/}).selectOption('top');await page.getByRole('combobox',{name:/^Color/}).selectOption('yellow');assert.equal((await draft()).font_size,'large');
 await button('Add subtitle').click();assert.equal(await page.locator('.manual-caption').count(),2);assert(await button('Save manual edits').isDisabled());await page.locator('.manual-caption').last().getByLabel('English',{exact:true}).fill('QA caption');await button('Remove subtitle',page.locator('.manual-caption').last()).click();assert.equal(await page.locator('.manual-caption').count(),1);await button('Adjust framing').click();assert.equal(await button('Edit',page.locator('.ws-tools')).getAttribute('aria-pressed'),'true');
});
await test('sound effects and B-roll controls',async({page,button,tool,expand,draft})=>{
 await tool('Effects');await expand();const clip=page.locator('.manual-clip:visible').first();await button('Add sound accent',clip).click();await clip.getByRole('combobox',{name:/^Sound/}).selectOption('whoosh');assert.equal((await draft()).clips[0].sound_effects[0].kind,'whoosh');await button('Remove',clip).click();assert.equal((await draft()).clips[0].sound_effects.length,0);
 await clip.getByLabel('Add cutaway',{exact:true}).check();assert((await draft()).clips[0].cutaway);await clip.getByRole('combobox',{name:/^Choose footage/}).selectOption('2'.repeat(32));assert.equal((await draft()).clips[0].cutaway,null);assert.equal((await draft()).clips[0].external_broll.asset_id,'2'.repeat(32));await clip.getByRole('combobox',{name:/^Choose footage/}).selectOption('');
});
await test('visual card types rows maps and event controls',async({page,button,tool,expand,draft})=>{
 await tool('Effects');await expand();const clip=page.locator('.manual-clip:visible').first(),type=clip.getByRole('combobox',{name:/^Card type/});
 for(const kind of ['number','comparison','bar_chart','ranking','map','timeline']){await type.selectOption(kind);assert.equal((await draft()).clips[0].card.kind,kind);assert(await button('Save manual edits').isDisabled());if(kind==='bar_chart'){await button('Add row',clip).click();assert.equal((await draft()).clips[0].card.items.length,3);await button('Remove row',clip).last().click();await clip.getByRole('combobox',{name:/^Bar animation/}).selectOption('grow')}
 if(kind==='map'){await button('Add location',clip).click();assert.equal((await draft()).clips[0].card.locations.length,2);await button('Remove location',clip).last().click()}
 if(kind==='timeline'){await button('Add event',clip).click();assert.equal((await draft()).clips[0].card.milestones.length,3);await button('Remove event',clip).last().click()}}
 await type.selectOption('none');assert.equal((await draft()).clips[0].card,null);
});
await test('soundtrack filters favorite add and copy',async({page,button,tool,writes})=>{
 await tool('Audio');await page.locator('.audio-library > summary').click();const lib=page.locator('.soundtrack-library');await button('Favorite: QA soundtrack',lib).click();await button('Favorites',lib).click();await page.getByText('QA soundtrack',{exact:true}).waitFor();await lib.getByLabel('Search',{exact:true}).fill('no such track');assert.equal(await lib.locator('.soundtrack-track').count(),0);await lib.getByLabel('Search',{exact:true}).fill('');await button('Add to project',lib).click();await button('Added to project',lib).waitFor();await lib.locator('summary').click();await button('Copy credit',lib).click();await button('Copied',lib).waitFor();assert(writes.some(w=>w.path.endsWith('/favorite')));
});
await test('music editing volume lock rhythm and beat preview',async({page,button,tool,expand,draft,save})=>{
 await tool('Audio');await page.getByRole('combobox',{name:/^Track/}).selectOption('1'.repeat(32));await page.locator('.music-advanced > summary').click();await button('Add volume point').click();await button('Add volume point').click();assert.equal((await draft()).music.levels.length,2);await button('Remove point').last().click();await page.getByRole('spinbutton',{name:/^Music level/}).fill('-12');assert.equal((await draft()).music.levels.length,0);await button('Analyze music rhythm').click();await button('Align an accent to the first approved cut (6.0s)').click();await button('Lock music').click();assert(await page.getByRole('combobox',{name:/^Track/}).isDisabled());await button('Unlock music').click();await save();await expand();await button('Find safe beat edits').click();await page.getByText('No safe alignment found. The current edit stays unchanged.').waitFor();
});
await test('AI soundtrack select and apply',async({page,button,tool,expand,writes,data})=>{
 await tool('Audio');await expand();const box=page.locator('details').filter({has:page.locator('summary').filter({hasText:'AI soundtrack selection'})});await box.getByLabel('QA music',{exact:true}).check();await button('Suggest a soundtrack',box).click();await button('Apply and update final video',box).click();await page.waitForFunction(()=>document.querySelector('.ws-footer')?.textContent.includes('Saved'));assert(data.manual.edit.music);assert(writes.some(w=>w.path.endsWith('/music/accept')));await page.waitForFunction(()=>document.querySelector('.ws-ready-player video')?.getAttribute('src')?.includes('/final-music/'));assert(writes.some(w=>w.path.endsWith('/final-music')));
});
await test('upload music shortcut and media upload',async({page,button,tool,expand,writes})=>{
 await tool('Audio');await expand();await button('Upload music').click();assert.equal(await button('Materials',page.locator('.ws-tools')).getAttribute('aria-pressed'),'true');const lib=page.locator('.media-library');await page.waitForFunction(()=>document.querySelector('.media-library select')?.value==='music');await lib.locator('input[type=file]').setInputFiles({name:'qa.wav',mimeType:'audio/wav',buffer:Buffer.from('qa fixture')});await lib.getByLabel('Source / license attribution').fill('QA owned');await lib.getByLabel('I have permission to use this footage.').check();await button('Upload to library',lib).click();await page.getByText('Uploaded successfully — ready to use').waitFor();assert(writes.some(w=>w.path.endsWith('/upload/asset')));
});
await test('music updates the final player and download after reload',async({page,button,tool,data,writes})=>{
 await tool('Audio');await page.getByRole('combobox',{name:/^Track/}).selectOption('1'.repeat(32));assert(await page.locator('.ws-ready-player').isVisible());
 await button('Add music to final video').click();await page.waitForFunction(()=>document.querySelector('.ws-ready-player video')?.getAttribute('src')?.includes('/final-music/'));
 assert(writes.some(w=>w.path.endsWith('/manual')&&w.method==='PUT'));assert(writes.some(w=>w.path.endsWith('/final-music')));assert(!writes.some(w=>w.path.endsWith('/manual/render')));
 assert.equal(await page.locator('.ws-header-download').getAttribute('href'),`/api/projects/${data.project.id}/media/result`);
 await page.reload();await page.waitForFunction(()=>document.querySelector('.ws-ready-player video')?.getAttribute('src')?.includes('/final-music/'));await tool('Audio');assert.match(await page.locator('.final-music-current').innerText(),/QA music/);assert(await button('Music is in the final video').isDisabled());
});
await test('voiceover becomes persistent final output',async({page,button,tool,data,writes})=>{
 await tool('Audio');await page.locator('.audio-voiceover > summary').click();const versions=page.locator('.dubbing-version');
 assert(await button('Use in final video',versions.nth(1)).isDisabled());
 await button('Use in final video',versions.first()).click();
 assert(writes.some(w=>w.path.endsWith('/dubbing/final')&&w.body.version_id==='c'.repeat(32)));
 await page.waitForFunction(()=>document.querySelector('.ws-ready-player video')?.getAttribute('src')?.includes('/dubbing/'));
 assert.match(await page.locator('.ws-preview-heading').innerText(),/Finished video.*Russian male/);
 await page.reload();await page.locator('.ws-ready-player video').waitFor();await page.waitForFunction(()=>document.querySelector('.ws-ready-player video')?.getAttribute('src')?.includes('/dubbing/'));
 await tool('Audio');await page.locator('.audio-voiceover > summary').click();assert(await page.getByText('Used in final video',{exact:true}).isVisible());
 await button('Use original edit audio').click();await page.waitForFunction(()=>document.querySelector('.ws-ready-player video')?.getAttribute('src')?.includes('/media/result'));
 assert.equal(data.dubbing.final_version_id,'master');
});
await test('voice sample and translated version submission',async({page,button,tool,writes})=>{
 await tool('Audio');await page.locator('.audio-voiceover > summary').click();await page.getByRole('combobox',{name:/^Voiceover language/}).selectOption('en');await button('Preview voice').click();assert(writes.some(w=>w.path.endsWith('/dubbing')&&w.body.kind==='sample'));await button('Create dubbed version').click();assert(writes.some(w=>w.path.endsWith('/dubbing')&&w.body.kind==='video'));assert.equal(writes.at(-1).body.language,'en');
});
await test('AI individual regeneration and replacement',async({page,button,expand,writes,data})=>{
 await expand();const box=page.locator('.timeline-regenerate');await box.getByLabel('What should improve?').fill('Add a gentle zoom');await button('Regenerate decision',box).click();await button('Replace this decision',box).click();assert(writes.some(w=>w.path.endsWith('/proposal/accept')));assert.equal(data.manual.edit.clips[0].approved,false);
});
await test('AI full plan generation apply and review',async({page,button,tool,expand,writes,data})=>{
 await tool('Review');await expand();await button('Generate full Director Timeline').click();await button('Use this plan → Review shots').first().click();await page.waitForFunction(()=>document.querySelector('.ws-tools button[aria-pressed=true]')?.textContent==='Edit');assert(data.manual.edit.clips.every(c=>!c.approved));assert(writes.some(w=>w.path.endsWith('/creative/accept')));
});
await test('alternative requires decision then generates and replaces',async({page,button,tool,expand,writes})=>{
 await tool('Review');await expand();await button('Suggest alternative').click();assert.equal(writes.length,0);await page.getByRole('combobox',{name:/^Decision/}).selectOption('cut');await page.getByLabel('What should change?').fill('Trim less');await button('Suggest alternative').click();await button('Replace this decision').click();assert(writes.some(w=>w.path.endsWith('/alternative/accept')));
});
await test('stock candidate opens AI matching controls',async({page,button,tool,expand})=>{
 await tool('Materials');await expand();await page.getByLabel('Visual subject',{exact:true}).fill('pool');await button('Search external footage').click();await button('Find a suitable moment with AI').click();assert(await page.locator('.timeline-regenerate').isVisible());await page.waitForFunction(()=>document.querySelector('.timeline-regenerate select')?.value==='library_broll');
});
await test('platform approval lock reopen edit and history',async({page,button,tool,data,writes})=>{
 await tool('Review');await button('Platform versions',page.locator('.director-tabs')).click();await button('Approve this version').click();await button('Lock approved version').click();assert(await button('Edit this version').isDisabled());await button('Unlock').click();await button('Reopen review').click();await button('Edit this version').click();await page.getByLabel('On-screen title',{exact:true}).fill('Changed title');await button('Cancel editing').click();assert.equal(data.pack.result.variants[0].title,'QA title');await page.getByRole('combobox',{name:/^Package history/}).selectOption('pack0');await button('Restore this package').click();assert(writes.some(w=>w.path.endsWith('/variants/restore')));
});

await test('cleanup render requires actual plan summary and confirmation',async({page,button,tool,expand,writes})=>{
 await tool('Review');await expand();await button('Review and render approved plan').click();await page.locator('dialog[open] .render-summary').waitFor();assert.equal(writes.length,0);assert.match(await page.locator('dialog[open]').innerText(),/Manual effects, music and the editor timeline are not included/);await button('Back to editing',page.locator('dialog[open]')).click();assert.equal(writes.length,0);
 await button('Review and render approved plan').click();await page.locator('dialog[open] .render-summary').waitFor();await button('Create video with these changes',page.locator('dialog[open]')).click();await page.waitForTimeout(100);assert(writes.some(w=>w.path.endsWith('/render')&&!w.path.includes('/manual/')));
});
await test('timeline view switches and scene activation',async({page,button})=>{
 await page.locator('.ws-scene-list > details > summary').click();await button('Approved output').click();assert.equal(await button('Approved output').getAttribute('aria-pressed'),'true');await button('Proposed timeline').click();assert.equal(await button('Proposed timeline').getAttribute('aria-pressed'),'true');
});
await test('save failure preserves draft and exposes retry',async({page,button,tool,draft,writes})=>{
 await tool('Effects');await button('Gentle zoom').click();await page.route('**/manual',async r=>r.request().method()==='PUT'?r.fulfill({status:409,json:{detail:'plan_changed'}}):r.fallback());await button('Save manual edits').click();await page.getByRole('alert').filter({hasText:'The plan changed. Reload saved edits before continuing.'}).waitFor();assert.equal((await draft()).clips[0].zoom_end,1.2);assert(await button('Save manual edits').isEnabled());
});
await test('platform create submits reviewed duration and story choices',async({page,button,tool,data,writes})=>{
 data.pack=null;await tool('Review');await button('Platform versions',page.locator('.director-tabs')).click();assert(await button('Create 5 versions').isDisabled());await page.getByLabel('I reviewed this master and approve creating platform previews.').check();await button('Create 5 versions').click();await page.waitForTimeout(100);const action=writes.find(w=>w.path.endsWith('/variants'));assert(action.body.reviewed);assert.equal(action.body.max_seconds.youtube_shorts,60);
});

await test('platform manual form captions ranges and save',async({page,button,tool,writes})=>{
 await tool('Review');await button('Platform versions',page.locator('.director-tabs')).click();await button('Edit this version').click();const form=page.locator('.variant-edit-form');await form.getByRole('combobox',{name:/^Export frame/}).selectOption('1:1');await form.getByRole('combobox',{name:/^Caption mode/}).selectOption('custom');await form.getByRole('combobox',{name:/^Size/}).selectOption('large');await button('Use as opening',form).last().click();assert.equal(await form.getByLabel('Start (s)',{exact:true}).first().inputValue(),'6');await button('Move later',form).first().click();await form.getByLabel('On-screen title',{exact:true}).fill('Edited QA title');await form.locator('button[type=submit]').click();await page.waitForTimeout(100);const submitted=writes.find(w=>w.path.endsWith('/variants/edit'));assert.equal(submitted.body.aspect,'1:1');assert.equal(submitted.body.caption_size,'large');assert.equal(submitted.body.title,'Edited QA title');
});

await test('all AI clip modes send explicit scoped tasks',async({page,button,expand,writes})=>{
 await expand();const panel=page.locator('.timeline-regenerate');
 for(const mode of ['visual_card','sound_effects','generated_broll','library_broll']){
  await panel.getByRole('combobox',{name:/^Task/}).selectOption(mode);await panel.getByLabel('What should improve?').fill('QA intentional change');if(mode==='library_broll')await panel.getByLabel('QA B-roll',{exact:true}).check();await button(mode==='library_broll'?'Suggest matching B-roll':'Regenerate decision',panel).click();await page.waitForTimeout(100);const sent=writes.filter(w=>w.path.endsWith('/timeline-proposals')).at(-1);assert.equal(sent.body.mode,mode);assert.equal(sent.body.clip_id,'one');
 }
});
await test('stock discovery request and direct placement',async({page,button,tool,expand,writes,draft})=>{
 await tool('Materials');await expand();await button('AI: find B-roll for this scene').click();assert(writes.some(w=>w.path.endsWith('/stock/discover')&&w.body.clip_id==='one'));await page.getByLabel('Visual subject',{exact:true}).fill('pool');await button('Search external footage').click();await page.getByRole('button',{name:/^Place in selected scene/}).click();assert.equal((await draft()).clips[0].external_broll.asset_id,'2'.repeat(32));assert.equal((await draft()).clips[0].approved,false);
});
}finally{await browser.close();require('fs').writeFileSync(process.env.UI_AUDIT_MATCH?'/tmp/lumen-ui-audit-browser-retry.json':'/tmp/lumen-ui-audit-browser.json',JSON.stringify(results,null,2));}if(results.some(r=>!r.pass))process.exitCode=1;
})();
