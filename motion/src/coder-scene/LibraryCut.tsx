import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {BOARD, CAPTION, SPEAKER} from './layout';
import {CJK_FONT} from './sceneRules';

export const EVIDENCE_FRAMES = 622;

const CUES: {text: string; start: number}[] = [
  {text: '房产买卖合同', start: 14},
  {text: '股权转让协议', start: 72},
  {text: '与银行完税流水', start: 130},
  {text: '第三叫', start: 194},
  {text: '证据依据', start: 228},
  {text: '合法的证据协议', start: 269},
  {text: '资金来源', start: 346},
  {text: '第四叫', start: 389},
  {text: '跨境路径合规性', start: 420},
  {text: '资金打入', start: 492},
  {text: '官方监管账户', start: 521},
  {text: '合法渠道', start: 581},
];

const PANELS: {from: number; duration: number; file: string; kind: 'image' | 'video'}[] = [
  {from: 14, duration: 58, file: 'ev_property_sale_contract.png', kind: 'image'},
  {from: 72, duration: 60, file: 'ev_equity_transfer_agreement.png', kind: 'image'},
  {from: 132, duration: 62, file: 'ev_bank_ledger.png', kind: 'image'},
  {from: 389, duration: 89, file: 'global_route_001.webm', kind: 'video'},
];

const panelAt = (frame: number) => PANELS.find((panel) => frame >= panel.from && frame < panel.from + panel.duration);

export const LibraryCut = () => {
  const frame = useCurrentFrame();
  const split = Boolean(panelAt(frame));
  let caption = CUES[0].text;
  for (const cue of CUES) {
    if (frame >= cue.start) caption = cue.text;
  }
  const speaker = split
    ? {position: 'absolute' as const, left: SPEAKER.left, top: SPEAKER.top, width: SPEAKER.width, height: SPEAKER.height, objectFit: 'cover' as const}
    : {position: 'absolute' as const, left: 0, top: 0, width: 1080, height: 1920, objectFit: 'cover' as const};
  return (
    <AbsoluteFill style={{backgroundColor: '#111'}}>
      <OffthreadVideo src={staticFile('speaker.mp4')} style={speaker} />
      {PANELS.map((panel) => (
        <Sequence key={panel.file} from={panel.from} durationInFrames={panel.duration}>
          <div style={{position: 'absolute', left: BOARD.left, top: BOARD.top, width: BOARD.width, height: BOARD.height, overflow: 'hidden', backgroundColor: '#F3EFE6'}}>
            {panel.kind === 'image' ? (
              <Img src={staticFile(panel.file)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
            ) : (
              <OffthreadVideo muted src={staticFile(panel.file)} style={{width: '100%', height: '100%', objectFit: 'contain', backgroundColor: '#111'}} />
            )}
          </div>
        </Sequence>
      ))}
      <div
        style={{
          position: 'absolute',
          left: CAPTION.left,
          top: CAPTION.top,
          width: CAPTION.width,
          height: CAPTION.height,
          color: '#fff',
          fontSize: 64,
          lineHeight: 1.15,
          fontWeight: 650,
          fontFamily: CJK_FONT,
          textShadow: '0 2px 8px rgba(0,0,0,0.85)',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {caption}
      </div>
    </AbsoluteFill>
  );
};
