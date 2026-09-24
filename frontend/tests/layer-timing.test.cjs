const {test}=require('node:test');const assert=require('node:assert/strict');const ts=require('typescript');const fs=require('node:fs');const path=require('node:path');const vm=require('node:vm');
const file=path.resolve(__dirname,'../src/layerTiming.ts');
const code=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const exposed={};vm.runInNewContext(code,{exports:exposed});
const {calloutBars,cardBar,progressBar,clipLayers}=exposed;
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
