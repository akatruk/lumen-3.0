"""Source transcript contract: no placeholder speech, cache by checksum, voice follows language."""

import json
from pathlib import Path

import pytest

from backend.language import resolve_voice
from backend.source_analysis import _transcribe_source
from backend.source_transcript import (
    TranscriptError,
    load_verified,
    save_verified,
    source_locale_for_rows,
)

ROOT = Path(__file__).resolve().parents[2]


def test_placeholder_grid_is_rejected():
    with pytest.raises(TranscriptError) as caught:
        source_locale_for_rows([
            {"start": 0, "end": 8, "original": "[segment 1]"},
            {"start": 8, "end": 16, "original": "[segment 2]"},
        ])
    assert caught.value.code == "SOURCE_TRANSCRIPT_UNAVAILABLE"


def test_empty_plan_stays_unset():
    assert source_locale_for_rows([]) is None


def test_same_language_keeps_the_original_voice():
    kept = resolve_voice(source_language="zh-CN", target_language="zh-CN", voice="zh-male")
    assert kept["mode"] == "original"
    assert kept["voiceId"] is None


def test_missing_target_voice_is_explicit(monkeypatch):
    monkeypatch.setattr("backend.dubbing_audio.VOICES", {})
    missing = resolve_voice(source_language="zh-CN", target_language="en-US", voice="en-male")
    assert missing["status"] == "VOICE_SETUP_REQUIRED"
    assert missing["mode"] == "dubbed"


def test_broken_provider_does_not_invent_segments(tmp_path, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "transcript_provider", "whisperx")
    def boom(self, video_path, language=None):
        raise ImportError("faster_whisper_unavailable")

    monkeypatch.setattr("backend.providers.transcript.WhisperXTranscriptProvider.transcribe", boom)
    source = tmp_path / "source"
    source.write_bytes(b"video")
    with pytest.raises(TranscriptError) as caught:
        _transcribe_source(source, language="zh-CN", duration=4)
    assert caught.value.code == "TRANSCRIPTION_PROVIDER_UNAVAILABLE"


def test_cached_transcript_skips_asr(tmp_path, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    pid = "p" * 32
    source = tmp_path / pid / "source"
    source.parent.mkdir()
    source.write_bytes(b"same-bytes")
    save_verified(
        pid, source,
        [{"start": 0, "end": 4, "text": "很多人第一次来咨询"}],
        provider="faster-whisper-small",
        provenance={"model": "faster-whisper-small"},
        declared_language="zh",
        duration=4,
    )
    monkeypatch.setenv("LUMEN_FORBID_ASR", "1")
    rows, provider = _transcribe_source(source, language="en", duration=4, project_id=pid)
    assert provider == "faster-whisper-small"
    assert rows[0]["text"].startswith("很多人")
    assert load_verified(pid, source)["sourceLanguage"] == "zh-CN"


def test_original_fixtures_are_real_chinese():
    original1 = json.loads((ROOT / "data/director_v5_original1/source.transcript.json").read_text())
    original2 = json.loads((ROOT / "data/original2/source.transcript.json").read_text())
    assert source_locale_for_rows(original1) == "zh-CN"
    assert source_locale_for_rows(original2) == "zh-CN"
    assert "segment" not in original1[0]["original"]


def test_original3_asr_restores_when_checksum_matches(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.source_analysis import source_checksum

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    asr = json.loads((ROOT / "data/original3/asr.json").read_text())
    source = ROOT / "data/original3/source"
    assert source_checksum(source) == "0a82755d83c2eba84647f70189c825a1a9eb5a81503cfca3f711bbb8f6c5d96c"
    pid = "cd5c9ab8b6e944babe80e109038be8bb"
    copied = tmp_path / pid / "source"
    copied.parent.mkdir()
    copied.write_bytes(source.read_bytes())
    record = save_verified(
        pid, copied, asr["segments"],
        provider=asr["model"],
        provenance={"model": asr["model"], "detectedLanguage": asr["detected_language"]},
        declared_language=asr["detected_language"],
        duration=float(asr["audio_duration"]),
    )
    assert record["sourceLanguage"] == "zh-CN"
    assert record["status"] == "verified"
    assert len(record["segments"]) == len(asr["segments"])
    assert record["segments"][-1]["end"] >= 150
    other = tmp_path / "other"
    other.write_bytes(b"not-the-source")
    assert load_verified(pid, other) is None


def test_same_language_job_does_not_dub(tmp_path, monkeypatch):
    from backend import director_v3
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    calls = []
    monkeypatch.setattr(director_v3, "speaker_for", lambda *a, **k: calls.append("speaker") or "speaker")
    monkeypatch.setattr(director_v3, "output_seconds", lambda requested, source: 4)
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)

    def boom(*a, **k):
        raise AssertionError("dub")

    monkeypatch.setattr("backend.worker._dub_for_job", boom)
    monkeypatch.setattr(director_v3, "render_assembly", lambda *a, **k: {"sha256": "abc"})
    # Stop after the voice decision by failing the picture stage.
    def stop(*_a, **_k):
        raise RuntimeError("stop-after-voice")

    monkeypatch.setattr("backend.remotion_engine.resolve_scene_plan", stop)
    payload = {
        "composition": "DirectorV3Preview",
        "duration_seconds": 4,
        "dubbed": True,
        "source_language": "zh-CN",
        "target_language": "zh-CN",
        "voice_resolution": {"mode": "dubbed"},
        "transcript": [{"start": 0, "end": 4, "original": "很多人第一次来咨询"}],
        "plan": {"transcript": [{"start": 0, "end": 4, "original": "很多人第一次来咨询"}]},
    }
    with pytest.raises(RuntimeError, match="stop-after-voice"):
        director_v3.run_job({"id": "p" * 32, "metadata": {"duration": 4}}, payload)
    assert calls == ["speaker"]


def test_model_change_archives_the_previous_transcript(tmp_path, monkeypatch):
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "asr_model", "small")
    monkeypatch.setattr(settings, "asr_config_version", "cpu-int8-vad-1")
    pid = "c" * 32
    source = tmp_path / pid / "source"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"same-bytes")
    segment = [{"start": 0, "end": 4, "text": "很多人第一次来咨询"}]
    save_verified(
        pid, source, segment,
        provider="faster-whisper-small",
        provenance={"modelId": "Systran/faster-whisper-small", "modelVersion": "faster-whisper==1.2.1", "configVersion": "cpu-int8-vad-1"},
        duration=4,
    )
    monkeypatch.setattr(settings, "asr_model", "medium")
    monkeypatch.setattr(settings, "asr_config_version", "cpu-int8-vad-2")
    saved = save_verified(
        pid, source, segment,
        provider="faster-whisper-medium",
        provenance={"modelId": "Systran/faster-whisper-medium", "modelVersion": "faster-whisper==1.2.1", "configVersion": "cpu-int8-vad-2"},
        duration=4,
    )
    folder = tmp_path / pid / "localization"
    archived = list(folder.glob("source-transcript-Systran-faster-whisper-small.json"))
    assert archived
    previous = json.loads(archived[0].read_text(encoding="utf-8"))
    assert previous["modelId"] == "Systran/faster-whisper-small"
    assert saved["modelId"] == "Systran/faster-whisper-medium"
    assert load_verified(pid, source)["modelId"] == "Systran/faster-whisper-medium"


def test_language_mismatch_without_gpu_is_a_voice_error(tmp_path, monkeypatch):
    from backend import director_v3
    from backend.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(director_v3, "speaker_for", lambda *a, **k: "speaker")
    monkeypatch.setattr(director_v3, "output_seconds", lambda requested, source: 4)
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    payload = {
        "composition": "DirectorV3Preview",
        "duration_seconds": 4,
        "dubbed": True,
        "source_language": "zh-CN",
        "target_language": "en-US",
        "voice_resolution": {"mode": "dubbed"},
        "transcript": [{"start": 0, "end": 4, "original": "很多人第一次来咨询"}],
    }
    with pytest.raises(ValueError, match="VOICE_PROVIDER_NOT_CONFIGURED"):
        director_v3.run_job({"id": "p" * 32, "metadata": {"duration": 4}}, payload)
