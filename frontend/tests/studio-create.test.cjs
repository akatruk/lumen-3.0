const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const code=ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../src/studioCreate.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const loaded={};
vm.runInNewContext(code,{exports:loaded});
const {createPrompt, projectTitleFromFile}=loaded;

const speechCode=ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../src/sourceSpeech.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const speechLoaded={};
vm.runInNewContext(speechCode,{exports:speechLoaded});
const {sourceSpeechLocale, audioMode}=speechLoaded;

test('Chinese speech stays original audio when captions are Chinese',()=>{
  const gloss=[{original:'Many people think foreign companies only change the language', en:'Many people think foreign companies only change the language', zh:'很多人以为外资公司只是换了一种语言'}];
  assert.equal(sourceSpeechLocale({lines:gloss}),'zh-CN');
  assert.equal(audioMode('zh-CN','zh-CN'),'original');
  assert.equal(audioMode('zh-CN','en-US'),'dub');
  assert.equal(sourceSpeechLocale({sourceLanguage:'zh-CN', lines:[{original:'Many people think'}]}),'zh-CN');
  assert.equal(sourceSpeechLocale({lines:[{en:'Ordinary Thai companies usually need at least three shareholders'}]}),null);
  assert.equal(audioMode(null,'zh-CN'),'original');
});

test('an uploaded reference file is enough to continue without a Douyin result',()=>{
  assert.equal(createPrompt(true,0,true),'ready');
  assert.equal(createPrompt(true,1,false),'ready');
  assert.equal(createPrompt(true,0,false),'ready');
  assert.equal(createPrompt(false,0,true),'video');
  assert.equal(createPrompt(false,0,false),'both');
  assert.equal(createPrompt(false,2,false),'video');
});

test('the project name comes from the file and keeps Chinese and Russian letters',()=>{
  assert.equal(projectTitleFromFile('咨询视频.mp4'),'咨询视频');
  assert.equal(projectTitleFromFile('Обзор квартиры.mov'),'Обзор квартиры');
  assert.equal(projectTitleFromFile('a'.repeat(140)+'.mp4').length,120);
  assert.equal(projectTitleFromFile('.mp4'),'Untitled video');
});
