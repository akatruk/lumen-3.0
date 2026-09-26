const {test}=require('node:test');const assert=require('node:assert/strict');const ts=require('typescript');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const file=path.resolve(__dirname,'../src/layerTiming.ts');
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const exposed={};vm.runInNewContext(code,{exports:exposed});
const {calloutBars,cardBar,progressBar,blurBar,glowBar,shadowBar,brollBar,joinBars,clipLayers,speedBar,speedText}=exposed;
const plain=value=>JSON.parse(JSON.stringify(value));

test('callout reads effect_at and effect_end and caps entrance at 0.98',()=>{
  assert.deepEqual(plain(calloutBars({start:0,end:2,text:'Visa',effect_at:0.25,effect_end:0.75})),[{start:0.5,end:1.5}]);
  assert.deepEqual(plain(calloutBars({start:0,end:2,text:'Late',effect_at:0.99,effect_end:1})),[{start:1.96,end:2}]);
  assert.deepEqual(plain(calloutBars({start:1,end:3,text:'Open',effect_at:0.5})),[{start:1,end:2}]);
  const exact=calloutBars({start:0,end:2.345678,text:'Hold',effect_at:0.25,effect_end:1});
  assert.equal(exact[0].end,2.345678);
  assert.equal(calloutBars({start:0,end:2,text:'Hi',effect_at:0.5,effect_end:0.1})[0].end,2);
  assert.deepEqual(plain(calloutBars({start:0,end:2,text:'  ',effect_at:0.5,effect_end:0.8})),[]);
});

test('kinetic marks and title motion are used only when those fields exist',()=>{
  assert.deepEqual(plain(calloutBars({start:0,end:4,text:'One Two',kinetic:true,kinetic_at:[0.25,0.5]})),[{start:1,end:2},{start:2,end:4}]);
  assert.deepEqual(plain(calloutBars({start:0,end:4,text:'Move',kinetic:true,title_x:0.2,title_in:0.25,title_out:0.75,kinetic_at:[]})),[{start:1,end:3}]);
  assert.equal(calloutBars({start:0,end:4,text:'Move',kinetic:true,title_x:0.2,title_in:0.25,title_out:1})[0].end,4);
  assert.equal(calloutBars({start:0,end:4,text:'A B',kinetic:true,title_x:0.2,title_in:0.1,title_out:0.2,kinetic_at:[0.25,0.5]})[0].start,1);
  assert.deepEqual(plain(calloutBars({start:0,end:4,text:'One',kinetic:true,kinetic_at:[0.25]})),[{start:1,end:4}]);
  assert.deepEqual(plain(calloutBars({start:0,end:4,text:'Move',kinetic:true,title_x:0.2,title_in:0.25,title_out:0.75,kinetic_at:[0.1]})),[{start:1,end:3}]);
  assert.deepEqual(plain(calloutBars({start:0,end:4,text:'Plain',kinetic:false,title_x:0.2,title_in:0.25,title_out:0.5,effect_at:0.1,effect_end:0.4})),[{start:0.4,end:1.6}]);
});

test('card and progress read stored windows and omit an absent layer',()=>{
  const span=2.345678;
  const card=cardBar({start:0,end:span,card:{start:0.2,end:span}});
  assert.equal(card.end,span);
  assert.notEqual(card.end,Math.round(span*1000)/1000);
  assert.equal(cardBar({start:0,end:2,text:'A'}),null);
  assert.deepEqual(plain(progressBar({start:0,end:4,progress:0.8,progress_at:0.25,progress_end:0.75})),{start:1,end:3});
  assert.equal(progressBar({start:0,end:4,progress:0.8,progress_at:0.25,progress_end:1}).end,4);
  assert.equal(progressBar({start:0,end:4,progress:0,progress_at:0.25,progress_end:0.75}),null);
  assert.deepEqual(plain(clipLayers({start:0,end:2,text:''}).map(layer=>layer.id)),['shot']);
  assert.deepEqual(plain(clipLayers({start:0,end:2,text:'Hi',effect_at:0,effect_end:1,card:{start:0,end:2},progress:0.5,progress_at:0,progress_end:1}).map(layer=>layer.id)),['shot','callout','card','progress']);
});

test('blur and the join get their own rows from the stored clip',()=>{
  assert.deepEqual(plain(blurBar({start:0,end:2,blur:2,effect_at:0.25,effect_end:0.5})),{start:0.5,end:1});
  assert.deepEqual(plain(blurBar({start:0,end:2,blur:2,effect_at:0.25,effect_end:0.6})),{start:0.5,end:1.2});
  assert.deepEqual(plain(blurBar({start:0,end:2,blur:2,effect_at:0.25,effect_end:1})),{start:0.5,end:2});
  assert.deepEqual(plain(blurBar({start:0,end:2,blur:2,effect_at:0})),{start:0,end:2});
  assert.equal(blurBar({start:0,end:2,blur:0.2,effect_at:0.5}),null);
  assert.equal(blurBar({start:0,end:2,blur:0}),null);
  assert.deepEqual(plain(joinBars({start:0,end:4,transition:'cut'})),[]);
  assert.deepEqual(plain(joinBars({start:0,end:4,transition:'wipe-down'})),[{start:0,end:0.4}]);
  assert.deepEqual(plain(joinBars({start:0,end:4,transition:'diagtl'})),[{start:0,end:0.4}]);
  assert.deepEqual(plain(joinBars({start:0,end:4,transition:'wipe-up',transition_seconds:1.2})),[{start:0,end:0.6}]);
  assert.deepEqual(plain(joinBars({start:0,end:1,transition:'crossfade',transition_seconds:2.4})),[{start:0,end:0.25}]);
  assert.deepEqual(plain(joinBars({start:0,end:4,transition:'fade'})),[{start:0,end:0.25},{start:3.75,end:4}]);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',blur:1.5,transition:'wipe-down'}).map(layer=>layer.id)),['shot','blur','join']);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',blur:1.5,speed:0.5,transition:'wipe-down'}).map(layer=>layer.id)),['shot','blur','speed','join']);
});

test('glow, shadow, and b-roll get rows and a straight cut still has no join',()=>{
  assert.deepEqual(plain(glowBar({start:0,end:2,glow:true,glow_amount:0.8,effect_at:0.25,effect_end:0.5})),{start:0.5,end:1});
  assert.deepEqual(plain(glowBar({start:0,end:2,glow:true,effect_at:0})),{start:0,end:2});
  assert.deepEqual(plain(glowBar({start:0,end:2,glow_amount:0.2,effect_at:0.99})),{start:1.96,end:2});
  assert.equal(glowBar({start:0,end:2,glow:false,glow_amount:0.19}),null);
  assert.equal(glowBar({start:0,end:2}),null);
  assert.deepEqual(plain(shadowBar({start:0,end:2,shadow:true,shade:0.8,effect_at:0.25,effect_end:0.5})),{start:0.5,end:1});
  assert.deepEqual(plain(shadowBar({start:0,end:4,shadow:true,effect_at:0.1})),{start:0,end:4});
  assert.deepEqual(plain(shadowBar({start:0,end:4,shade:0.2,effect_at:0})),{start:0,end:4});
  assert.equal(shadowBar({start:0,end:2,shadow:false,shade:0}),null);
  assert.equal(shadowBar({start:0,end:2}),null);
  assert.deepEqual(plain(brollBar({start:10,end:14,external_broll:{start:1,end:3}})),{start:1,end:3});
  assert.deepEqual(plain(brollBar({start:0,end:4,cutaway:{start:0.5,end:2}})),{start:0.5,end:2});
  assert.deepEqual(plain(brollBar({start:0,end:4,external_broll:{start:1,end:2},cutaway:{start:0,end:4}})),{start:1,end:2});
  assert.equal(brollBar({start:0,end:4}),null);
  assert.equal(brollBar({start:0,end:4,external_broll:null,cutaway:null}),null);
  assert.equal(brollBar({start:0,end:4,cutaway:{start:5,end:9}}),null);
  assert.deepEqual(plain(joinBars({start:0,end:4})),[]);
  assert.deepEqual(plain(joinBars({start:0,end:4,transition:'cut'})),[]);
  const full=clipLayers({start:0,end:4,text:'Hi',blur:1.5,glow:true,shadow:true,shade:0.5,speed:0.5,transition:'wipe-down',external_broll:{start:1,end:2},effect_at:0,effect_end:1,card:{start:0,end:4},progress:0.5,progress_at:0,progress_end:1});
  assert.deepEqual(plain(full.map(layer=>layer.id)),['shot','blur','glow','shadow','speed','join','broll','callout','card','progress']);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',transition:'cut',glow:false,shadow:false}).map(layer=>layer.id)),['shot']);
  assert.ok(!clipLayers({start:0,end:4,text:'',transition:'fade',glow:true}).some(layer=>layer.id==='join'&&layer.windows.length!==2));
  assert.equal(clipLayers({start:0,end:4,text:'',transition:'cut'}).some(layer=>layer.id==='join'),false);
});

test('a constant slow speed gets its own row and speed 1 does not',()=>{
  assert.deepEqual(plain(speedBar({start:0,end:4,speed:0.75,speed_end:null})),{start:0,end:4});
  assert.deepEqual(plain(speedBar({start:0,end:4,speed:0.75})),{start:0,end:4});
  assert.equal(speedText({start:0,end:4,speed:0.75}),'0.75×');
  assert.equal(speedBar({start:0,end:4,speed:1,speed_end:null}),null);
  assert.equal(speedBar({start:0,end:4,speed:1}),null);
  assert.equal(speedBar({start:0,end:4,text:'slow motion'}),null);
  assert.equal(clipLayers({start:0,end:4,text:'slow motion'}).some(layer=>layer.id==='speed'),false);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'slow motion',speed:1}).map(layer=>layer.id)),['shot','callout']);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',speed:0.75}).map(layer=>layer.id)),['shot','speed']);
  assert.deepEqual(plain(speedBar({start:0,end:4,speed:1,speed_end:1.45})),{start:0,end:4});
  assert.equal(speedText({start:0,end:4,speed:1,speed_end:1.45}),'1×–1.45×');
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',speed:1,speed_end:1.45}).map(layer=>layer.id)),['shot','speed']);
  assert.equal(speedText({start:0,end:4,speed:0.75,speed_end:0.75}),'0.75×');
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',speed:0.75,speed_end:0.75}).map(layer=>layer.id)),['shot','speed']);
});

test('a cut has no join row and picture layers appear only when the clip has them',()=>{
  assert.equal(clipLayers({start:0,end:4,text:'',transition:'cut'}).some(layer=>layer.id==='join'),false);
  const blur=blurBar({start:0,end:5,blur:2,effect_end:0.6});
  assert.equal(blur.end,0.6*5);
  assert.ok(blur.end<5);
  assert.equal(glowBar({start:0,end:5,glow:true,effect_end:0.6}).end,0.6*5);
  assert.equal(shadowBar({start:0,end:5,shadow:true,effect_end:0.6}).end,0.6*5);
  assert.equal(blurBar({start:0,end:5,blur:2}).end,5);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',transition:'cut',cutout:false,mask:false,split:false,picture_insert:null,art:''}).map(layer=>layer.id)),['shot']);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',cutout:true}).map(layer=>layer.id)),['shot','cutout']);
  assert.equal(clipLayers({start:0,end:4,text:'',cutout:false}).some(layer=>layer.id==='cutout'),false);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',mask:true}).find(layer=>layer.id==='mask').windows),[{start:0,end:4}]);
  assert.equal(clipLayers({start:0,end:4,text:'',mask:false}).some(layer=>layer.id==='mask'),false);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',split:true}).map(layer=>layer.id)),['shot','split']);
  assert.equal(clipLayers({start:0,end:4,text:'',split:false}).some(layer=>layer.id==='split'),false);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',picture_insert:{start:0.4,end:1.2,at:2}}).find(layer=>layer.id==='reference').windows),[{start:0.4,end:1.2}]);
  assert.equal(clipLayers({start:0,end:4,text:'',picture_insert:null}).some(layer=>layer.id==='reference'),false);
  assert.equal(clipLayers({start:0,end:4,text:'',picture_insert:{start:5,end:9}}).some(layer=>layer.id==='reference'),false);
  assert.deepEqual(plain(clipLayers({start:0,end:4,text:'',art:'style-art-2.png'}).find(layer=>layer.id==='art').windows),[{start:0,end:4}]);
  assert.equal(clipLayers({start:0,end:4,text:'',art:''}).some(layer=>layer.id==='art'),false);
  assert.equal(clipLayers({start:0,end:4,text:'',art:'still.png'}).some(layer=>layer.id==='art'),false);
  const ordered=clipLayers({start:0,end:4,text:'Hi',blur:1.5,glow:true,shadow:true,shade:0.5,speed:0.5,transition:'wipe-down',cutout:true,mask:true,split:true,picture_insert:{start:0.2,end:1},art:'style-art-0.png',external_broll:{start:1,end:2},effect_at:0,effect_end:1,card:{start:0,end:4},progress:0.5,progress_at:0,progress_end:1});
  assert.deepEqual(plain(ordered.map(layer=>layer.id)),['shot','blur','glow','shadow','speed','join','cutout','mask','split','reference','art','broll','callout','card','progress']);
  assert.equal(clipLayers({start:0,end:4,text:'',transition:'cut',cutout:true,mask:true,split:true,picture_insert:{start:0.2,end:1},art:'style-art-0.png'}).some(layer=>layer.id==='join'),false);
});
