const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const setup=require('./ui-audit-helper.cjs');
const report={
 scores:{shot_structure:44,visual_pacing:80,effect_similarity:100,motion_graphic_style:15,color_treatment:0,production_quality:70,overall:51.5},
 applied:['cuts','zoom','transitions','enhance','cards','track','mask','exposure','progress','illustration','lower','panel','icon','still','screen','diagram','art','stock'],
 gaps:[{id:'motion_tracking',essential:false},{id:'number_card',essential:true},{id:'blur',essential:false}],
 sections:[{index:0,start:0,end:6},{index:1,start:6,end:12}],
 note:'owned_only'
};
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const x=await setup(browser);
 const base=process.env.WORKSPACE_URL||'http://127.0.0.1:5192';
 try{
  await x.page.goto(base+'/#studio');
  await x.page.getByRole('heading',{name:'Learn the technique. Tell your story.'}).waitFor();
  const box=x.page.locator('input[name=style_match]');
  assert.equal(await box.isChecked(),false);
  await x.page.getByText('Reference video').waitFor();
  await x.page.getByText('Upload the reference video. The finished film still uses only your footage.').waitFor();
  assert.equal(await x.page.locator('input.director-file-input').count(),2);
  await box.check();
  assert.equal(await x.page.locator('input.director-file-input').count(),2);
  await box.uncheck();
  assert.equal(await x.page.locator('input.director-file-input').count(),2);
  x.data.studio.context.style_match=true;
  x.data.studio.context.style_report=report;
  x.data.studio.context.style_match_status='pending';
  await x.goto();
  const fold=x.page.locator('.ws-preview .style-match-fold');
  await fold.waitFor();
  assert.equal(await x.page.locator('.ws-inspector .style-match-fold').count(),0);
  assert.equal(await fold.evaluate(el=>el.open),false);
  await fold.locator('summary').click();
  await x.page.getByText('Needs your input').first().waitFor();
  await x.page.getByText('Not reproduced').first().waitFor();
  await x.page.getByText('Exposure and color were lifted slightly.').waitFor();
  await x.page.getByText('Charts and number cards use figures from your script.').waitFor();
  await x.page.getByText('Blur is not available.').waitFor();
  await x.page.getByText('The frame follows where the detail moves.').waitFor();
  await x.page.getByText('The presenter sits in a soft window over a clean plate.').waitFor();
  await x.page.getByText('Exposure was shifted toward the reference measurement.').waitFor();
  await x.page.getByText('A progress bar follows the position in the cut.').waitFor();
  await x.page.getByText('A title-like reference shot is replaced by a chart of your figures, fading in and out.').waitFor();
  await x.page.getByText('A lower band fades in and out over the presenter.').waitFor();
  await x.page.getByText('A small mark fades in and out on that band.').waitFor();
  await x.page.getByText('A title-like shot with no figures holds another frame of your footage, then lets it go.').waitFor();
  await x.page.getByText('A screen-like reference shot holds your frame inside a border, then lets it go.').waitFor();
  await x.page.getByText('An illustration of equal shapes is drawn from your words and fades out.').waitFor();
  await x.page.getByText('One generated picture uses your words. It has no text from the reference.').waitFor();
  await x.page.getByText('A Commons clip with a CC BY, CC0, or public-domain license was inserted. Its credit stays on the asset.').waitFor();
  await x.page.getByText('The other half of a split frame is another moment of your footage.').waitFor();
  await x.page.getByText('Approve renders the saved edit with the voice and music you selected. It does not publish the video, and it does not copy the reference. The editor stays on this page.').waitFor();
  await x.page.getByText('A score of 100 is not a picture match.').waitFor();
  await x.page.getByText('Frames have not been compared yet.').waitFor();
  assert.equal(await x.page.getByText('Effect similarity', {exact: true}).count(), 0);
  Object.assign(report, {compared: true, effect_similarity_rule: 100, measured_effect_similarity: 40});
  report.scores.effect_similarity = 70;
  report.scores.overall = 95;
  await x.goto();
  const compared = x.page.locator('.ws-preview .style-match-fold');
  await compared.waitFor();
  await compared.evaluate(el => { el.open = true; });
  await x.page.getByText('Effect similarity averages the rule score with the measured frames. It is not a copy of the reference.').waitFor();
  await x.page.getByText('Effect similarity: 70/100').waitFor();
  await x.page.getByText('Frame measurement: 40/100').waitFor();
  await x.button('Approve this cut').click();
  await x.button('Regenerate video').click();
  await x.page.getByRole('combobox',{name:'Style section',exact:true}).selectOption('1');
  await x.button('Regenerate selected section').click();
  const paths=x.writes.map(w=>w.path);
  assert.ok(paths.some(p=>p.endsWith('/style-match/approve')));
  assert.ok(paths.some(p=>p.endsWith('/style-match/regenerate')));
  assert.ok(paths.some(p=>p.endsWith('/style-match/sections/1/regenerate')));
  assert.deepEqual(x.errors,[]);
  await x.page.screenshot({path:'/tmp/lumen-style-match.png'});
  console.log('PASS style match');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
