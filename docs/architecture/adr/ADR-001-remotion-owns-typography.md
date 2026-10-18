# ADR-001: Remotion owns deterministic typography, layout and motion

Status: Accepted (2026-10-11)

Context: Studio controls and generated stills must not invent parallel CSS/seek engines.

Decision: Remotion (`motion/`) renders text via AutoFitText/AnimatedCaption; Director picks type/variant/data only.

Consequences: Hypit prompts stay for AI picture path; Remotion path must not bake captions into generated images.
