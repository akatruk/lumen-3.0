# Visual data cards

Added editor-supplied number and comparison cards with bilingual heading, values and source/date, clip-relative timing and fade animation. Cards render over owned video and compile into the Director Timeline inserts track. Project language selects the rendered text. Clip approval and locks cover cards. AI clip proposals cannot change or invent their data.

Validation: frontend build; isolated Linux suite 74 passed, 2 skipped; PostgreSQL QA suite 15 passed. Browser saved bilingual comparison on an existing two-clip timeline containing a locked clip. Inspected actual Chinese rendered frame. Pixel assertions verify that the panel appears only during its time range. No paid AI requests.

These are manual inserts, not automated fact checking, map/chart generation or external B-roll retrieval. Each clip supports one card; split the clip for multiple cards. Draft video preview does not render the card; the data-card track shows its timing and final render shows exact appearance.
