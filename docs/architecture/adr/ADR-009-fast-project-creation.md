# ADR-009: Fast project creation without AI inference

## Status

Accepted — 2026-10-12

## Context

Studio create previously enqueued `studio_analyze` (OpenRouter Director + optional Douyin DNA) before the workspace opened. That blocked editing on external LLM credit and added cost on every upload.

## Decision

1. `FAST_PROJECT_CREATION_ENABLED` (default true): create writes source + ffprobe metadata and sets `status=ready` with **no** analyze job and **no** LLM. A `transcribe` job may be queued. That is CPU ASR, not Director inference, and it does not block the ready response.
2. Deferred analysis runs in `ensure_analysis` when the user presses Create video (or when a legacy analyze job runs without an LLM).
3. `LLM_PROVIDER` defaults to `none`. OpenRouter remains an optional provider behind the abstraction in `backend/providers/`.
4. Source cache key: `source_checksum` + `analysis_version`.

## Consequences

- Upload works with zero AI credentials.
- Heuristic Director plans have empty recommendations until an LLM path is configured.
- Rollback: disable fast create and set `LLM_PROVIDER=openrouter` with a funded key.
