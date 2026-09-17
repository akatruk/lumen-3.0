# Russian interface

User request: add Russian to the interface alongside English and Chinese.

Use an explicit three-option selector at sign-in, in the sidebar and in the top bar. Keep the existing localStorage language preference; accept ru and preserve en/zh. Update the document language for assistive technology.

Translate interface labels, actions, guidance, error messages and written tutorial chapters through one shared Russian catalog. Reuse existing bilingual UI call sites through a shared translator, so current English and Chinese wording stays intact. Static English messages are catalog keys; automated coverage checks flag untranslated interface additions.

Separate UI Lang from ContentLang. Legacy analysis/caption APIs accept only en/zh. A Russian interface defaults those forms to English and never submits ru accidentally. Existing generated bilingual analysis uses English fallback with an explicit Russian notice. Voiceover has its own independent ru/en/zh selector. Existing tutorial videos remain English/Chinese; Russian written instructions use the English video's timestamps and label its narration accurately.

Deploy frontend assets only, retaining previous bundles and backing up index.html. Do not change any project media, render, edit, budget or voiceover.
