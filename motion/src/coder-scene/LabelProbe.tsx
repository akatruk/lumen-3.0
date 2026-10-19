// Fixture only. These titles are not the source speech.
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {GraphicsBoard} from './GraphicsBoard';
import type {GraphicsEvent} from './graphicsContract';
import {BOARD} from './layout';

const FIXTURE: GraphicsEvent[] = [
  {id: 'a', text: '短', role: 'category', group: 1, relation: null, appearFrame: 0},
  {id: 'b', text: '股东决议', role: 'document', group: 1, relation: 'alternative', appearFrame: 0},
  {id: 'c', text: '这是一个很长的测试标题不会出现在原视频里', role: 'document', group: 1, relation: 'alternative', appearFrame: 0},
  {id: 'd', text: '或股东决议不能拆开', role: 'document', group: 1, relation: 'alternative', appearFrame: 0},
];

export const LabelProbe = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: '#111'}}>
      <div style={{position: 'absolute', left: BOARD.left, top: BOARD.top, width: BOARD.width, height: BOARD.height, overflow: 'hidden'}}>
        <GraphicsBoard frame={frame} fps={fps} width={BOARD.width} height={BOARD.height} activeGroup={1} activeId="c" events={FIXTURE} />
      </div>
    </AbsoluteFill>
  );
};
