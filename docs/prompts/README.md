# Lumen prompts

| Prompt | Role |
| --- | --- |
| **[cinematic-director-v3-quality-recovery.md](./cinematic-director-v3-quality-recovery.md)** | **MAIN** agent/product brief — Director V3 / Remotion / video QA. **Start here** for console work. Not loaded into the model wholesale. |
| `backend/assembly_prompt.txt` | Hypit **main** model body (QUALITY ENFORCEMENT + E2E rules). Content extended only via modules — do not dump recovery checklists here. |
| `backend/prompt_modules/` | Attachable modules: `editing_controls` (Calm/Balanced/Dynamic + sliders), `localization` (RU/EN/ZH). Assembled by `assemble_hypit_prompt` → `hypit_prompt.illustration_request`. |
| `backend/director_media_rules.py` | Shared measurable rules for Remotion planner/validator (same-source ban, etc.). |
| [lumen-hypit-integration-cursor-prompt.md](./lumen-hypit-integration-cursor-prompt.md) | Historical Hypit **integration planning** — **NOT** the product MAIN prompt. |

## Assembly path (Hypit create-video)

```
assembly_prompt.txt  (main, versioned by sha256)
  + STUDIO LEVELS
  + applicable modules (editing_controls@1.0.0, localization@1.0.0, …)
  + MODULE CONFLICTS
  + RUN PARAMS (JSON: editingControls, targetLocale, versions, …)
  + USER CONTENT pointer (timed lines live in author SVML)
```

Job payload stores `promptAssembly: { mainPromptVersion, modules[], conflicts[], runParams }`.
Director/Remotion also receives `visual_plan.editingControls` (not prompt text alone).
Rendition cache: `data/<pid>/localization/<locale>/` (UI language ≠ video language).
Language switch (`PUT …/language`) and montage prefs (`PUT …/editing-controls`) persist only — do not enqueue render.

## Routing

- Task mentions Director, Remotion, preview, captions, shot plan, video quality → load **MAIN** `cinematic-director-v3-quality-recovery.md` first.
- Task is Hypit studio→prompt handoff / modules → `backend/prompt_modules` + `assembly_prompt.txt` via `hypit_prompt.py`.
- Do not treat `lumen-hypit-integration-cursor-prompt.md` as the default product brief.
