import type {Caption} from '@remotion/captions';
import {useCurrentFrame} from 'remotion';
export const Captions=({captions}:{captions:Caption[]})=>{const f=useCurrentFrame();const caption=captions.find(c=>c.startMs<=f/30*1000&&c.endMs>f/30*1000);return caption?<div style={{position:'absolute',left:120,right:120,bottom:90,textAlign:'center',fontSize:34,lineHeight:1.4,color:'#183d32',fontWeight:500}}>{caption.text}</div>:null};
