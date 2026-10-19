// Trusted shell. Speaker, audio and captions stay here.
import {AbsoluteFill, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {GraphicsBoard} from './GraphicsBoard';
import {EVENTS, activeGroup, activeId, captionAt} from './fragment';
import {BOARD, CAPTION, SPEAKER} from './layout';
import {CJK_FONT, captionFont} from './sceneRules';

export const TrustedScene = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const caption = captionAt(frame);
  const captionSize = captionFont(caption, CAPTION.width, CAPTION.height);
  return (
    <AbsoluteFill style={{backgroundColor: '#111'}}>
      <OffthreadVideo
        src={staticFile('speaker.mp4')}
        style={{position: 'absolute', left: SPEAKER.left, top: SPEAKER.top, width: SPEAKER.width, height: SPEAKER.height, objectFit: 'cover'}}
      />
      <div
        style={{
          position: 'absolute',
          left: BOARD.left,
          top: BOARD.top,
          width: BOARD.width,
          height: BOARD.height,
          overflow: 'hidden',
          contain: 'strict',
          transform: 'translateZ(0)',
        }}
      >
        <GraphicsBoard
          frame={frame}
          fps={fps}
          width={BOARD.width}
          height={BOARD.height}
          activeGroup={activeGroup(frame)}
          activeId={activeId(frame)}
          events={EVENTS}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: CAPTION.left,
          top: CAPTION.top,
          width: CAPTION.width,
          height: CAPTION.height,
          color: '#fff',
          fontSize: captionSize,
          lineHeight: 1.2,
          fontWeight: 650,
          fontFamily: CJK_FONT,
          textShadow: '0 2px 8px rgba(0,0,0,0.8)',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {caption}
      </div>
    </AbsoluteFill>
  );
};
