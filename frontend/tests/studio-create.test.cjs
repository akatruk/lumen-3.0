const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const code=ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../src/studioCreate.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const loaded={};
vm.runInNewContext(code,{exports:loaded});
const {createPrompt}=loaded;

test('an uploaded reference file is enough to continue without a Douyin result',()=>{
  assert.equal(createPrompt(true,0,true),'ready');
  assert.equal(createPrompt(true,1,false),'ready');
  assert.equal(createPrompt(true,0,false),'reference');
  assert.equal(createPrompt(false,0,true),'video');
  assert.equal(createPrompt(false,0,false),'both');
  assert.equal(createPrompt(false,2,false),'video');
});
