# Right Inspector Implementation Plan

**Goal:** Make scene tools clear and directly usable, with fewer nested disclosures.
**Architecture:** A small scene-navigation component and visual preset component reuse the existing ManualEditor state and handlers. Flat sections replace wrapper accordions; task-specific defaults expose frequent controls. Scoped CSS updates the inspector and draft preview without changing render data.
**Tech Stack:** React, TypeScript, CSS, existing Playwright browser audit.

- [x] Build localized scene navigation and preset components with accessible labels and existing lock/approval behavior.
- [x] Flatten ManualEditor groups; move help and scene ordering to secondary placement; remove irrelevant analysis notice from editing tabs.
- [x] Apply responsive inspector typography, spacing, numeric values, focus styling and larger draft preview.
- [x] Inspect RU desktop/mobile screenshots and run affected browser flows, TypeScript build and localization checks.
- [x] Publish shared UI, verify public build and commit result.
