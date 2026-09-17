# Clear task and upload states

Shared icon/text/color badges used across project lists, project processing, creative plans, alternatives, clip proposals, media library uploads and platform packages. Green completion, red failures, blue work in progress, amber review/paused states. Completion is not conflated with review approval.

Server-confirmed upload progress shows percentage, saved bytes and transfer rate. At 100% the UI switches to indeterminate file checking instead of implying the entire pipeline has completed. After 20 seconds without a new saved-byte confirmation, the waiting state is explicit. Upload pause is acknowledged and preserves resumability. Reduced-motion and progressbar semantics included.

Validation: TypeScript/Vite production build succeeded. Real shared components rendered in Chrome using production CSS in a local state showcase, inspected at desktop and 390px content widths (screenshots attached). This is visual component verification, not an authenticated full application walkthrough. Production index, JS, CSS and health verified. Static-only deployment, no service restarts; backup backups/status-ui-20260916-111014. JS index-Dwaj8o4r.js; CSS index-CstxNPMW.css.
