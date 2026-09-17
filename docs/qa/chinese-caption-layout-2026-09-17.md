# Word-aware Chinese caption layout

Read-only review of existing production QA found a reported split of 工作证 across subtitle lines. The renderer previously divided Chinese strings by character count twice: line wrapping and multi-card splitting.

Chinese wrapping now uses pinned offline Jieba segmentation and a bounded line-layout pass. Layout penalizes opening punctuation at line ends, closing punctuation at line starts and very short lines. Multi-card splitting reuses those boundaries. The transcript characters are preserved exactly; this change does not correct recognition errors or rewrite speech. Words longer than the line limit must still be split. Existing encoded exports remain unchanged until rerendered.

Tests cover 工作证, 房地产, 管理/逻辑, 护照, numbers, punctuation, long captions and ASS injection sanitization. Local logic checks passed; two real subtitle-render tests require server FFmpeg/libass, which the local FFmpeg lacks. Server results follow below.

Dependency: jieba==0.42.1 (MIT); https://github.com/fxsjy/jieba

Server validation: 22 passed in 23.87 seconds across media logic, actual EN/ZH emphasis rendering and render regression tests, using the isolated lumen_qa database. No customer projects were mutated and no paid AI calls were made.
