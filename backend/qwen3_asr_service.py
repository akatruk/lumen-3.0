"""Serial transcription service. The model runs in a child, outside the web and worker."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import wave
from pathlib import Path

from .asr_memory import assert_can_load, available_mb

SOCKET_PATH = os.environ.get(
    "QWEN_ASR_SOCKET",
    "/mnt/volume_nyc1_1791446889637/qwen3-asr/asr.sock",
)
QWEN_PYTHON = os.environ.get(
    "QWEN_PYTHON",
    "/mnt/volume_nyc1_1791446889637/qwen3-asr/venv/bin/python",
)
WORK = Path(os.environ.get(
    "QWEN_ASR_WORK",
    "/mnt/volume_nyc1_1791446889637/qwen3-asr/work",
))
HERE = Path(__file__).resolve().parent / "asr_qwen"
NAMES = {
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "en": "English",
    "en-us": "English",
    "ru": "Russian",
    "ru-ru": "Russian",
    "chinese": "Chinese",
    "english": "English",
    "russian": "Russian",
}


def _send(conn: socket.socket, payload: dict) -> None:
    conn.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode())


def _wav(source: Path, dest: Path) -> tuple[float, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(source),
            "-vn", "-ac", "1", "-ar", "16000",
            str(dest),
        ],
        check=True,
        capture_output=True,
    )
    with wave.open(str(dest), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate() or 16000
        samples = handle.readframes(frames)
    peak = 0
    for index in range(0, len(samples) - 1, 2):
        value = int.from_bytes(samples[index:index + 2], "little", signed=True)
        peak = max(peak, abs(value))
    return (frames / rate if rate else 0.0), peak


def _model_child_running() -> bool:
    proc = Path("/proc")
    if not proc.is_dir():
        return False
    for child in proc.iterdir():
        if not child.name.isdigit():
            continue
        try:
            command = (child / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="ignore")
        except OSError:
            continue
        if "asr_qwen/recognize.py" in command or "asr_qwen/align.py" in command:
            return True
    return False


def _run(script: str, args: list[str]) -> dict:
    if _model_child_running():
        raise RuntimeError("TRANSCRIPTION_BUSY")
    assert_can_load(available_mb())
    completed = subprocess.run(
        [QWEN_PYTHON, str(HERE / script), *args],
        capture_output=True,
        text=True,
        timeout=1200,
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "")[-800:]
        raise RuntimeError(f"{script} exit {completed.returncode}: {tail}")
    out = args[args.index("--out") + 1]
    return json.loads(Path(out).read_text(encoding="utf-8"))


def _handle(request: dict, conn: socket.socket) -> None:
    from .qwen3_segments import group_tokens

    source = Path(request["audio"])
    if not source.is_file():
        raise FileNotFoundError(str(source))
    job = WORK / str(request.get("id") or "job")
    if job.exists():
        for child in job.iterdir():
            child.unlink()
    job.mkdir(parents=True, exist_ok=True)
    _send(conn, {"phase": "transcription_processing_audio"})
    wav = job / "audio.wav"
    duration, peak = _wav(source, wav)
    if peak < 200:
        _send(conn, {
            "phase": "done",
            "speech": "silence",
            "duration": round(duration, 3),
            "segments": [],
            "text": "",
        })
        return
    override = str(request.get("language") or "").strip()
    forced = NAMES.get(override.lower()) if override else None
    _send(conn, {"phase": "transcription_running"})
    from .asr_memory import assert_can_load, available_mb

    assert_can_load(available_mb())
    recognized = _run("recognize.py", [
        "--audio", str(wav),
        "--out", str(job / "asr.json"),
        "--language", forced or "",
    ])
    text = str(recognized.get("text") or "").strip()
    if not text:
        _send(conn, {
            "phase": "done",
            "speech": "silence",
            "duration": round(duration, 3),
            "raw": recognized,
            "segments": [],
            "text": "",
        })
        return
    language_name = forced or str(recognized.get("language") or "")
    if language_name not in {"Chinese", "English", "Russian"}:
        raise RuntimeError(f"unsupported_alignment_language:{language_name}")
    _send(conn, {"phase": "transcription_timing"})
    aligned = _run("align.py", [
        "--audio", str(wav),
        "--text", text,
        "--language", language_name,
        "--out", str(job / "align.json"),
    ])
    segments, uncertain = group_tokens(aligned.get("tokens") or [], text)
    _send(conn, {
        "phase": "done",
        "speech": "speech",
        "duration": round(duration, 3),
        "text": text,
        "language": language_name,
        "forcedLanguage": forced,
        "segments": segments,
        "uncertain": uncertain,
        "recognition": recognized,
        "alignment": {
            "model": aligned.get("model"),
            "revision": aligned.get("revision"),
            "loadSeconds": aligned.get("loadSeconds"),
            "inferSeconds": aligned.get("inferSeconds"),
            "tokens": len(aligned.get("tokens") or []),
        },
    })


def serve() -> None:
    path = Path(SOCKET_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    os.chmod(path, 0o660)
    server.listen(4)
    while True:
        conn, _ = server.accept()
        try:
            raw = b""
            while b"\n" not in raw:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                raw += chunk
            if not raw:
                continue
            request = json.loads(raw.split(b"\n", 1)[0])
            _handle(request, conn)
        except Exception as exc:
            try:
                _send(conn, {"phase": "error", "error": str(exc)[:800]})
            except Exception:
                pass
        finally:
            conn.close()


if __name__ == "__main__":
    serve()
