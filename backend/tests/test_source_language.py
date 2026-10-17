"""Source language is independent of the requested output language."""

import time

from backend.db import connect, init_db
from backend.language import (
    decide_source_language,
    detect_source_locale,
    explicit_user_source_language,
    resolve_voice,
)
from backend.source_transcript import source_language_decision, source_locale_for_rows


def _rows(*pairs):
    cursor = 0.0
    rows = []
    for duration, text in pairs:
        rows.append({"start": cursor, "end": cursor + duration, "text": text})
        cursor += duration
    return rows


EN = _rows((30, "The price of the house is not very good and the street is quiet"))
ZH = _rows((30, "很多人第一次来咨询的时候都会把地段放在第一位"))
MIXED = _rows(
    (20, "The price of the house is not very good"),
    (20, "很多人第一次来咨询的时候都会把地段放在第一位"),
)
EN_WITH_CJK = _rows(
    (40, "The price of the house is not very good and the owner still wants to sell"),
    (3, "關注自美"),
)


def test_english_source_and_english_target_keep_original_audio():
    decision = decide_source_language(
        EN,
        project_language="en",
        detection={"languageMode": "automatic", "detectedLanguage": "en", "languageProbability": 0.97},
    )
    assert decision["sourceLanguage"] == "en-US"
    assert decision["languageProvenance"] == "automatic"
    assert decision["projectLanguage"] == "en-US"
    voice = resolve_voice(source_language=decision["sourceLanguage"], target_language="en-US")
    assert voice["mode"] == "original" and voice["voiceId"] is None


def test_chinese_source_and_chinese_target_keep_original_audio():
    decision = decide_source_language(
        ZH,
        project_language="zh",
        detection={"languageMode": "automatic", "detectedLanguage": "zh", "languageProbability": 0.99},
    )
    assert decision["sourceLanguage"] == "zh-CN"
    assert decision["languageProvenance"] == "automatic"
    voice = resolve_voice(source_language=decision["sourceLanguage"], target_language="zh-CN")
    assert voice["mode"] == "original"


def test_chinese_source_and_english_target_is_a_dub():
    decision = decide_source_language(
        ZH,
        project_language="en",
        detection={"languageMode": "automatic", "detectedLanguage": "zh", "languageProbability": 0.99},
    )
    assert decision["sourceLanguage"] == "zh-CN"
    assert decision["projectLanguage"] == "en-US"
    voice = resolve_voice(source_language=decision["sourceLanguage"], target_language="en-US")
    assert voice["mode"] == "dubbed"
    assert voice["voiceId"] == "en-male"


def test_mixed_speech_does_not_dub():
    decision = decide_source_language(
        MIXED,
        project_language="en",
        detection={"languageMode": "automatic", "detectedLanguage": "zh", "languageProbability": 0.62},
    )
    assert decision["status"] == "mixed"
    assert decision["sourceLanguage"] is None
    assert decision["dubbing"] == "blocked"
    assert source_locale_for_rows(MIXED) is None
    voice = resolve_voice(source_language=None, target_language="en-US", language_status="mixed")
    assert voice["mode"] == "original"
    assert voice["path"] == "language_uncertain"
    assert voice["dubbing"] == "blocked"


def test_one_cjk_segment_does_not_make_the_transcript_chinese():
    assert detect_source_locale(
        "The price of the house is not very good " * 20 + "關注"
    ) == "en-US"
    decision = source_language_decision(EN_WITH_CJK)
    assert decision["sourceLanguage"] == "en-US"
    assert decision["status"] == "resolved"
    assert source_locale_for_rows(EN_WITH_CJK) == "en-US"


def test_forced_language_is_not_reported_as_automatic():
    forced = decide_source_language(
        EN,
        project_language="en",
        detection={
            "languageMode": "forced",
            "detectedLanguage": "en",
            "languageProbability": 1,
            "forcedTranscriptionLanguage": "en",
        },
    )
    assert forced["languageProvenance"] == "forced"
    assert forced["languageMode"] == "forced"
    assert forced["detectedLanguage"] is None
    assert forced["languageProbability"] is None
    assert forced["forcedTranscriptionLanguage"] == "en-US"

    auto = decide_source_language(
        EN,
        detection={"languageMode": "automatic", "detectedLanguage": "en", "languageProbability": 0.91},
    )
    assert auto["languageProvenance"] == "automatic"
    assert auto["detectedLanguage"] == "en-US"
    assert auto["languageProbability"] == 0.91


def test_output_language_is_not_a_source_setting():
    assert explicit_user_source_language({"language": "en", "video_language": "en-US"}) is None
    assert explicit_user_source_language({"source_language": "zh-CN", "language": "en"}) == "zh-CN"


def test_worker_does_not_force_the_output_language(tmp_path, monkeypatch):
    from backend.config import settings
    from backend.transcription import persist_source_transcript

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "asr_model_cache", str(tmp_path / "asr"))
    init_db()
    pid = "c" * 32
    source = tmp_path / pid / "source"
    source.parent.mkdir()
    source.write_bytes(b"original4-bytes")
    now = time.time()
    with connect() as db:
        db.execute(
            "INSERT INTO users(id,email,password,created) VALUES(?,?,?,?)",
            ("u", "lang@example.com", "x", now),
        )
        db.execute(
            "INSERT INTO projects(id,user_id,title,brief,language,aspect,auto_render,generative,budget,status,stage,metadata,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (pid, "u", "original4", "", "en", "original", 0, 0, 1, "ready", "ready", '{"duration":4}', now, now),
        )
        db.execute(
            "INSERT INTO studio_projects(project_id,context,dna,plan,decisions,revision) VALUES(?,?,?,?,?,?)",
            (pid, '{"language":"en","video_language":"en-US"}', "[]", None, "[]", 0),
        )
    seen = {}

    def fake(source, *, duration=None, language=None, project_id=None):
        seen["language"] = language
        from backend import whisperx_local
        whisperx_local.transcribe_segments.last_info = {
            "languageMode": "automatic",
            "detectedLanguage": "zh",
            "languageProbability": 0.96,
            "forcedTranscriptionLanguage": None,
            "modelId": "Systran/faster-whisper-small",
            "modelVersion": "test",
            "configVersion": "cpu-int8-vad-1",
        }
        return ([{"start": 0, "end": 4, "text": "很多人第一次来咨询"}], "whisperx")

    monkeypatch.setattr("backend.source_analysis._transcribe_source", fake)
    saved = persist_source_transcript(pid)
    assert seen["language"] is None
    assert saved["sourceLanguage"] == "zh-CN"
    assert saved["languageProvenance"] == "automatic"
    assert saved["detectedLanguage"] == "zh-CN"
    with connect() as db:
        row = db.execute("SELECT language, metadata FROM projects WHERE id=?", (pid,)).fetchone()
    assert row["language"] == "en"
    assert '"source_language": "zh-CN"' in row["metadata"] or '"source_language":"zh-CN"' in row["metadata"]
