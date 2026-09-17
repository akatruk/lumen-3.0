# Apple-inspired Lumen visual system

Applied the user-requested apple-design skill: https://github.com/emilkowalski/skills/blob/main/skills/apple-design/SKILL.md

System fonts, neutral surfaces, blue actions, translucent navigation, clear status colors, immediate press feedback, reduced motion/transparency and increased contrast support. Dedicated apple-design.css is loaded after feature CSS. Native upload, select and text controls remain unchanged. No new gesture interaction or animation dependency introduced.

Validation: TypeScript/Vite production build passed. Actual React app rendered in headless Chrome with mocked session/project API responses, English desktop and Chinese mobile screenshots inspected. Mobile menu opens; upload control computed display is block. This is UI fixture validation, not an authenticated production editing test. Screenshots precede final minor border/fieldset/responsive-submit refinements.
