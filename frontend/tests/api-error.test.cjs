const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const code=ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../src/apiError.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const loaded={};
vm.runInNewContext(code,{exports:loaded});
const {apiErrorCode}=loaded;

test('a FastAPI validation list keeps invalid_date and invalid_url',()=>{
  assert.equal(apiErrorCode({detail:[{type:'value_error',msg:'Value error, invalid_date'}]}),'invalid_date');
  assert.equal(apiErrorCode({detail:[{msg:'Value error, invalid_url'}]}),'invalid_url');
  assert.equal(apiErrorCode({detail:'not_found'}),'not_found');
  assert.equal(apiErrorCode({detail:[{msg:'Field required'}]}),'request_failed');
  assert.equal(apiErrorCode({}),'request_failed');
});
