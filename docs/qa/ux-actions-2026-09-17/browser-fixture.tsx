import React from '../../../frontend/node_modules/react/index.js';
import {createRoot} from '../../../frontend/node_modules/react-dom/client.js';
import {CreativePlan} from '../../../frontend/src/CreativePlan';
import {ManualEditor} from '../../../frontend/src/ManualEditor';
import '../../../frontend/src/style.css';
import '../../../frontend/src/studio.css';
import '../../../frontend/src/apple-design.css';
const text={en:'Review the opening and tighten the pacing.',zh:'审核开场并调整节奏。'};
const edit={clips:[{id:'clip',start:0,end:5,zoom:1,zoom_end:1,x:.5,y:.5,text:'',approved:false,locked:false,transition:'cut',shot_type:'presenter',card:null,cutaway:null,sound_effects:[]}],captions:[],subtitles:false,normalize:false,font_size:'medium',position:'bottom',color:'white'};
window.fetch=async(url:any,options:any)=>({ok:true,json:async()=>String(url).endsWith('/manual')?{revision:1,saved:true,edit}:String(url).includes('creative-plans')?[{id:'test',revision:1,status:'ready',result:{reason:text,notes:[],edit,decisions:[]}}]:[]}) as any;
function App(){const [applied,setApplied]=React.useState(false);return <div className="director-project" style={{maxWidth:1100,margin:'auto',padding:16}}><header className="topbar">Lumen · UX review</header><section className="director-inspector"><div className="director-tabs"><button>Decisions</button><button>Director Timeline</button></div><div id="ready"><CreativePlan pid="qa" revision={1} lang="en" disabled={false} onApplied={async()=>setApplied(true)}/></div><div id="blocked"><CreativePlan pid="qa" revision={1} lang="zh" disabled disabledReason="Save your plan changes to continue." onApplied={async()=>{}}/></div><details className="cleanup-controls"><summary>Additional cleanup controls</summary>Optional settings</details><div id="manual"><ManualEditor pid="ux-review" lang="en" outputLanguage="en" duration={5} ratio={1} disabled={false} onSaved={async()=>{}}/></div>{applied&&<p id="applied">Applied</p>}</section></div>}
createRoot(document.getElementById('root')!).render(<App/>);
const results:any={};
setTimeout(()=>{
 const ready=document.querySelector('#ready .creative-plan-actions button') as HTMLButtonElement;
 results.visiblePrimary=!!ready&&getComputedStyle(ready).backgroundColor==='rgb(0, 102, 204)'&&ready.getBoundingClientRect().height>=44;
 results.duplicatedAction=document.querySelectorAll('#ready .creative-plan-actions .primary').length===2;
 results.disabledExplanation=(document.querySelector('#blocked .creative-plan-actions button') as HTMLButtonElement)?.disabled&&document.querySelector('#blocked')?.textContent?.includes('Save your plan');
 const render=[...document.querySelectorAll('#manual button')].find(x=>x.textContent==='Render manual cut') as HTMLButtonElement;
 results.unapprovedRenderBlocked=render?.disabled&&document.querySelector('#manual')?.textContent?.includes('Shots awaiting approval: 1');
 const lib=document.querySelector('.media-library') as HTMLDetailsElement;lib.open=true;
 results.uploadInputVisible=getComputedStyle(lib.querySelector('input[type=file]')!).display!=='none';
 results.uploadReason=lib.textContent?.includes('Choose a file to upload.');
 results.noPageOverflow=document.documentElement.scrollWidth<=window.innerWidth;
 results.tabOffset=getComputedStyle(document.querySelector('.director-inspector > .director-tabs')!).top==='68px';
 ready?.click();
},500);
setTimeout(()=>{results.applyWorks=!!document.getElementById('applied');const p=document.createElement('pre');p.id='qa-results';p.textContent=JSON.stringify(results);document.body.appendChild(p);document.body.dataset.result=Object.values(results).every(Boolean)?'passed':'failed'},1100);
