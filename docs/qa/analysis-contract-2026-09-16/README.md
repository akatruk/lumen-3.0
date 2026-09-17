# Analysis response contract repair

Production events confirmed repeated director_plan `json_invalid` failures after HTTP 200, preceded by a timestamp validation failure. The client requested json_object and supplied the schema only in prompt text.

Changes:
- Request json_schema with strict object properties and required fields; require compatible provider parameters.
- Remove unsupported scalar/collection constraints only from the provider schema. Original Pydantic schema remains in the prompt and validates every response locally.
- Keep property names such as title intact when simplifying schema metadata.
- Allow one additional completed-response validation attempt for reference DNA and Director plans, with a fresh budget reservation. Never retry uncertain HTTP errors automatically.
- Include Director semantic checks and reference timestamp checks within the bounded repair path. Invalid second results still fail closed.
- Cached reference DNA and source media are preserved.

Validation: 21 targeted tests passed locally and against isolated PostgreSQL on the production host. Real provider schema compatibility probe returned HTTP 200 and a Pydantic-valid Director object. Production health check passed after deployment.

Deployment backup: /opt/lumen-rebuild/backups/analysis-contract-20260916-102620
Recovery of failed project 837141609a5c42d5aa70644fe515b3e9 queued once under its existing $5 budget. End-to-end recovery verified: production project status=ready, stage=ready, error=NULL. The saved user video produced a valid plan with the new contract.

No promise of zero provider failures: timeouts, billing limits and invalid second results remain explicit failures rather than fabricated plans.
