const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const setup=require('./ui-audit-helper.cjs');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const {page,goto,button,writes,errors,data}=await setup(browser);let blocked=false;
 await page.route('**/manual/summary',r=>r.fulfill({json:{revision:data.manual.revision,source_duration:12,output_duration:12,removed_seconds:0,removed_ranges:[],near_original:false,captions:0,music:true,normalize:false,global_operations:[],pending_proposals:{},clips:[],voiceover:blocked?{error:'voiceover_range_unavailable'}:{language:'ru',voice:'ru-male'}}}));
 await goto();await button('Review and create version').click();
 await page.getByText(/The selected voiceover will stay in the new edit/).waitFor();
 assert(await button('Create video with these changes').isEnabled());assert.equal(writes.length,0);
 await button('Back to editing').click();blocked=true;await button('Review and create version').click();
 await page.getByRole('alert').filter({hasText:'The selected voice cannot be carried safely'}).waitFor();
 assert(await button('Create video with these changes').isDisabled());assert.equal(writes.length,0);assert.deepEqual(errors,[]);
 console.log('PASS selected voice retention summary and unavailable coverage prevents render');
 }finally{await browser.close()}})().catch(e=>{console.error(e.message);process.exit(1)});
