import React from '../../../frontend/node_modules/react/index.js';
import {createRoot} from '../../../frontend/node_modules/react-dom/client.js';
import {DirectorProject} from '../../../frontend/src/Studio';
import '../../../frontend/src/style.css';
import '../../../frontend/src/apple-design.css';
const t={en:'Trim opening',zh:'修剪开场'};
const state={revision:1,context:{creator:{topic:'travel',audience:'',tone:'',rules:''},references:[],platforms:[]},dna:[],decisions:[{id:'trim',approved:true,locked:false,start:0,end:1.5}],plan:{summary:t,transfers:[],recommendations:[{id:'trim',start:0,end:1.5,title:t,improvement:t,evidence:t,action:'trim'}]}};
const p:any={id:'moment-qa',title:'Moment preview',status:'complete',stage:'complete',progress:100,cost:0,budget:5,metadata:{preview_ready:true,duration:6,width:320,height:568},result:{metadata:{size:1},applied:[],plan_revision:1}};
window.fetch=async(url:any)=>({ok:true,json:async()=>String(url).endsWith('/moment-qa')?state:[]}) as any;
createRoot(document.getElementById('root')!).render(<DirectorProject p={p} lang="en" onBack={()=>{}} onRefresh={async()=>{}}/>);
const wait=(ms:number)=>new Promise(r=>setTimeout(r,ms));
const button=(s:string)=>[...document.querySelectorAll('button')].find(b=>b.textContent===s) as HTMLButtonElement;
async function ready(){for(let i=0;i<100;i++){const v=document.querySelector('video')!;if(v?.readyState>=1)return v;await wait(50)}throw Error('metadata timeout')}
(async()=>{await wait(300);(document.querySelector('.cleanup-controls') as HTMLDetailsElement).open=true;let v=await ready();const result:any={defaultMaster:v.src.endsWith('/result')};button('View moment').click();await wait(150);v=await ready();await wait(150);result.zeroStartsPlayback=!v.paused&&v.currentTime<1.5;button('View moment').click();await wait(1900);result.endPauses=v.paused&&v.currentTime>=1.5&&v.currentTime<1.9;
button('Master preview').click();await wait(100);await ready();button('View moment').click();await wait(100);v=await ready();await wait(100);result.switchToSource=v.src.endsWith('/source')&&!v.paused;v.pause();
const nativePlay=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=()=>Promise.reject(new Error('blocked'));button('View moment').click();await wait(100);result.blockedPlaybackExplained=document.body.textContent?.includes('Playback did not start. Press Play');HTMLMediaElement.prototype.play=nativePlay;
const el=document.createElement('pre');el.id='qa-results';el.textContent=JSON.stringify(result);document.body.appendChild(el);document.body.dataset.result=Object.values(result).every(Boolean)?'passed':'failed';})().catch(e=>{document.body.dataset.result='failed';document.body.append(String(e))});
