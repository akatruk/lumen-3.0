"""Film one Hypit workspace on the pinned RunPod GPU pod.

The worker sets LUMEN_HYPIT_GPU=1. Tests leave it unset and keep the software
profile on this machine. Production resumes only LUMEN_GPU_POD_ID (default
dznvwn90el5au4 / lumen-hypit-4090). Never terminate an existing pod and never
create a new one. Speech uses the same pod. lumen-web-gpu is left alone.
"""
import contextvars
import fcntl
import json
import logging
import os
import shlex
import subprocess
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from .hypit_picture import LOCAL_RENDER_TIMEOUT_S, _note_failure

log = logging.getLogger('lumen.hypit')

VOLUME_ID = 'spsiypcy8y'
POD_NAME = 'lumen-hypit-4090'
# Surviving pin after terminate+redeploy destroyed sovtlhobiu7wvt (2026-10-12).
DEFAULT_POD_ID = 'dznvwn90el5au4'
FORBIDDEN_POD_IDS = frozenset({'hufsgfs9f7gpga'})
CHROME_LIBS = (
    'libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 '
    'libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 '
    'libasound2t64 libpango-1.0-0 libcairo2 libx11-6 libx11-xcb1 libxcb1 '
    'libxext6 fonts-noto-cjk'
)


_pod = contextvars.ContextVar('lumen_gpu_pod', default=None)


def _pinned_pod_id():
    raw = (os.environ.get('LUMEN_GPU_POD_ID') or DEFAULT_POD_ID).strip()
    if not raw:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'LUMEN_GPU_POD_ID is empty')
    if raw in FORBIDDEN_POD_IDS:
        raise _note_failure(RuntimeError('hypit_unavailable'), f'gpu pod {raw} is forbidden')
    return raw


@contextmanager
def pod_session():
    """Resume the pinned Hypit pod, or reuse the holder already running in this process.

    The pod stops when the outermost holder exits. A nested speech call does
    not shut the machine down in the middle of a picture. Never terminates or
    creates pods.
    """
    current = _pod.get()
    if current is not None:
        yield current
        return
    from .config import settings
    lock_path = Path(settings.data_dir) / 'gpu' / 'session.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = lock_path.open('a+')
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        pinned = _find_pinned(_pods())
        already = bool(pinned and pinned.get('desiredStatus') not in ('EXITED', 'TERMINATED'))
        ip, port, pod_id = _ensure_pod()
        token = _pod.set((ip, port, pod_id))
        try:
            yield ip, port, pod_id
        finally:
            _pod.reset(token)
            if not already:
                _stop_pod(pod_id)
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()


def film(work):
    """Capture work/visual.mp4 on the pinned Hypit pod. Speech uses that same pod."""
    work = Path(work)
    _hardware_runtime(work)
    try:
        from . import runpod_llm

        runpod_llm.unload_model()
    except Exception:
        pass
    ip = port = None
    try:
        with pod_session() as (ip, port, _pod_id):
            _prepare_machine(ip, port)
            _sync(work, ip, port)
            _capture(ip, port)
            return _fetch(work, ip, port)
    except RuntimeError as exc:
        extra = _tail_logs(ip, port) if ip and port else ''
        if extra:
            try:
                Path('/tmp/lumen-gpu-extra.txt').write_text(extra)
            except OSError:
                pass
            log.warning('gpu program log: %s', extra[-4000:])
        detail = getattr(exc, 'hypit_detail', '') or ''
        try:
            Path('/tmp/lumen-gpu-detail.txt').write_text(detail)
        except OSError:
            pass
        log.warning('gpu capture failed: %s', detail[-2000:])
        raise
    except Exception as exc:
        raise _note_failure(RuntimeError('hypit_unavailable'), f'{type(exc).__name__}: {exc}') from exc


def _hardware_runtime(work):
    profile = {
        'format': 'hypit.runtime-local@1',
        'dataRoot': '.hypit/runtimes/local',
        'credentials': {'platform': {'use': '@hypit/credential-store-platform'}},
        'endpoints': {
            'media.local': {'use': '@hypit/provider-media-local'},
            'hyperframes.local': {
                'use': '@hypit/provider-hyperframes-local',
                'config': {
                    'workers': 1,
                    'browserGpu': 'hardware',
                    'chromePath': '/opt/chrome/chrome-headless-shell',
                    'processTimeoutMs': LOCAL_RENDER_TIMEOUT_S * 1000,
                    'maxDecodedSourceBytes': 512 * 1024 * 1024,
                    'maxPendingFrameBytes': 128 * 1024 * 1024,
                },
            },
            'whisperx.local': {
                'use': '@hypit/provider-whisperx-local',
                'config': {'alignmentLanguages': ['zh', 'en', 'ru']},
            },
        },
        'bindings': {'@hypit/whisperx@1#whisperx-alignment': 'whisperx.local'},
    }
    path = Path(work) / 'hypit.runtime.json'
    path.write_text(json.dumps(profile))
    return path


def _key_path():
    from .config import settings
    raw = os.environ.get('LUMEN_GPU_SSH_KEY')
    path = Path(raw) if raw else Path(settings.data_dir) / 'gpu' / 'id_ed25519'
    if not path.is_file():
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu ssh key is missing')
    return path


def _ssh_argv(ip, port):
    key = _key_path()
    known = key.parent / 'known_hosts'
    return [
        'ssh', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'StrictHostKeyChecking=accept-new',
        '-o', 'UserKnownHostsFile=' + str(known),
        '-o', 'ConnectTimeout=20', '-o', 'ServerAliveInterval=30',
        '-o', 'ServerAliveCountMax=240',
        '-i', str(key), '-p', str(port), f'root@{ip}',
    ]


def _ssh(ip, port, script, timeout):
    # The script is a file. bash -s would leave the script on stdin, and ffmpeg
    # or apt would eat the lines after the current command.
    remote = "bash -c 'cat >/tmp/lumen-capture.sh && bash /tmp/lumen-capture.sh </dev/null'"
    try:
        completed = subprocess.run(
            _ssh_argv(ip, port) + [remote],
            input=script, check=False, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace',
        )
    except subprocess.TimeoutExpired as exc:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu capture timed out') from exc
    if completed.returncode != 0:
        detail = ((completed.stdout or '') + '\n' + (completed.stderr or '')).strip()[-2500:] or 'gpu ssh failed'
        raise _note_failure(RuntimeError('hypit_unavailable'), detail)
    return completed.stdout


def _tail_logs(ip, port):
    remote = (
        "bash -c 'echo ---BUILD---; tail -n 40 /opt/lumen-web-job/build.jsonl 2>/dev/null; "
        "echo ---DMESG---; dmesg -T 2>/dev/null | tail -n 20; "
        "echo ---PROG---; tail -n 40 /opt/hypit-home/.local/state/hypit/programs/*/program.log "
        "/opt/hypit-home/.local/state/hypit/programs/*/install.log 2>/dev/null'"
    )
    try:
        completed = subprocess.run(
            _ssh_argv(ip, port) + [remote],
            check=False, timeout=30,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace',
        )
    except (subprocess.TimeoutExpired, OSError):
        return ''
    return (completed.stdout or '').strip()


def _gql(query, variables=None):
    token = os.environ.get('RUNPOD_API_KEY') or ''
    if not token:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu api key is missing')
    body = json.dumps({'query': query, 'variables': variables or {}}).encode()
    request = urllib.request.Request(
        'https://api.runpod.io/graphql?api_key=' + token,
        data=body,
        headers={'Content-Type': 'application/json', 'User-Agent': 'lumen-ops'},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:
        raise _note_failure(RuntimeError('hypit_unavailable'), f'gpu api: {type(exc).__name__}') from exc
    if payload.get('errors'):
        message = '; '.join(str(item.get('message') or item) for item in payload['errors'])
        raise _note_failure(RuntimeError('hypit_unavailable'), message[:500])
    return payload.get('data') or {}


def _pods():
    data = _gql('query { myself { pods { id name desiredStatus runtime { ports { ip isIpPublic privatePort publicPort } } } } }')
    return ((data.get('myself') or {}).get('pods')) or []


def _find_pinned(pods):
    """Return the allowlisted Hypit pod only. Never touch forbidden ids."""
    pinned_id = _pinned_pod_id()
    match = next((pod for pod in pods if pod.get('id') == pinned_id), None)
    if not match:
        return None
    if match.get('id') in FORBIDDEN_POD_IDS:
        raise _note_failure(RuntimeError('hypit_unavailable'), f'gpu pod {match.get("id")} is forbidden')
    name = match.get('name') or ''
    if name and name != POD_NAME:
        raise _note_failure(
            RuntimeError('hypit_unavailable'),
            f'gpu pod {pinned_id} name mismatch: want {POD_NAME}, got {name}',
        )
    return match


def _ssh_endpoint(pod):
    for item in ((pod.get('runtime') or {}).get('ports')) or []:
        if item.get('isIpPublic') and item.get('privatePort') == 22 and item.get('ip') and item.get('publicPort'):
            return item['ip'], int(item['publicPort'])
    return None


def _gpu_busy(exc):
    detail = str(getattr(exc, 'hypit_detail', ''))
    return (
        'not enough free GPUs' in detail
        or 'no longer any instances' in detail
        or 'no gpu free' in detail
        or 'Something went wrong' in detail
        or 'try again later' in detail
    )


def _ensure_pod():
    """Resume the pinned pod only. Wait while the host has no free card; never create."""
    last = None
    for _attempt in range(40):
        try:
            return _start_pod()
        except RuntimeError as exc:
            last = exc
            if not _gpu_busy(exc):
                raise
            time.sleep(30)
    raise last


def _start_pod():
    """Resume or attach the pinned pod. Never terminate. Never deploy on demand."""
    pinned_id = _pinned_pod_id()
    match = _find_pinned(_pods())
    if not match:
        raise _note_failure(
            RuntimeError('hypit_unavailable'),
            f'pinned gpu pod {pinned_id} not found; refuse create/terminate',
        )
    status = match.get('desiredStatus')
    if status not in ('EXITED', 'TERMINATED') and status:
        return _wait_ready(match['id'])
    if status == 'TERMINATED':
        raise _note_failure(
            RuntimeError('hypit_unavailable'),
            f'pinned gpu pod {pinned_id} is TERMINATED; refuse create',
        )
    if status != 'EXITED':
        raise _note_failure(
            RuntimeError('hypit_unavailable'),
            f'pinned gpu pod {pinned_id} status {status!r}; refuse create/terminate',
        )
    # Resume only. Capacity errors bubble to _ensure_pod for wait/retry.
    # Never terminate or deploy-on-demand — fail closed instead.
    _gql(
        'mutation($id: String!) { podResume(input: { podId: $id, gpuCount: 1 }) { id } }',
        {'id': pinned_id},
    )
    return _wait_ready(pinned_id)


def _wait_ready(pod_id):
    deadline = time.time() + 360
    while time.time() < deadline:
        match = next((pod for pod in _pods() if pod.get('id') == pod_id), None)
        if match and match.get('id') in FORBIDDEN_POD_IDS:
            raise _note_failure(RuntimeError('hypit_unavailable'), f'gpu pod {pod_id} is forbidden')
        endpoint = _ssh_endpoint(match) if match else None
        if endpoint and match.get('desiredStatus') == 'RUNNING':
            _wait_ssh(*endpoint)
            return endpoint[0], endpoint[1], pod_id
        time.sleep(10)
    raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu pod did not open ssh')


def _wait_ssh(ip, port):
    deadline = time.time() + 180
    last = ''
    while time.time() < deadline:
        try:
            _ssh(ip, port, 'echo ready\n', timeout=30)
            return
        except RuntimeError as exc:
            last = getattr(exc, 'hypit_detail', '') or last
            time.sleep(8)
    raise _note_failure(RuntimeError('hypit_unavailable'), last or 'gpu ssh was not ready')


def _stop_pod(pod_id):
    try:
        _gql('mutation($id: String!) { podStop(input: { podId: $id }) { id desiredStatus } }', {'id': pod_id})
        log.info('gpu pod %s stopped', pod_id)
    except Exception as exc:
        log.warning('gpu pod %s stayed up: %s', pod_id, type(exc).__name__)


def _prepare_machine(ip, port):
    probe = _ssh(ip, port, _BOOTSTRAP, timeout=900)
    if 'NEED_RUNTIME' not in probe:
        return
    key = _key_path()
    known = key.parent / 'known_hosts'
    remote = ' '.join(shlex.quote(part) for part in _ssh_argv(ip, port))
    copy = (
        "tar -C / -cf - opt/hypit usr/local/bin/node usr/local/bin/npm "
        "usr/local/bin/npx usr/local/bin/corepack usr/local/lib/node_modules "
        "opt/lumen-rebuild/.cache/hyperframes/chrome | "
        f"{remote} 'cat > /workspace/lumen-runtime.tar'"
    )
    try:
        subprocess.run(copy, shell=True, check=True, timeout=1800)
    except subprocess.CalledProcessError as exc:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu runtime copy failed') from exc
    except subprocess.TimeoutExpired as exc:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu runtime copy timed out') from exc
    ready = _ssh(ip, port, _BOOTSTRAP, timeout=900)
    if 'NEED_RUNTIME' in ready or 'CHROME_MISSING' in ready:
        raise _note_failure(RuntimeError('hypit_unavailable'), ready[-500:])


_BOOTSTRAP = f'''
set -eu
if ! findmnt /workspace >/dev/null 2>&1 && ! grep -q ' /workspace ' /proc/mounts; then
  echo WORKSPACE_NOT_MOUNTED
  exit 43
fi
if [ ! -x /opt/hypit/bin/hypit.mjs ] || [ ! -x /usr/local/bin/node ] || [ ! -x /usr/local/bin/npm ]; then
  if [ ! -f /workspace/lumen-runtime.tar ]; then
    echo NEED_RUNTIME
    exit 0
  fi
  tar -C / --no-same-owner -xf /workspace/lumen-runtime.tar
fi
if [ ! -x /usr/local/bin/npm ]; then
  rm -f /workspace/lumen-runtime.tar
  echo NEED_RUNTIME
  exit 0
fi
if [ ! -x /opt/chrome/chrome-headless-shell ]; then
  found=$(find /opt/lumen-rebuild/.cache/hyperframes/chrome -type f -name chrome-headless-shell | head -1)
  if [ -z "$found" ]; then echo CHROME_MISSING; exit 44; fi
  mkdir -p /opt/chrome
  ln -sfn "$found" /opt/chrome/chrome-headless-shell
fi
if ! /opt/chrome/chrome-headless-shell --version >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq {CHROME_LIBS}
fi
/opt/chrome/chrome-headless-shell --version
echo RUNTIME_READY
'''


def _sync(work, ip, port):
    remote = ' '.join(shlex.quote(part) for part in _ssh_argv(ip, port))
    script = (
        f"tar -C {shlex.quote(str(work))} -cf - --exclude .hypit --exclude visual.mp4 . | "
        f"{remote} 'rm -rf /opt/lumen-web-job && mkdir -p /opt/lumen-web-job && tar -C /opt/lumen-web-job --no-same-owner -xf -'"
    )
    try:
        subprocess.run(script, shell=True, check=True, timeout=600)
    except subprocess.CalledProcessError as exc:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu workspace copy failed') from exc


def _capture(ip, port):
    _ssh(ip, port, _CAPTURE, timeout=LOCAL_RENDER_TIMEOUT_S)


_CAPTURE = r'''
set -eu
export HOME=/opt/hypit-home
export HF_HOME=/opt/hypit-home/.cache/huggingface
export UV_CACHE_DIR=/opt/hypit-home/.cache/uv
export XDG_CACHE_HOME=/opt/hypit-home/.cache
export NODE_OPTIONS=--max-old-space-size=16384
export HYPIT_ROOT=/opt/hypit
export PATH=/usr/local/bin:$PATH
mkdir -p "$HOME"
rm -f /workspace/lumen-picture.mp4
cd /opt/lumen-web-job
HYPIT="$HYPIT_ROOT/bin/hypit.mjs"
PROFILE="$PWD/hypit.runtime.json"
python3 ./hypit_figures.py /opt/lumen-web-job
node "$HYPIT" runtime use "$PROFILE" --workspace /opt/lumen-web-job
node "$HYPIT" programs up --runtime "$PROFILE" --max-wait-ms 2700000 --workspace /opt/lumen-web-job || {
  echo PROGRAM_LOG >&2
  tail -n 100 /opt/hypit-home/.local/state/hypit/programs/*/program.log >&2 || true
  exit 1
}
node "$HYPIT" build build.svrun --follow --json --workspace /opt/lumen-web-job > /opt/lumen-web-job/build.jsonl || {
  echo BUILD_LOG >&2
  tail -n 80 /opt/lumen-web-job/build.jsonl >&2 || true
  exit 1
}
python3 - <<'PY'
import json, sys
text = open('/opt/lumen-web-job/build.jsonl', errors='replace').read()
decoder = json.JSONDecoder()
found = None
for index, char in enumerate(text):
    if char != '{':
        continue
    try:
        payload, _end = decoder.raw_decode(text[index:])
    except json.JSONDecodeError:
        continue
    if isinstance(payload, dict) and payload.get('format') == 'hypit.cli-build@1':
        found = payload
if not found or not (found.get('build') or {}).get('id'):
    sys.stderr.write(text[-2000:])
    sys.exit(2)
work = (found.get('build') or {}).get('work') or {}
if work.get('outcome') == 'failed' or work.get('state') == 'failed':
    sys.stderr.write(text[-2000:])
    sys.exit(3)
open('/opt/lumen-web-job/build.id', 'w').write(found['build']['id'])
PY
build_id=$(cat /opt/lumen-web-job/build.id)
node /opt/hypit/bin/hypit.mjs get "$build_id" --output final.video --to /opt/lumen-web-job/visual.mp4 --workspace /opt/lumen-web-job
if [ ! -f /opt/lumen-web-job/visual.mp4 ] || [ ! -s /opt/lumen-web-job/visual.mp4 ]; then
  echo PICTURE_MISSING >&2
  ls -la /opt/lumen-web-job >&2 || true
  exit 1
fi
# The next SSH can miss /opt/lumen-web-job. The volume keeps the finished file.
cp -f /opt/lumen-web-job/visual.mp4 /workspace/lumen-picture.mp4
test -s /workspace/lumen-picture.mp4
'''


def _fetch(work, ip, port):
    visual = Path(work) / 'visual.mp4'
    last = ''
    for attempt in range(3):
        try:
            with visual.open('wb') as out:
                subprocess.run(
                    _ssh_argv(ip, port) + [
                        'if [ -s /workspace/lumen-picture.mp4 ]; then cat /workspace/lumen-picture.mp4; '
                        'else cat /opt/lumen-web-job/visual.mp4; fi'
                    ],
                    check=True, timeout=600, stdout=out, stderr=subprocess.PIPE,
                )
            break
        except subprocess.CalledProcessError as exc:
            last = ((exc.stderr or b'').decode('utf-8', 'replace')[-240:]).strip()
            visual.unlink(missing_ok=True)
            if attempt == 2:
                raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu picture copy failed ' + last) from exc
            time.sleep(6)
        except subprocess.TimeoutExpired as exc:
            visual.unlink(missing_ok=True)
            raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu picture copy timed out') from exc
    if not visual.is_file() or visual.stat().st_size < 32:
        raise _note_failure(RuntimeError('hypit_unavailable'), 'gpu picture was empty')
    return visual
