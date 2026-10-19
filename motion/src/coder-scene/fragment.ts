// test1 window only. Not a default for other projects.
import type {GraphicsEvent} from './graphicsContract';

export const FRAGMENT_PROJECT_ID = '50ea1ad005fa42dca35a04c5485cb2da';
export const PLAN_HASH = 'cbbfc9395b054114560ab8a5be6a08e513a456a878bc5906457b006f28b35731';

const ORIGIN = 46.72;
const FPS = 30;

function frameAt(seconds: number): number {
  return Math.round((seconds - ORIGIN) * FPS);
}

export const EVENTS: GraphicsEvent[] = [
  {id: 'g1', text: '原始积累证明', role: 'category', group: 1, relation: null, appearFrame: 26},
  {id: 'd1', text: '工资完税单', role: 'document', group: 1, relation: 'alternative', appearFrame: 101},
  {id: 'd2', text: '分红凭证', role: 'document', group: 1, relation: 'alternative', appearFrame: 149},
  {id: 'd3', text: '股东决议', role: 'document', group: 1, relation: 'alternative', appearFrame: 202},
  {id: 'g2', text: '资产变现链条', role: 'category', group: 2, relation: null, appearFrame: 266},
  {id: 'd4', text: '房产买卖合同', role: 'document', group: 2, relation: 'sequence', appearFrame: 334},
  {id: 'd5', text: '股权转让协议', role: 'document', group: 2, relation: 'sequence', appearFrame: 391},
  {id: 'd6', text: '银行完税流水', role: 'document', group: 2, relation: 'sequence', appearFrame: 451},
];

export type CaptionCue = {text: string; startFrame: number};

// Saved word starts from source-transcript.json. Not a new transcription.
export const CAPTION_CUES: CaptionCue[] = [
  {text: '第一叫', startFrame: frameAt(46.72)},
  {text: '原始积累证明', startFrame: frameAt(47.6)},
  {text: '包括', startFrame: frameAt(49.6)},
  {text: '工资完税单', startFrame: frameAt(50.08)},
  {text: '分红凭证', startFrame: frameAt(51.68)},
  {text: '或股东决议', startFrame: frameAt(53.2)},
  {text: '第二叫', startFrame: frameAt(54.88)},
  {text: '资产变现链条', startFrame: frameAt(55.6)},
  {text: '房产买卖合同', startFrame: frameAt(57.84)},
  {text: '股权转让协议', startFrame: frameAt(59.76)},
  {text: '与银行完税流水', startFrame: frameAt(61.68)},
];

export function activeGroup(frame: number): 1 | 2 {
  return frame >= 266 ? 2 : 1;
}

export function activeId(frame: number): string | null {
  const group = activeGroup(frame);
  const shown = EVENTS.filter((item) => item.group === group && item.role === 'document' && item.appearFrame <= frame);
  return shown.length ? shown[shown.length - 1].id : null;
}

export function captionAt(frame: number): string {
  let current = CAPTION_CUES[0].text;
  for (const cue of CAPTION_CUES) {
    if (frame >= cue.startFrame) current = cue.text;
  }
  return current;
}
