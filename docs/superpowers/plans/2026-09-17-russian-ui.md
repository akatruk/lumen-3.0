# Russian interface

Requested scope: add Russian alongside English and Chinese throughout the existing interface. Keep generated project content and voiceover language independent of the UI locale.

Implementation: shared Russian message catalog for existing bilingual UI messages; explicit three-option language selector on login, desktop and mobile; persistent validated locale; separate content-language type and safe English fallback for previously generated bilingual content.

- [x] Extract and translate existing interface messages, errors and accessibility labels.
- [x] Wire shared translation into all screens and editors; distinguish UI locale from project output language.
- [x] Add language selector and persistence. Format dates/numbers for Russian.
- [x] Build; verify catalog coverage, language switching/reload, project creation payload, editor and voiceover in Chrome, desktop and mobile.
- [x] Deploy frontend, check live test11 without altering project media, revoke QA session and commit.
