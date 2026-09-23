import React from 'react';
import {AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';
import timing from './timing.json';

const ink = '#17231f';
const green = '#176c4f';
const muted = '#65736c';

function Scene({scene, lang, index, total}: {scene: any; lang: 'en' | 'zh'; index: number; total: number}) {
  const frame = useCurrentFrame();
  const progress = Math.min(1, frame / scene.frames);
  const active = Math.min(2, Math.floor(progress * 3));
  return (
    <AbsoluteFill style={{background: '#f4f6f2', color: ink, fontFamily: 'Arial, "PingFang SC", sans-serif', padding: '66px 100px'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <div style={{fontSize: 39, fontWeight: 750}}>lumen<span style={{color: green}}>.</span></div>
        <div style={{fontSize: 21, color: muted, letterSpacing: 2}}>{lang === 'en' ? 'STYLE MATCH' : '风格匹配'}　{String(index + 1).padStart(2, '0')} / {total}</div>
      </div>
      <div style={{display: 'grid', gridTemplateColumns: '0.9fr 1.1fr', gap: 70, alignItems: 'center', height: 760, opacity: interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'})}}>
        <div>
          <div style={{color: green, fontSize: 22, fontWeight: 650, marginBottom: 24}}>{lang === 'en' ? `STEP ${index + 1}` : `第 ${index + 1} 步`}</div>
          <h1 style={{fontSize: lang === 'en' ? 64 : 68, lineHeight: 1.12, letterSpacing: -1.5, margin: '0 0 36px', fontWeight: 650}}>{scene.title}</h1>
          {scene.lines.map((line: string, i: number) => (
            <div key={line} style={{fontSize: 30, lineHeight: 1.35, padding: '16px 20px', marginBottom: 12, borderRadius: 14, background: active === i ? '#e0eddf' : 'transparent', color: active === i ? ink : muted}}>
              <span style={{color: green, marginRight: 12}}>0{i + 1}</span>{line}
            </div>
          ))}
        </div>
        <div style={{border: '1px solid #dce3de', background: 'white', borderRadius: 24, padding: 36, minHeight: 460}}>
          <div style={{fontSize: 22, color: muted, marginBottom: 28}}>{lang === 'en' ? 'VIDEO STUDIO' : '视频工作室'}</div>
          {scene.lines.map((line: string, i: number) => (
            <div key={line} style={{border: '1px solid', borderColor: active === i ? green : '#dce3de', borderRadius: 16, padding: '18px 20px', marginBottom: 16, fontSize: 28, boxShadow: active === i ? '0 0 0 3px #bfe0c9' : 'none'}}>{line}</div>
          ))}
          <div style={{marginTop: 28, height: 8, background: '#dae6de', borderRadius: 8}}>
            <div style={{width: `${Math.round(progress * 100)}%`, height: '100%', background: green, borderRadius: 8}} />
          </div>
        </div>
      </div>
      <div style={{position: 'absolute', bottom: 28, left: 100, right: 100, display: 'flex', justifyContent: 'space-between', fontSize: 18, color: muted}}>
        <span>lumen-fix.universalgravity.org</span>
        <span>{lang === 'en' ? 'Illustrated guide' : '流程示意'}</span>
      </div>
    </AbsoluteFill>
  );
}

export function StyleGuide({lang}: {lang: 'en' | 'zh'}) {
  const frame = useCurrentFrame();
  const data = timing[lang];
  const caption = data.captions.find((item) => item.startMs <= (frame / 30) * 1000 && item.endMs > (frame / 30) * 1000);
  return (
    <AbsoluteFill>
      {data.scenes.map((scene, index) => (
        <Sequence key={scene.id} from={scene.fromFrame} durationInFrames={scene.frames}>
          <Scene scene={scene} lang={lang} index={index} total={data.scenes.length} />
          <Sequence from={6}>
            <Audio src={staticFile(scene.audio)} />
          </Sequence>
        </Sequence>
      ))}
      {caption && (
        <div style={{position: 'absolute', left: 140, right: 140, bottom: 78, textAlign: 'center', background: 'rgba(244,246,242,0.92)', borderRadius: 16, padding: '14px 22px', fontFamily: 'Arial, "PingFang SC", sans-serif', fontSize: 32, lineHeight: 1.35, color: ink}}>
          {caption.text}
        </div>
      )}
    </AbsoluteFill>
  );
}

export const styleTiming = timing;
