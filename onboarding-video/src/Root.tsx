import {GuideV5,newTiming} from './guide-v5/Guide';
import {Guide as UpdatedGuide,guideTiming} from './guide-v2/Guide';
import {Composition,Sequence,staticFile} from 'remotion';
import {Audio} from '@remotion/media';
import {TransitionSeries} from '@remotion/transitions';
import {Base} from './visuals';
import {Base as EnglishBase} from './en/visuals';
import {Upload as EnglishUpload} from './en/scenes/Upload';
import {Analyze as EnglishAnalyze} from './en/scenes/Analyze';
import {Recommend as EnglishRecommend} from './en/scenes/Recommend';
import {Export as EnglishExport} from './en/scenes/Export';
import {Upload} from './scenes/Upload';
import {Analyze} from './scenes/Analyze';
import {Recommend} from './scenes/Recommend';
import {Export} from './scenes/Export';
const Guide=()=> <Base><TransitionSeries>
 <TransitionSeries.Sequence durationInFrames={75} name="上传视频"><Upload/></TransitionSeries.Sequence>
 <TransitionSeries.Sequence durationInFrames={75} name="智能分析"><Analyze/></TransitionSeries.Sequence>
 <TransitionSeries.Sequence durationInFrames={75} name="选择建议"><Recommend/></TransitionSeries.Sequence>
 <TransitionSeries.Sequence durationInFrames={75} name="预览下载"><Export/></TransitionSeries.Sequence>
 </TransitionSeries>
 <Sequence from={0} durationInFrames={300}><Audio src={staticFile('narration-zh.wav')}/></Sequence>
 </Base>;
const EnglishGuide=()=> <EnglishBase><TransitionSeries>
 <TransitionSeries.Sequence durationInFrames={60}><EnglishUpload/></TransitionSeries.Sequence>
 <TransitionSeries.Sequence durationInFrames={81}><EnglishAnalyze/></TransitionSeries.Sequence>
 <TransitionSeries.Sequence durationInFrames={69}><EnglishRecommend/></TransitionSeries.Sequence>
 <TransitionSeries.Sequence durationInFrames={90}><EnglishExport/></TransitionSeries.Sequence>
 </TransitionSeries><Sequence from={0} durationInFrames={300}><Audio src={staticFile('narration-en.wav')}/></Sequence></EnglishBase>;
export const RemotionRoot=()=> <>{(["en","zh"] as const).flatMap(lang=>(["guide","walkthrough"] as const).map(mode=><Composition key={lang+mode} id={`LumenV5-${mode}-${lang}`} component={GuideV5} defaultProps={{lang,mode}} width={1920} height={1080} fps={30} durationInFrames={newTiming[lang][mode].frames}/>))}<Composition id="LumenGuideEnV4" component={UpdatedGuide} defaultProps={{lang:"en" as const,quick:true}} width={1920} height={1080} fps={30} durationInFrames={300}/><Composition id="LumenGuideZhV4" component={UpdatedGuide} defaultProps={{lang:"zh" as const,quick:true}} width={1920} height={1080} fps={30} durationInFrames={300}/><Composition id="LumenWalkthroughEnV4" component={UpdatedGuide} defaultProps={{lang:"en" as const,quick:false}} width={1920} height={1080} fps={30} durationInFrames={guideTiming.en.frames}/><Composition id="LumenWalkthroughZhV4" component={UpdatedGuide} defaultProps={{lang:"zh" as const,quick:false}} width={1920} height={1080} fps={30} durationInFrames={guideTiming.zh.frames}/><Composition id="LumenChineseGuide" component={Guide} width={1920} height={1080} fps={30} durationInFrames={300}/><Composition id="LumenEnglishGuide" component={EnglishGuide} width={1920} height={1080} fps={30} durationInFrames={300}/></>;
