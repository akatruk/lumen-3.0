"""Provider-neutral AI surfaces for Lumen (LLM, transcript, Director).

Production default is local / none — OpenRouter is optional, never required for
project creation.
"""

from .llm import LLMProvider, get_llm_provider
from .transcript import TranscriptProvider, get_transcript_provider
from .director import DirectorProvider, get_director_provider

__all__ = [
    "LLMProvider",
    "DirectorProvider",
    "TranscriptProvider",
    "get_llm_provider",
    "get_director_provider",
    "get_transcript_provider",
]
