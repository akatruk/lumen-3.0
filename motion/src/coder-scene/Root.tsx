import type {FC} from 'react';
import {Composition} from 'remotion';
import {LabelProbe} from './LabelProbe';
import {TrustedScene} from './TrustedScene';
import {CANVAS} from './layout';

export const RemotionRoot: FC = () => {
  return (
    <>
      <Composition
        id="QwenScene"
        component={TrustedScene}
        durationInFrames={CANVAS.frames}
        fps={CANVAS.fps}
        width={CANVAS.width}
        height={CANVAS.height}
      />
      <Composition id="LabelProbe" component={LabelProbe} durationInFrames={2} fps={CANVAS.fps} width={CANVAS.width} height={CANVAS.height} />
    </>
  );
};
