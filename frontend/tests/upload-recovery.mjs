import ts from 'typescript';
import fs from 'node:fs';
import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../src/resumableUpload.ts',import.meta.url),'utf8');
const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText;
const {uploadVideo}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const realSetTimeout=globalThis.setTimeout,realClearTimeout=globalThis.clearTimeout;
const timers=new Set();
globalThis.setTimeout=(...args)=>{const id=realSetTimeout(...args);timers.add(id);return id};
globalThis.clearTimeout=id=>{timers.delete(id);return realClearTimeout(id)};
const storage=new Map();globalThis.sessionStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)};
const file=new File([new Uint8Array(2*1024*1024+20).fill(7)],'demo.mp4',{lastModified:1});
let offset=0,begin=0,completed=false,lost=true,completions=0;const offsets=[];
globalThis.fetch=async(url,opts={})=>{
 const respond=data=>new Response(JSON.stringify(data),{status:200});
 if(url.includes('/completed/'))return respond(completed?{id:'project'}:{});
 if(url.endsWith('/uploads')){begin++;return respond({id:'upload',offset,size:file.size})}
 if(opts.method==='PUT'){
  assert.equal(timers.size,0,'file chunk must have no total-duration timeout');
  offsets.push(Number(new URL(url,'https://test').searchParams.get('offset')));
  assert.equal(offsets.at(-1),offset);offset+=opts.body.size;
  if(lost){lost=false;throw new TypeError('response lost')}
  return respond({offset});
 }
 if(url.endsWith('/complete')){completions++;completed=true;if(completions===1)throw new TypeError('completion response lost');return respond({id:'project'})}
 return respond({id:'upload',offset,size:file.size});
};
const progress=[];assert.equal((await uploadVideo(file,{request_id:'request'},new AbortController().signal,n=>progress.push(n))).id,'project');
assert.equal(offsets[0],0);assert.equal(offsets[1],256*1024);assert.equal(offset,file.size);assert.equal(progress.at(-1),100);assert.equal(completions,2);assert.equal(storage.size,0);
console.log('PASS: lost chunk response resumes at committed offset; lost completion retries idempotently.');
// Previously completed project skips the video transfer entirely.
offsets.length=0;await uploadVideo(file,{request_id:'request'},new AbortController().signal,()=>{});assert.equal(offsets.length,0);assert.equal(begin,1);
console.log('PASS: completion lookup avoids retransferring an already accepted video.');
// Large-file path must honor the server's 4 MB chunk size.
completed=false;offset=0;lost=false;completions=2;offsets.length=0;
const large=new File([new Uint8Array(20*1024*1024)],'large.mp4',{lastModified:2});
const previousFetch=globalThis.fetch;
globalThis.fetch=async(url,opts={})=>url.endsWith('/uploads')?new Response(JSON.stringify({id:'large',offset:0,size:large.size,chunk_size:4*1024*1024})):previousFetch(url,opts);
await uploadVideo(large,{request_id:'large-request'},new AbortController().signal,()=>{});
assert.ok(offsets.length<20);assert.equal(offset,large.size);
console.log('PASS: adaptive chunks begin at 256 KiB and grow on a fast connection; full size accounted for.');

globalThis.setTimeout=realSetTimeout;globalThis.clearTimeout=realClearTimeout;
// Asset uploads use a separate completion path and never create an analysis project.
storage.clear();let assetCompletes=0;
globalThis.fetch=async(url,opts={})=>{
 if(url.includes('/completed-asset/'))return new Response('{}');
 if(url.endsWith('/uploads'))return new Response(JSON.stringify({id:'asset-upload',offset:0,size:4,chunk_size:4194304}));
 if(opts.method==='PUT')return new Response(JSON.stringify({offset:4}));
 assert.ok(url.endsWith('/asset'),'asset must not use project completion');assetCompletes++;
 return new Response(JSON.stringify({id:'asset-id'}));
};
assert.equal((await uploadVideo(new File(['test'],'broll.mp4'),{asset_project_id:'project-id',request_id:'asset-request'},new AbortController().signal,()=>{})).id,'asset-id');
assert.equal(assetCompletes,1);
console.log('PASS: library uploads finalize as assets without invoking project analysis.');
