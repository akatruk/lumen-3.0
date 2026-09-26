import React from 'react';
import {AbsoluteFill, Sequence, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';
import timing from './timing.json';

const ink = '#17231f';
const green = '#176c4f';
const muted = '#65736c';
const line = '#dce3de';

function Field({label, value, on}: {label: string; value?: string; on?: boolean}) {
  return (
    <div style={{marginBottom: 16}}>
      <div style={{fontSize: 18, color: muted, marginBottom: 8}}>{label}</div>
      <div style={{border: '1px solid', borderColor: on ? green : line, borderRadius: 12, padding: '14px 16px', fontSize: 24, background: on ? '#f3faf6' : 'white', boxShadow: on ? '0 0 0 3px #bfe0c9' : 'none'}}>
        {value || ' '}
      </div>
    </div>
  );
}

function Button({children, primary, on}: {children: React.ReactNode; primary?: boolean; on?: boolean}) {
  return (
    <div style={{borderRadius: 12, padding: '14px 18px', fontSize: 24, textAlign: 'center', background: primary || on ? green : 'white', color: primary || on ? 'white' : ink, border: '1px solid', borderColor: primary || on ? green : line, boxShadow: on ? '0 0 0 3px #bfe0c9' : 'none'}}>
      {children}
    </div>
  );
}

function Panel({id, lang, active}: {id: string; lang: 'en' | 'zh'; active: number}) {
  const t = (en: string, zh: string) => (lang === 'en' ? en : zh);
  const card: React.CSSProperties = {border: '1px solid ' + line, background: 'white', borderRadius: 24, padding: 32, minHeight: 520};
  if (id === 'signin') {
    return (
      <div style={card}>
        <div style={{fontSize: 18, letterSpacing: 1.5, color: muted, marginBottom: 18}}>{t('LUMEN WORKSPACE', 'LUMEN WORKSPACE')}</div>
        <h2 style={{fontSize: 40, margin: '0 0 8px'}}>{t('Sign in', '登录')}</h2>
        <p style={{color: muted, fontSize: 20, marginTop: 0}}>{t('Interface language does not choose the video voice.', '界面语言不会选择成片的声音。')}</p>
        <Field label={t('Email address', '电子邮箱')} on={active === 0} />
        <Field label={t('Password', '密码')} value="••••••••••" on={active === 1} />
        <Button primary on={active === 2}>{t('Continue', '继续')}</Button>
        <div style={{marginTop: 18, fontSize: 18, color: muted}}>{t('Interface language', '界面语言')} · {lang === 'en' ? 'English' : '中文'}</div>
      </div>
    );
  }
  if (id === 'create') {
    return (
      <div style={card}>
        <div style={{fontSize: 18, color: muted, marginBottom: 10}}>{t('VIDEO STUDIO', '视频工作室')}</div>
        <h2 style={{fontSize: 34, margin: '0 0 18px', lineHeight: 1.2}}>{t('Learn the technique. Tell your story.', '借鉴创作方法，讲好自己的故事。')}</h2>
        <Field label={t('Reference video', '参考视频')} value={t('1–5 Douyin results, or this file', '1–5 条抖音结果，或这个文件')} on={active === 1} />
        <p style={{fontSize: 20, color: muted}}>{t('Reference pictures, speech, and music stay out of the file.', '参考的画面、语音和音乐不会进入成片。')}</p>
        <Button on={active === 2}>{t('Analyze & build my plan', '分析并创建剪辑计划')}</Button>
      </div>
    );
  }
  if (id === 'upload') {
    return (
      <div style={card}>
        <Field label={t('Choose your video to upload', '选择要上传的自有视频')} value={t('Vertical · 30 s–7 min · 250 MB', '竖屏 · 30 秒–7 分钟 · 250 MB')} on={active === 0} />
        <Field label={t('Project name', '项目名称')} value={t('Your title', '你的项目名称')} />
        <Field label={t('Script & intended message', '脚本与核心信息')} />
        <div style={{fontSize: 22, margin: '8px 0 16px'}}>{t('I own or have permission to edit this footage.', '我拥有或已获得此素材的编辑使用权。')}</div>
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16}}>
          <Field label={t('Caption language', '字幕语言')} value={lang === 'en' ? 'English' : '简体中文'} on={active === 1} />
          <Field label={t('Voice & style', '语气与风格')} value={t('calm, factual', '平静、客观')} on={active === 2} />
        </div>
      </div>
    );
  }
  if (id === 'picture') {
    return (
      <div style={card}>
        <div style={{fontSize: 20, color: muted, marginBottom: 18}}>{t('First picture still uses your footage sound.', '第一版画面仍使用你的素材声音。')}</div>
        <div style={{display: 'grid', gap: 14}}>
          <Button primary on={active === 0}>{t('Approve this cut', '批准这个成片')}</Button>
          <Button on={active === 1}>{t('Create video with these changes', '按这些更改创建视频')}</Button>
          <Button on={active === 2}>{t('Save and refresh summary', '保存并更新摘要')}</Button>
        </div>
        <p style={{fontSize: 20, color: muted}}>{t('Review edits and create a version opens the summary. It does not render.', '审核更改并创建版本只打开摘要，不会渲染。')}</p>
      </div>
    );
  }
  if (id === 'voice') {
    return (
      <div style={card}>
        <div style={{fontSize: 18, color: muted}}>{t('Edit · Voiceover and language', '剪辑 · 配音与语言')}</div>
        <h2 style={{fontSize: 32, margin: '8px 0 16px'}}>{t('Create a translated voiceover', '创建翻译配音')}</h2>
        <Field label={t('Voiceover language', '配音语言')} value={lang === 'en' ? 'English' : '中文'} on={active === 0} />
        <Field label={t('AI voice', 'AI 声音')} value={lang === 'en' ? 'Female — warm · en-female' : '女声 — 亲切 · zh-female'} on={active === 1} />
        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
          <Button>{t('Preview voice', '试听声音')}</Button>
          <Button primary on={active === 2}>{t('Create dubbed version', '创建配音版本')}</Button>
        </div>
        <p style={{fontSize: 20, color: green}}>{t('Used in final video · en-female', '已用于最终视频 · zh-female')}</p>
      </div>
    );
  }
  if (id === 'music') {
    return (
      <div style={card}>
        <div style={{fontSize: 18, color: muted}}>{t('Audio', '声音')}</div>
        <h2 style={{fontSize: 32, margin: '8px 0 16px'}}>{t('Background music', '背景音乐')}</h2>
        <Field label={t('Track', '曲目')} value={t('No added music', '不添加音乐')} on={active === 1} />
        <p style={{fontSize: 20, color: muted}}>{t('A chosen track is mixed under the voice. It does not replace en-female.', '选中的曲目混在声音下面，不会替换 zh-female。')}</p>
        <Button primary on={active === 2}>{t('Add music to final video', '将音乐加入成片')}</Button>
      </div>
    );
  }
  if (id === 'edit') {
    const tabs = lang === 'en' ? ['Edit', 'Subtitles', 'Audio', 'Effects', 'Materials', 'Review'] : ['剪辑', '字幕', '声音', '效果', '素材', '审核'];
    return (
      <div style={card}>
        <div style={{display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 22}}>
          {tabs.map((tab, i) => (
            <span key={tab} style={{padding: '10px 14px', borderRadius: 999, background: i === active ? green : '#eef3ef', color: i === active ? 'white' : ink, fontSize: 20}}>{tab}</span>
          ))}
        </div>
        <p style={{fontSize: 26, lineHeight: 1.4}}>{t('Saving the edit does not render. Approve this cut again carries en-female into the new picture.', '保存剪辑不会渲染。再次批准这个成片时，zh-female 会带到新画面里。')}</p>
        <Button primary>{t('Approve this cut', '批准这个成片')}</Button>
      </div>
    );
  }
  return (
    <div style={card}>
      <div style={{height: 220, borderRadius: 16, background: ink, color: 'white', display: 'flex', alignItems: 'flex-end', padding: 20, marginBottom: 18}}>
        <span style={{background: green, borderRadius: 999, padding: '8px 14px', fontSize: 20}}>{t('Finished video', '已完成视频')} · {lang === 'en' ? 'en-female' : 'zh-female'}</span>
      </div>
      <Button primary>{t('Download video', '下载视频')}</Button>
      <p style={{fontSize: 22, color: muted}}>{t('The player and this download are the same file.', '播放器里的文件和这次下载是同一个。')}</p>
    </div>
  );
}

function Scene({scene, lang, index, total}: {scene: {id: string; title: string; lines: string[]; frames: number}; lang: 'en' | 'zh'; index: number; total: number}) {
  const frame = useCurrentFrame();
  const progress = Math.min(1, frame / scene.frames);
  const active = Math.min(2, Math.floor(progress * 3));
  return (
    <AbsoluteFill style={{background: '#f4f6f2', color: ink, fontFamily: 'Arial, "PingFang SC", sans-serif', padding: '56px 88px'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <div style={{fontSize: 36, fontWeight: 750}}>lumen<span style={{color: green}}>.</span></div>
        <div style={{fontSize: 20, color: muted, letterSpacing: 2}}>{lang === 'en' ? 'VOICE WALKTHROUGH' : '配音流程'}　{String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</div>
      </div>
      <div style={{display: 'grid', gridTemplateColumns: '0.82fr 1.18fr', gap: 56, alignItems: 'center', height: 760, opacity: interpolate(frame, [0, 10], [0, 1], {extrapolateRight: 'clamp'})}}>
        <div>
          <div style={{color: green, fontSize: 20, fontWeight: 650, marginBottom: 18}}>{lang === 'en' ? `STEP ${index + 1}` : `第 ${index + 1} 步`}</div>
          <h1 style={{fontSize: lang === 'en' ? 54 : 56, lineHeight: 1.12, letterSpacing: -1, margin: '0 0 28px', fontWeight: 650}}>{scene.title}</h1>
          {scene.lines.map((item, i) => (
            <div key={item} style={{fontSize: 26, lineHeight: 1.35, padding: '14px 16px', marginBottom: 10, borderRadius: 14, background: active === i ? '#e0eddf' : 'transparent', color: active === i ? ink : muted}}>
              <span style={{color: green, marginRight: 10}}>0{i + 1}</span>{item}
            </div>
          ))}
        </div>
        <Panel id={scene.id} lang={lang} active={active} />
      </div>
      <div style={{position: 'absolute', bottom: 24, left: 88, right: 88, display: 'flex', justifyContent: 'space-between', fontSize: 16, color: muted}}>
        <span>{lang === 'en' ? 'Illustrated from product labels' : '按产品界面文案示意'}</span>
        <span>{lang === 'en' ? 'Studio after sign-in was not recorded' : '登录后的工作室未录屏'}</span>
      </div>
    </AbsoluteFill>
  );
}

export function VoiceWalkthrough({lang}: {lang: 'en' | 'zh'}) {
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
        <div style={{position: 'absolute', left: 160, right: 160, bottom: 64, textAlign: 'center', background: 'rgba(244,246,242,0.94)', borderRadius: 16, padding: '12px 20px', fontFamily: 'Arial, "PingFang SC", sans-serif', fontSize: 28, lineHeight: 1.35, color: ink}}>
          {caption.text}
        </div>
      )}
    </AbsoluteFill>
  );
}

export const voiceTiming = timing;
