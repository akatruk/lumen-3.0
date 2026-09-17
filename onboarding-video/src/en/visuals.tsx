import React from 'react';
import {AbsoluteFill, Interactive, interpolate, useCurrentFrame, Easing} from 'remotion';
export const Ink='#183f35';
export const Motion:React.FC<{children:React.ReactNode}>=({children})=>{
 const frame=useCurrentFrame();
 return <Interactive.Div name="Interface demo" style={{position:'absolute',left:845,top:205,width:955,height:660,opacity:interpolate(frame,[0,10],[0,1],{extrapolateRight:'clamp'}),translate:interpolate(frame,[0,20],['55px 16px','0px 0px'],{extrapolateRight:'clamp',easing:Easing.bezier(.16,1,.3,1)})}}>{children}</Interactive.Div>
};
export const Headline:React.FC<{number:string;title:React.ReactNode;description:string}>=({number,title,description})=>{
 const frame=useCurrentFrame();
 return <Interactive.Div name="Step title" style={{position:'absolute',left:120,top:270,width:660,opacity:interpolate(frame,[0,8],[0,1],{extrapolateRight:'clamp'}),translate:interpolate(frame,[0,16],['0px 24px','0px 0px'],{extrapolateRight:'clamp',easing:Easing.bezier(.16,1,.3,1)})}}>
 <div style={{fontSize:28,fontWeight:650,letterSpacing:3,color:'#4f7e69',marginBottom:38}}>QUICK START / {number}</div>
 <div style={{fontSize:80,fontWeight:650,lineHeight:1.25,letterSpacing:-4}}>{title}</div>
 <div style={{fontSize:31,color:'#687970',marginTop:35,lineHeight:1.6}}>{description}</div>
 </Interactive.Div>
};
export const Window:React.FC<{children:React.ReactNode;title:string}>=({children,title})=><div style={{height:'100%',background:'#fff',borderRadius:30,border:'1px solid #dde5db',boxShadow:'0 24px 80px #183f3514',overflow:'hidden'}}>
 <div style={{height:78,borderBottom:'1px solid #e8ece6',display:'flex',alignItems:'center',padding:'0 35px',gap:10}}><span style={{width:12,height:12,borderRadius:9,background:'#abc6a7'}}/><span style={{width:12,height:12,borderRadius:9,background:'#dce4d5'}}/><span style={{width:12,height:12,borderRadius:9,background:'#e9ede3'}}/><span style={{marginLeft:26,fontSize:27,fontWeight:600}}>{title}</span><span style={{marginLeft:'auto',fontSize:23,color:'#7a887d'}}>lumen.</span></div>
 {children}</div>;
export const Button:React.FC<{children:React.ReactNode;light?:boolean}>=({children,light})=><div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:20,borderRadius:14,padding:'19px 27px',background:light?'#e8f0e3':Ink,color:light?Ink:'#fff',fontSize:30,fontWeight:600}}>{children}</div>;
export const Check:React.FC=()=> <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="m5 12 4 4L19 6" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
export const Product:React.FC<{small?:boolean}>=({small})=>{
 const frame=useCurrentFrame();
 return <div style={{position:'relative',height:'100%',overflow:'hidden',background:'linear-gradient(140deg,#e8eee0,#bfd0b3)',borderRadius:18,display:'flex',alignItems:'center',justifyContent:'center'}}>
 <div style={{position:'absolute',width:310,height:310,borderRadius:'50%',background:'#f6f6e966',left:-60,top:-110}}/>
 <div style={{position:'absolute',width:220,height:80,borderRadius:'50%',background:'#263d2420',bottom:'12%',filter:'blur(17px)'}}/>
 <div style={{position:'relative',height:small?155:230,width:small?85:135,borderRadius:'20px 20px 25px 25px',background:'linear-gradient(95deg,#53674a,#a3b08b 45%,#617550)',boxShadow:'inset 6px 0 10px #ffffff25,14px 12px 25px #283c2625',rotate:interpolate(frame,[0,74],['-5deg','3deg'])}}>
 <div style={{position:'absolute',height:small?25:38,width:'70%',left:'15%',top:small?-20:-30,borderRadius:'8px 8px 1px 1px',background:'#234235'}}/>
 <div style={{position:'absolute',left:'10%',top:'31%',height:'46%',width:'80%',background:'#f0eedf',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',borderRadius:2,color:'#335340'}}><span style={{fontFamily:'Georgia',fontSize:small?22:36}}>lumen</span><span style={{fontSize:small?10:15,marginTop:8,letterSpacing:2}}>NATURAL</span></div>
 </div></div>
};
export const Base:React.FC<{children:React.ReactNode}>=({children})=>{
 const frame=useCurrentFrame();const step=frame<60?0:frame<141?1:frame<210?2:3;
 return <AbsoluteFill style={{background:'#f4f5ed',color:Ink,fontFamily:'Arial, sans-serif'}}>
 <div style={{position:'absolute',width:800,height:800,borderRadius:'50%',background:'radial-gradient(circle,#dce8ce88,transparent 70%)',right:-240,top:-300}}/>
 <div style={{position:'absolute',left:120,right:120,top:75,display:'flex',alignItems:'center',justifyContent:'space-between'}}><span style={{fontFamily:'Arial',fontSize:57,fontWeight:700,letterSpacing:-3}}>◒ lumen.</span><span style={{fontSize:26,padding:'13px 25px',border:'1px solid #cad5c3',borderRadius:99}}>10-second guide · English</span></div>
 {children}
 <div style={{position:'absolute',left:120,right:120,bottom:73,display:'flex',gap:22}}>{['Upload video','AI analysis','Choose changes','Preview & download'].map((label,i)=><div key={label} style={{flex:1}}><div style={{height:4,background:'#dce4d5',borderRadius:3,overflow:'hidden',marginBottom:20}}><div style={{height:4,width:`${Math.max(0,Math.min(1,(frame-[0,60,141,210][i])/[60,81,69,90][i]))*100}%`,background:Ink}}/></div><div style={{fontSize:27,color:i===step?Ink:'#899385',fontWeight:i===step?600:400}}><span style={{fontSize:21,marginRight:18}}>0{i+1}</span>{label}</div></div>)}</div>
 <div style={{position:'absolute',right:120,bottom:27,fontSize:17,color:'#8a9487'}}>Illustrative interface · Processing time varies</div>
 </AbsoluteFill>
};
