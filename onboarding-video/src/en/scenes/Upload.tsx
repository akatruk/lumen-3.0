import {useCurrentFrame,interpolate} from 'remotion';
import {Headline,Motion,Window,Button,Check} from '../visuals';
export const Upload=()=>{const f=useCurrentFrame();return <>
 <Headline number="01" title={<>Upload video<br/>Set your goal</>} description="Sign in and create your first project."/>
 <Motion><Window title="New project"><div style={{padding:36}}>
 <div style={{height:218,border:'2px dashed #aec4a3',background:'#f4f7ef',borderRadius:18,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:15}}><div style={{fontSize:54,lineHeight:1}}>↑</div><div style={{fontSize:34,fontWeight:600}}>{f<35?'Upload a video':'Video added'}</div><div style={{fontSize:24,color:'#778371'}}>{f<35?'MP4 · MOV · WEBM':'product-film.mp4'}</div></div>
 <div style={{fontSize:25,marginTop:26,marginBottom:12}}>What should this video achieve?</div><div style={{height:69,border:'1px solid #dbe2d5',borderRadius:12,padding:'15px 21px',fontSize:27,color:'#58724f',boxSizing:'border-box'}}>Show the product. Strengthen the opening.</div>
 <div style={{marginTop:25,opacity:interpolate(f,[35,45],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}><Button><Check/>Start analysis →</Button></div>
 </div></Window></Motion></>};
