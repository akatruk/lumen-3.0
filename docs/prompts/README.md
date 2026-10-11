# Lumen prompts

| Prompt | Role |
| --- | --- |
| **[cinematic-director-v3-quality-recovery.md](./cinematic-director-v3-quality-recovery.md)** | **MAIN** agent/product brief — Director V3 / Remotion / video QA. **Start here** for console work. Not loaded into the model wholesale. |
| `backend/assembly_prompt.txt` | Hypit **model** handoff (via `hypit_prompt.py`). Concise QUALITY ENFORCEMENT + E2E assembly rules. |
| `backend/director_media_rules.py` | Shared measurable rules for Remotion planner/validator (same-source ban, etc.). |
| [lumen-hypit-integration-cursor-prompt.md](./lumen-hypit-integration-cursor-prompt.md) | Historical Hypit **integration planning** — **NOT** the product MAIN prompt. |

## Routing

- Task mentions Director, Remotion, preview, captions, shot plan, video quality → load **MAIN** `cinematic-director-v3-quality-recovery.md` first.
- Task is Hypit studio→prompt handoff sentences → `backend/assembly_prompt.txt` via `backend/hypit_prompt.py`.
- Do not treat `lumen-hypit-integration-cursor-prompt.md` as the default product brief.
