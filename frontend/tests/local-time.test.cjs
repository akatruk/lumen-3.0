const {test}=require('node:test');
const assert=require('node:assert/strict');
const ts=require('typescript');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const code=ts.transpileModule(fs.readFileSync(path.resolve(__dirname,'../src/localTime.ts'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const loaded={};
vm.runInNewContext(code,{exports:loaded});
const {localDateTimeValue,localDateTimeToUnix}=loaded;

test('a datetime-local value is local wall time and round-trips',()=>{
  const when=new Date(Date.now()-3600_000);
  const value=localDateTimeValue(when);
  const pad=n=>String(n).padStart(2,'0');
  assert.equal(value,`${when.getFullYear()}-${pad(when.getMonth()+1)}-${pad(when.getDate())}T${pad(when.getHours())}:${pad(when.getMinutes())}`);
  const unix=localDateTimeToUnix(value);
  assert.ok(Math.abs(unix-when.getTime()/1000)<60);
  assert.ok(unix<=Date.now()/1000+60);
  const utcSlice=when.toISOString().slice(0,16);
  if(when.getTimezoneOffset()!==0){
    assert.notEqual(value,utcSlice);
    const shifted=localDateTimeToUnix(utcSlice);
    assert.ok(Math.abs((shifted-when.getTime()/1000)-when.getTimezoneOffset()*60)<90);
  }
});

test('a clock string that is not a datetime is rejected',()=>{
  assert.ok(Number.isNaN(localDateTimeToUnix('')));
  assert.ok(Number.isNaN(localDateTimeToUnix('2026-09-28')));
});
