"""Record speech on the RunPod pod lumen-web-gpu.

Picture and speech share that machine. OpenRouter is not called for audio.
"""
import base64
import logging
import shlex
import subprocess
from pathlib import Path

from .hypit_gpu import _note_failure, _ssh, _ssh_argv, pod_session

log = logging.getLogger('lumen.speech')

ROOT = '/workspace/lumen-speech'
MODEL = 'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice'
MODEL_DIR = ROOT + '/Qwen3-TTS-12Hz-1.7B-CustomVoice'
PYTHON = ROOT + '/venv/bin/python'

_INSTALL = f'''
set -eu
mkdir -p {ROOT}/hf
if [ ! -x {PYTHON} ]; then
  python3 -m venv --system-site-packages {ROOT}/venv
fi
if ! {PYTHON} -c 'import qwen_tts, soundfile' >/dev/null 2>&1; then
  {ROOT}/venv/bin/pip install -q qwen-tts soundfile
fi
if [ ! -f {MODEL_DIR}/config.json ]; then
  HF_HOME={ROOT}/hf {PYTHON} -c "from huggingface_hub import snapshot_download; snapshot_download({MODEL!r}, local_dir={MODEL_DIR!r})"
fi
echo SPEECH_READY
'''


def speak(text, voice, destination):
    speak_lines([(text, voice, destination)])


def speak_lines(jobs):
    """Synthesize every line with one model load. The pod stops when this returns."""
    if not jobs:
        return
    from .dubbing_audio import VOICES
    specs = []
    for index, (text, voice, _dest) in enumerate(jobs):
        item = VOICES.get(voice)
        spoken = (text or '').strip()
        if not item or not item.get('speaker') or not spoken:
            raise ValueError('dubbing_audio_invalid')
        specs.append({
            'text': spoken,
            'language': item['qwen_language'],
            'speaker': item['speaker'],
            'out': f'/tmp/lumen-speech-{index}.wav',
        })
    with pod_session() as (ip, port, _pod_id):
        _install(ip, port)
        _infer(ip, port, specs)
        for spec, (_text, _voice, destination) in zip(specs, jobs):
            _pull(ip, port, spec['out'], Path(destination))


def _install(ip, port):
    ready = _ssh(ip, port, _INSTALL, timeout=3600)
    if 'SPEECH_READY' not in ready:
        raise _note_failure(RuntimeError('hypit_unavailable'), (ready or 'speech runtime missing')[-500:])


def _infer(ip, port, specs):
    runtime = Path(__file__).with_name('gpu_speech_runtime.py').read_bytes()
    payload = json_bytes(specs)
    script = f'''
set -eu
mkdir -p {ROOT}
base64 -d > {ROOT}/runtime.py << 'END'
{base64.b64encode(runtime).decode()}
END
base64 -d > /tmp/lumen-speech-jobs.json << 'END'
{base64.b64encode(payload).decode()}
END
export HF_HOME={ROOT}/hf
export HF_HUB_OFFLINE=1
{PYTHON} {ROOT}/runtime.py /tmp/lumen-speech-jobs.json {MODEL_DIR}
'''
    done = _ssh(ip, port, script, timeout=900)
    if 'SPEECH_DONE' not in done:
        raise _note_failure(RuntimeError('hypit_unavailable'), (done or 'speech did not finish')[-500:])


def json_bytes(specs):
    import json
    return json.dumps(specs, ensure_ascii=False).encode()


def _pull(ip, port, remote, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    wav = destination.with_suffix('.wav')
    try:
        with wav.open('wb') as out:
            subprocess.run(
                _ssh_argv(ip, port) + ['cat ' + shlex.quote(remote)],
                check=True, timeout=180, stdout=out, stderr=subprocess.PIPE,
            )
    except subprocess.CalledProcessError as exc:
        detail = ((exc.stderr or b'').decode('utf-8', 'replace')[-240:]).strip()
        wav.unlink(missing_ok=True)
        raise _note_failure(RuntimeError('hypit_unavailable'), 'speech copy failed ' + detail) from exc
    except subprocess.TimeoutExpired as exc:
        wav.unlink(missing_ok=True)
        raise _note_failure(RuntimeError('hypit_unavailable'), 'speech copy timed out') from exc
    if wav.stat().st_size < 1000:
        wav.unlink(missing_ok=True)
        raise ValueError('dubbing_audio_invalid')
    from .media import ffmpeg
    from .music import probe_audio
    ffmpeg('-i', wav, '-vn', '-c:a', 'libmp3lame', '-q:a', '2', destination)
    wav.unlink(missing_ok=True)
    probed = probe_audio(destination)
    if not probed.get('duration') or float(probed['duration']) < 0.2:
        destination.unlink(missing_ok=True)
        raise ValueError('dubbing_audio_invalid')
    log.info('speech wrote %s', destination.name)
