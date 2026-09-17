# Lumen · Chinese onboarding film

A 10-second, 1920×1080, 30 fps Mandarin product walkthrough. Four 75-frame scenes explain upload/brief, analysis, recommendation selection, and preview/download. Interface illustrations are demonstrative; there is no claim that real video processing completes in ten seconds.

Voiceover: MiniMax Speech 2.8 HD via OpenRouter, Chinese (Mandarin)_Warm_Bestie. One continuous synthesis of original instructional copy, divided only at measured sentence silences to align the four scenes. No speech speed adjustment. Master normalized to -16 LUFS / -1.5 dBTP before AAC encoding. The previous macOS system voice has been replaced. Automated comparative listening preferred this variant; this is not evidence of human indistinguishability. Chinese typography uses PingFang SC on macOS. Render on macOS for the same typography, or install an appropriate Simplified Chinese font and update the fallback for other environments.

Preview: `npm install`, then `npx remotion studio --no-open`.

Render: `npx remotion render LumenChineseGuide ../frontend/public/tutorial/lumen-guide-zh.mp4 --codec=h264 --crf=18 --pixel-format=yuv420p --concurrency=2`.

For exact MP4 container duration, remux with `ffmpeg -i input.mp4 -t 10 -c:v copy -c:a aac -b:a 160k -movflags +faststart output.mp4`.

Published assets: frontend/public/tutorial/lumen-guide-zh.{mp4,jpg,vtt}. Embedded on the sign-in screen and studio home using the TutorialVideo component, on-demand native controls, no autoplay, Simplified Chinese caption track.

Validation: 300 video frames; final container 10.000 seconds; H.264 1080p plus AAC; four-scene contact sheet reviewed; production frontend build passed; public video HTTP 200 and byte-range HTTP 206 confirmed.
