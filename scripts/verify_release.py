#!/usr/bin/env python3
"""Build and verify in an isolated Linux checkout, never in production data.

Requires SSH/SCP, local Chrome + Playwright, and a Linux Python environment with
the project's dependencies, pytest and FFmpeg (including the ASS filter).
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, help='SSH host for isolated Linux verification')
    parser.add_argument('--python', required=True, help='Existing remote Python with test dependencies')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-server-suite', action='store_true', help='Use only for debugging the browser bridge')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    ssh = ['ssh', '-o', 'ConnectTimeout=15', args.host]
    remote_python = shlex.quote(args.python)
    run(['npm', '--prefix', 'frontend', 'run', 'build'], cwd=ROOT)
    run(['npm', '--prefix', 'frontend', 'run', 'test:locale'], cwd=ROOT)
    stage = run(ssh + ['mktemp -d /tmp/lumen-release-check.XXXXXX'], capture_output=True, text=True).stdout.strip()
    assert stage.startswith('/tmp/lumen-release-check.') and '\n' not in stage
    quote_stage = shlex.quote(stage)
    remote_port = int(run(ssh + [remote_python + " -c 'import socket; s=socket.socket(); s.bind((\"127.0.0.1\",0)); print(s.getsockname()[1])'"], capture_output=True, text=True).stdout)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        local_port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{local_port}'
    server = tunnel = None
    with tempfile.TemporaryDirectory(prefix='lumen-release-check-') as temp:
        temp = Path(temp)
        archive = temp / 'source.tgz'
        def include(info):
            parts = Path(info.name).parts
            return None if any(p in ('__pycache__', '.env', '.pytest_cache') or p.startswith('._') for p in parts) else info
        with tarfile.open(archive, 'w:gz') as tar:
            for name in ('backend', 'frontend/dist'):
                tar.add(ROOT / name, arcname=name, filter=include)
        run(['scp', '-q', '-o', 'ConnectTimeout=15', str(archive), args.host + ':' + stage + '/source.tgz'])
        run(ssh + [f'cd {quote_stage} && tar -xzf source.tgz'])
        try:
            if not args.skip_server_suite:
                with (args.output / 'server-tests.log').open('w') as log:
                    run(ssh + [f'cd {quote_stage} && DATABASE_URL= {remote_python} -m pytest backend/tests -q'], stdout=log, stderr=subprocess.STDOUT)
            log = (args.output / 'bridge.log').open('w')
            server = subprocess.Popen(ssh + [f'cd {quote_stage} && DATABASE_URL= LUMEN_ACCEPTANCE_PORT={remote_port} LUMEN_ACCEPTANCE_ORIGIN={shlex.quote(origin)} LUMEN_BROWSER_ACCEPTANCE={quote_stage}/bridge {remote_python} -m pytest backend/tests/test_browser_acceptance.py -q -s'], stdout=log, stderr=subprocess.STDOUT)
            tunnel = subprocess.Popen(['ssh', '-o', 'ConnectTimeout=15', '-o', 'ExitOnForwardFailure=yes', '-N', '-L', f'{local_port}:127.0.0.1:{remote_port}', args.host])
            ready = temp / 'ready.json'
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if server.poll() is not None or tunnel.poll() is not None:
                    raise RuntimeError('Acceptance server or SSH tunnel exited; inspect bridge.log')
                copied = subprocess.run(['scp', '-q', '-o', 'ConnectTimeout=15', args.host + ':' + stage + '/bridge/ready.json', str(ready)], stderr=subprocess.DEVNULL)
                if copied.returncode == 0:
                    ready.chmod(0o600)
                    break
                time.sleep(1)
            else:
                raise TimeoutError('Acceptance server did not become ready')
            env = os.environ | {'WORKSPACE_URL': origin, 'LUMEN_ACCEPTANCE_READY': str(ready),
                                'LUMEN_ACCEPTANCE_REPORT': str(args.output.resolve() / 'browser.json')}
            with (args.output / 'browser.log').open('w') as browser_log:
                result = subprocess.run(['node', 'frontend/tests/real-render.browser.cjs'], cwd=ROOT, env=env, stdout=browser_log, stderr=subprocess.STDOUT)
            report = args.output / 'browser.json'
            if not report.exists():
                report.write_text(json.dumps({'passed': False, 'error': 'Browser process did not produce a report'}))
            run(['scp', '-q', '-o', 'ConnectTimeout=15', str(report), args.host + ':' + stage + '/bridge/done.next.json'])
            run(ssh + [f'mv {quote_stage}/bridge/done.next.json {quote_stage}/bridge/done.json'])
            assert server.wait(timeout=90) == 0, 'Media verification failed; inspect bridge.log'
            assert result.returncode == 0, 'Browser verification failed; inspect browser.log'
            for name in ('verified.json', 'verified-final.mp4'):
                run(['scp', '-q', '-o', 'ConnectTimeout=15', args.host + ':' + stage + '/bridge/' + name, str(args.output / name)])
            print('PASS: real browser → API → worker → MP4 → repeated render → reload → download')
        finally:
            if server and server.poll() is None:
                abort = temp / 'abort.json'
                abort.write_text('{"passed":false,"error":"Acceptance runner aborted"}')
                copied = subprocess.run(['scp', '-q', '-o', 'ConnectTimeout=15', str(abort), args.host + ':' + stage + '/bridge/done.next.json'], stderr=subprocess.DEVNULL)
                if copied.returncode == 0:
                    subprocess.run(ssh + [f'mv {quote_stage}/bridge/done.next.json {quote_stage}/bridge/done.json'])
                try:
                    server.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    server.terminate()
            if tunnel:
                tunnel.terminate()
                tunnel.wait(timeout=10)
            print('Isolated test checkout (no production data):', stage)


if __name__ == '__main__':
    main()
