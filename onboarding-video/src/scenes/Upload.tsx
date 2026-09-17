import {useCurrentFrame,interpolate} from 'remotion';
import {Headline,Motion,Window,Button,Check} from '../visuals';
export const Upload=()=>{const f=useCurrentFrame();return <>
 <Headline number="01" title={<>上传视频<br/>填写目标</>} description="登录后，创建你的第一个项目。"/>
 <Motion><Window title="新建项目"><div style={{padding:36}}>
 <div style={{height:218,border:'2px dashed #aec4a3',background:'#f4f7ef',borderRadius:18,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:15}}><div style={{fontSize:54,lineHeight:1}}>↑</div><div style={{fontSize:34,fontWeight:600}}>{f<35?'点击上传视频':'视频已添加'}</div><div style={{fontSize:24,color:'#778371'}}>{f<35?'MP4 · MOV · WEBM':'产品短片.mp4'}</div></div>
 <div style={{fontSize:25,marginTop:26,marginBottom:12}}>这支视频希望实现什么？</div><div style={{height:69,border:'1px solid #dbe2d5',borderRadius:12,padding:'15px 21px',fontSize:27,color:'#58724f',boxSizing:'border-box'}}>突出产品亮点，增强开场吸引力</div>
 <div style={{marginTop:25,opacity:interpolate(f,[35,45],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}><Button><Check/>开始分析 →</Button></div>
 </div></Window></Motion></>};
