// Same split as portraitLayouts: speaker on the right, board on the left.
export const CANVAS = {width: 1080, height: 1920, fps: 30, frames: 507};

const PAD = 28;
const GUTTER = 20;
const SPEAKER_WIDTH = 500;
const SPEAKER_TOP = 140;
const SPEAKER_BOTTOM_CLEARANCE = 356;

export const SPEAKER = {
  left: CANVAS.width - PAD - SPEAKER_WIDTH,
  top: SPEAKER_TOP,
  width: SPEAKER_WIDTH,
  height: CANVAS.height - SPEAKER_TOP - SPEAKER_BOTTOM_CLEARANCE,
};

export const BOARD = {
  left: PAD,
  top: SPEAKER_TOP,
  width: SPEAKER.left - GUTTER - PAD,
  height: SPEAKER.height,
};

export const CAPTION = {
  left: 48,
  top: CANVAS.height - 300,
  width: CANVAS.width - 96,
  height: 220,
};
