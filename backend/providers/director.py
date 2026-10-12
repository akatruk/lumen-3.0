"""Director plan providers — heuristic local vs optional LLM."""

from __future__ import annotations

from typing import Protocol

from ..config import settings
from ..schemas import Caption, Scene, Score, Text


def _t(en: str, zh: str | None = None) -> Text:
    return Text(en=en[:2400], zh=(zh or en)[:2400])


class DirectorProvider(Protocol):
    name: str

    def build_plan(self, *, duration: float, language: str, transcript: list[dict], dna: list | None = None):
        ...


class HeuristicDirectorProvider:
    """Local Director substitute: transcript + duration → valid Director, no LLM."""

    name = "heuristic"

    def build_plan(self, *, duration: float, language: str, transcript: list[dict], dna: list | None = None):
        from ..studio import Director

        step = min(20.0, max(6.0, duration / 4 if duration else 10.0))
        scenes = []
        t = 0.0
        i = 1
        roles = ("hook", "context", "proof", "product", "cta", "transition")
        while t < duration - 0.05:
            end = min(t + step, duration)
            scenes.append(
                Scene(
                    start=round(t, 3),
                    end=round(end, 3),
                    title=_t(f"Segment {i}"),
                    observation=_t("Local plan segment from source timing."),
                    role=roles[min(i - 1, len(roles) - 1)],
                )
            )
            t = end
            i += 1
        if not scenes:
            scenes = [
                Scene(
                    start=0.0,
                    end=round(duration, 3),
                    title=_t("Full clip"),
                    observation=_t("Single-scene local plan."),
                    role="context",
                )
            ]

        caps = []
        for seg in transcript:
            start = float(seg.get("start") or 0)
            end = float(seg.get("end") or start)
            text = str(seg.get("text") or "").strip() or "…"
            if end <= start:
                end = min(start + 1.0, duration)
            end = min(end, duration)
            caps.append(
                Caption(
                    start=round(start, 3),
                    end=round(end, 3),
                    original=text[:300],
                    en=text[:300],
                    zh=text[:300],
                    ru=text[:400],
                )
            )
        if not caps:
            caps = [
                Caption(
                    start=0.0,
                    end=round(duration, 3),
                    original="[no speech]",
                    en="[no speech]",
                    zh="[no speech]",
                    ru="[no speech]",
                )
            ]

        return Director(
            summary=_t("Local plan from source transcript (no external LLM)."),
            strongest_moment=_t("Opening segment"),
            audience=_t("Project audience from upload settings"),
            scores=[
                Score(category="clarity", value=70, reason=_t("Heuristic baseline")),
                Score(category="pacing", value=60, reason=_t("Even segment grid")),
                Score(category="hook", value=50, reason=_t("No LLM ranking")),
            ],
            scenes=scenes,
            transcript=caps,
            recommendations=[],
            uncertainties=[_t("Built without external LLM; refine at generation if needed.")],
            transfers=[],
        )


class OpenRouterDirectorProvider:
    name = "openrouter"

    def build_plan(self, *, duration: float, language: str, transcript: list[dict], dna: list | None = None):
        # Full OpenRouter path stays in studio.analyze when LLM is configured.
        raise RuntimeError("use_studio_analyze_for_openrouter")


def get_director_provider(name: str | None = None) -> DirectorProvider:
    llm = (name or getattr(settings, "llm_provider", "none") or "none").strip().lower()
    if llm in ("openrouter", "or") and settings.openrouter_api_key:
        return OpenRouterDirectorProvider()
    return HeuristicDirectorProvider()
