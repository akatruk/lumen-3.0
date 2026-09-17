import {useCurrentFrame,interpolate} from 'remotion';
import {Headline,Motion,Window,Check} from '../visuals';
export const Recommend=()=>{const f=useCurrentFrame();return <>
 <Headline number="03" title={<>展开建议<br/>勾选优化</>} description="看清理由，再决定如何改。"/>
 <Motion><Window title="改进建议"><div style={{padding:32}}>
 <div style={{background:'#edf3e5',border:'2px solid #a8c08e',borderRadius:16,padding:'22px 26px'}}><div style={{display:'flex',alignItems:'center',gap:20,fontSize:32,fontWeight:600}}><span style={{width:32,height:32,background:'#35573c',color:'#fff',borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center'}}><Check/></span>把亮点移到开场<span style={{marginLeft:'auto',rotate:f>18?'180deg':'0deg'}}>⌄</span></div><div style={{height:interpolate(f,[16,30],[0,112],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}),overflow:'hidden'}}><div style={{borderTop:'1px solid #cddbc2',marginTop:19,paddingTop:17,fontSize:26,lineHeight:1.7,color:'#637556'}}>00:04 – 00:06 · 优先呈现产品主体<br/>让观众更快看到核心内容。</div></div></div>
 {['精简停顿，改善节奏','添加字幕，清晰传达'].map((label,i)=><div key={label} style={{marginTop:20,border:'1px solid #dde4d7',borderRadius:15,padding:'22px 26px',fontSize:29,display:'flex',alignItems:'center',gap:20}}><span style={{width:32,height:32,borderRadius:6,border:'1px solid #b7c8ab',background:f>38+i*8?'#35573c':'white',color:'white',display:'flex',alignItems:'center',justifyContent:'center'}}>{f>38+i*8&&<Check/>}</span>{label}<span style={{marginLeft:'auto',color:'#829176'}}>⌄</span></div>)}
 </div></Window></Motion></>};
