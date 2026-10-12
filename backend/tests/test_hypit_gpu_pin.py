"""Pinned Hypit pod: resume only. Never terminate or deploy on demand."""
from __future__ import annotations

import pytest

from backend.hypit_picture import _note_failure


PINNED = 'dznvwn90el5au4'
FORBIDDEN = 'hufsgfs9f7gpga'


def _exited_pod(pod_id=PINNED, name='lumen-hypit-4090'):
    return {'id': pod_id, 'name': name, 'desiredStatus': 'EXITED', 'runtime': {'ports': []}}


def _running_pod(pod_id=PINNED, name='lumen-hypit-4090'):
    return {
        'id': pod_id,
        'name': name,
        'desiredStatus': 'RUNNING',
        'runtime': {
            'ports': [{'ip': '1.2.3.4', 'isIpPublic': True, 'privatePort': 22, 'publicPort': 2222}],
        },
    }


def test_pinned_id_prefers_env(monkeypatch):
    from backend import hypit_gpu

    monkeypatch.setenv('LUMEN_GPU_POD_ID', 'abc123pin')
    assert hypit_gpu._pinned_pod_id() == 'abc123pin'
    monkeypatch.delenv('LUMEN_GPU_POD_ID', raising=False)
    assert hypit_gpu._pinned_pod_id() == hypit_gpu.DEFAULT_POD_ID


def test_forbidden_pin_refused(monkeypatch):
    from backend import hypit_gpu

    monkeypatch.setenv('LUMEN_GPU_POD_ID', FORBIDDEN)
    with pytest.raises(RuntimeError, match='hypit_unavailable') as caught:
        hypit_gpu._pinned_pod_id()
    assert 'forbidden' in (caught.value.hypit_detail or '')


def test_resume_busy_never_terminates_or_creates(monkeypatch):
    """GPU-busy resume must fail closed — the old terminate+create path is gone."""
    from backend import hypit_gpu

    monkeypatch.setenv('LUMEN_GPU_POD_ID', PINNED)
    mutations = []

    def fake_pods():
        return [_exited_pod(), {'id': FORBIDDEN, 'name': 'lumen-web-gpu', 'desiredStatus': 'EXITED'}]

    def fake_gql(query, variables=None):
        mutations.append((query, variables))
        if 'podResume' in query:
            busy = RuntimeError('hypit_unavailable')
            raise _note_failure(busy, 'not enough free GPUs on host machine to start this pod')
        raise AssertionError(f'unexpected gql: {query}')

    monkeypatch.setattr(hypit_gpu, '_pods', fake_pods)
    monkeypatch.setattr(hypit_gpu, '_gql', fake_gql)

    with pytest.raises(RuntimeError, match='hypit_unavailable') as caught:
        hypit_gpu._start_pod()

    assert hypit_gpu._gpu_busy(caught.value) is True
    joined = '\n'.join(q for q, _ in mutations)
    assert 'podResume' in joined
    assert 'podTerminate' not in joined
    assert 'podFindAndDeployOnDemand' not in joined
    src = open(hypit_gpu.__file__).read()
    assert 'podTerminate' not in src
    assert 'podFindAndDeployOnDemand' not in src
    assert 'PodFindAndDeployOnDemandInput' not in src


def test_missing_pinned_pod_refuses_create(monkeypatch):
    from backend import hypit_gpu

    monkeypatch.setenv('LUMEN_GPU_POD_ID', PINNED)
    monkeypatch.setattr(hypit_gpu, '_pods', lambda: [{'id': FORBIDDEN, 'name': 'lumen-web-gpu', 'desiredStatus': 'EXITED'}])
    calls = []

    def fake_gql(query, variables=None):
        calls.append(query)
        raise AssertionError('must not call RunPod mutate when pin missing')

    monkeypatch.setattr(hypit_gpu, '_gql', fake_gql)

    with pytest.raises(RuntimeError, match='hypit_unavailable') as caught:
        hypit_gpu._start_pod()
    assert 'not found' in (caught.value.hypit_detail or '')
    assert 'refuse create' in (caught.value.hypit_detail or '')
    assert calls == []


def test_running_pinned_pod_waits_ready(monkeypatch):
    from backend import hypit_gpu

    monkeypatch.setenv('LUMEN_GPU_POD_ID', PINNED)
    monkeypatch.setattr(hypit_gpu, '_pods', lambda: [_running_pod()])
    monkeypatch.setattr(hypit_gpu, '_wait_ready', lambda pod_id: ('1.2.3.4', 2222, pod_id))
    calls = []
    monkeypatch.setattr(hypit_gpu, '_gql', lambda *a, **k: calls.append(a) or {})

    assert hypit_gpu._start_pod() == ('1.2.3.4', 2222, PINNED)
    assert calls == []


def test_name_only_match_does_not_select_unpinned(monkeypatch):
    """A same-name orphan must not be used; pin is by id."""
    from backend import hypit_gpu

    monkeypatch.setenv('LUMEN_GPU_POD_ID', PINNED)
    orphan = _exited_pod(pod_id='orphan999', name='lumen-hypit-4090')
    monkeypatch.setattr(hypit_gpu, '_pods', lambda: [orphan])
    with pytest.raises(RuntimeError, match='hypit_unavailable') as caught:
        hypit_gpu._start_pod()
    assert PINNED in (caught.value.hypit_detail or '')
