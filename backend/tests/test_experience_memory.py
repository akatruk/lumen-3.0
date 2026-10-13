"""Experience memory against a real PostgreSQL database with pgvector."""
import json
import os
import shutil
import subprocess
import uuid

import pytest

from backend.config import settings
from backend.database import connect
from backend.db import init_db
from backend.experience_memory import (
    PREAMBLE,
    add_asset_feedback,
    add_decision,
    add_engineering_memory,
    add_incident,
    add_review,
    add_scene_feedback,
    attach_to_visual_plan,
    bounded_context,
    context_for_transcript,
    prompt_addon,
    redact,
    remember_generation,
    status,
    store_asset_embedding,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get('LUMEN_TEST_POSTGRES_URL'),
    reason='requires LUMEN_TEST_POSTGRES_URL (lumen_qa)',
)


def _axis(index):
    values = [0.0] * 512
    values[index] = 1.0
    return values


def _ready():
    init_db()
    info = status()
    if not info.get('pgvector'):
        pytest.fail('pgvector extension is not installed in lumen_qa')
    return info


def test_redact_strips_urls_and_secrets():
    text = redact('failed postgres://lumen:secret@db/lumen password=hunter2')
    assert 'hunter2' not in text
    assert 'secret@' not in text
    assert '<redacted>' in text


def test_migration_is_idempotent_and_pgvector_visible():
    info = _ready()
    again = _ready()
    assert info['pgvector']
    assert info['migration'] == '002_media_embeddings'
    assert again['migration'] == '002_media_embeddings'
    with connect() as db:
        db.execute('SELECT frame_seconds, embedding_model FROM asset_embeddings LIMIT 0')
        db.execute('SELECT asset_id, embedding_version, created_at, embedding FROM media_embeddings LIMIT 0')
    assert info['counts']['engineering_memory'] == 0
    with connect() as db:
        row = db.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
    assert row['extversion'] == info['pgvector']


def test_memory_write_read_and_separate_ratings():
    _ready()
    project_id = 'proj_' + uuid.uuid4().hex
    memory_id = add_engineering_memory(
        project_id=project_id, title='Growth treatment', body='Use an upward arrow for profit.',
        embedding=_axis(0),
    )
    decision_id = add_decision(
        project_id=project_id, title='Keep source numbers', body='Spoken counts stay on screen.', status='active',
    )
    incident_id = add_incident(
        project_id=project_id, summary='Invented shareholder count', defect='Card said 2 shareholders',
        resolution='Bind the card to the spoken fact', status='resolved',
    )
    generation_id = 'gen_' + uuid.uuid4().hex
    remember_generation(project_id=project_id, generation_id=generation_id, plan={
        'scenes': [{
            'sceneId': 'proof',
            'query': 'profit arrow',
            'semanticPurpose': 'growth',
            'speaker': {'layout': 'speaker_split_left'},
            'background': {'assetId': 'pm_hero_growth_001', 'treatment': 'rise'},
        }],
    })
    user_id = add_review(
        project_id=project_id, generation_id=generation_id, review_source='user',
        user_quality_rating=5, comments='Arrow reads clearly', defects=['tight crop'], fixes='Inset the arrow',
    )
    qa_id = add_review(
        project_id=project_id, generation_id=generation_id, review_source='automated',
        automated_qa_score=91, comments='caption contrast passed',
    )
    with pytest.raises(Exception):
        add_review(
            project_id=project_id, generation_id=generation_id, review_source='user',
            user_quality_rating=4, automated_qa_score=10,
        )
    scene_id = add_scene_feedback(
        project_id=project_id, generation_id=generation_id, scene_index=0, review_source='user',
        layout='speaker_split_left', treatment='rise', user_quality_rating=5, comments='kept',
    )
    with connect() as db:
        user = db.execute('SELECT * FROM generation_reviews WHERE id=?', (user_id,)).fetchone()
        qa = db.execute('SELECT * FROM generation_reviews WHERE id=?', (qa_id,)).fetchone()
        history = db.execute('SELECT * FROM generation_history WHERE id=?', (generation_id,)).fetchone()
        assert db.execute('SELECT id FROM engineering_memory WHERE id=?', (memory_id,)).fetchone()
        assert db.execute('SELECT id FROM architecture_decisions WHERE id=?', (decision_id,)).fetchone()
        assert db.execute('SELECT id FROM incidents WHERE id=?', (incident_id,)).fetchone()
        assert db.execute('SELECT id FROM scene_feedback WHERE id=?', (scene_id,)).fetchone()
    assert user['review_source'] == 'user' and user['user_quality_rating'] == 5 and user['automated_qa_score'] is None
    assert qa['review_source'] == 'automated' and qa['automated_qa_score'] == 91 and qa['user_quality_rating'] is None
    assert json.loads(history['selected_assets']) == ['pm_hero_growth_001']
    assert history['director_version'] == 'v11.2'
    assert history['prompt_version'] == 'experience-context-v1'


def test_project_isolation_and_bounded_retrieval():
    _ready()
    project_a = 'a_' + uuid.uuid4().hex
    project_b = 'b_' + uuid.uuid4().hex
    add_engineering_memory(
        project_id=project_a, title='Profit arrow', body='Rising profit uses an arrow moving up.',
        domain='investment', embedding=_axis(0),
    )
    secret = 'project-b-private-passport-defect-' + uuid.uuid4().hex
    add_engineering_memory(
        project_id=project_b, title='Passport defect', body=secret,
        domain='immigration', embedding=_axis(0),
    )
    context = bounded_context(project_a, 'profit', domain='investment', query_embedding=_axis(0))
    blob = json.dumps(context, ensure_ascii=False)
    assert secret not in blob
    assert context['overridesSourceFacts'] is False
    assert context['overridesSafetyRules'] is False
    assert len(context['items']) <= 8
    assert len(blob) <= 3500
    assert any(item['kind'] == 'engineering_memory' for item in context['items'])
    assert all(item['untrusted'] is True for item in context['items'])


def test_director_memory_does_not_rewrite_scenes(monkeypatch):
    _ready()
    monkeypatch.setattr(settings, 'visual_experience_memory_enabled', False)
    plan = {
        'generationId': 'gen_keep',
        'language': 'ru',
        'scenes': [{'sceneId': 'hook', 'query': 'прибыль', 'speaker': {'layout': 'speaker_fullscreen'}}],
    }
    assert attach_to_visual_plan(plan, 'proj') is plan
    assert context_for_transcript('proj', [{'text': 'прибыль'}]) is None
    monkeypatch.setattr(settings, 'visual_experience_memory_enabled', True)
    project_id = 'dir_' + uuid.uuid4().hex
    add_engineering_memory(
        project_id=project_id, title='Arrow', body='Profit growth is an arrow moving up.',
        embedding=_axis(3),
    )
    attached = attach_to_visual_plan(dict(plan), project_id)
    assert attached['scenes'] == plan['scenes']
    memory = attached['experienceMemory']
    assert memory['overridesSourceFacts'] is False
    assert memory['overridesSafetyRules'] is False
    assert 'source transcript facts' in memory['preamble']
    addon = prompt_addon({
        'items': [{
            'kind': 'incidents',
            'id': 'inc',
            'score': 0.91,
            'summary': 'keep the spoken shareholder count',
            'untrusted': True,
        }],
    })
    assert 'ADVISORY EXPERIENCE MEMORY' in addon
    assert PREAMBLE in addon
    assert 'keep the spoken shareholder count' in addon
    assert len(addon) <= 3500


def test_asset_modality_metadata_and_library_scope():
    _ready()
    from backend.experience_embeddings import content_hash
    spec = {
        'embedding': _axis(4),
        'embedding_model': settings.experience_image_model,
        'model_version': 'clip-vit-b-32',
        'vector_dimension': 512,
        'modality': 'image',
        'content_hash': content_hash(b'image-bytes'),
    }
    store_asset_embedding(asset_id='pm_hero_growth_001', modality='image', spec=spec, scope='library')
    with pytest.raises(Exception):
        store_asset_embedding(asset_id='bad', modality='image', spec={**spec, 'embedding_model': settings.experience_text_model, 'modality': 'image'})
    with connect() as db:
        row = db.execute(
            "SELECT embedding_model, vector_dimension, content_hash, scope FROM asset_embeddings WHERE asset_id=?",
            ('pm_hero_growth_001',),
        ).fetchone()
    assert row['embedding_model'] == 'sentence-transformers/clip-ViT-B-32'
    assert row['vector_dimension'] == 512
    assert row['scope'] == 'library'
    assert row['content_hash'] == spec['content_hash']


def test_dump_and_restore_roundtrip(tmp_path):
    _ready()
    project_id = 'bak_' + uuid.uuid4().hex
    marker = 'backup-marker-' + uuid.uuid4().hex
    add_engineering_memory(project_id=project_id, title='Backup', body=marker, embedding=_axis(5))
    with connect() as db:
        schema = db.execute('SELECT current_schema() AS name').fetchone()['name']
    if not shutil.which('pg_dump') or not shutil.which('pg_restore'):
        pytest.fail('pg_dump and pg_restore are required')
    dump = tmp_path / 'memory.dump'
    url = os.environ['LUMEN_TEST_POSTGRES_URL']
    subprocess.run(
        ['pg_dump', '--dbname', url, '--schema', schema, '--table', f'{schema}.engineering_memory',
         '--format', 'custom', '--file', str(dump)],
        check=True, capture_output=True,
    )
    assert dump.stat().st_size > 0
    with connect() as db:
        db.execute('DELETE FROM engineering_memory WHERE project_id=?', (project_id,))
        assert db.execute('SELECT 1 FROM engineering_memory WHERE project_id=?', (project_id,)).fetchone() is None
    restored = subprocess.run(
        ['pg_restore', '--data-only', '--no-owner', '--dbname', url, str(dump)],
        capture_output=True,
    )
    assert restored.returncode in (0, 1), restored.stderr[-400:]
    with connect() as db:
        row = db.execute('SELECT body FROM engineering_memory WHERE project_id=?', (project_id,)).fetchone()
    assert row['body'] == marker
    if not shutil.which('pg_dump'):
        return
    dump = tmp_path / 'memory.dump'
    url = os.environ['LUMEN_TEST_POSTGRES_URL']
    subprocess.run(
        ['pg_dump', '--dbname', url, '--schema', schema, '--format', 'custom', '--file', str(dump)],
        check=True, capture_output=True,
    )
    assert dump.stat().st_size > 0


def test_runpod_prompt_keeps_memory_advisory(monkeypatch):
    captured = {}

    class FakeLLM:
        def require_available(self):
            return None

        def json_call(self, **kwargs):
            captured['prompt'] = kwargs['prompt']
            raise RuntimeError('stop-after-prompt')

    monkeypatch.setattr('backend.runpod_llm.load_model', lambda: None)
    monkeypatch.setattr('backend.runpod_llm.unload_model', lambda: None)
    monkeypatch.setattr('backend.providers.llm.RunPodLLMProvider', lambda: FakeLLM())
    from backend.providers.director import RunPodDirectorProvider
    provider = RunPodDirectorProvider()
    with pytest.raises(RuntimeError, match='stop-after-prompt'):
        provider.build_plan(duration=12, language='en', transcript=[{'text': 'profit'}], experience=None)
    assert 'ADVISORY EXPERIENCE MEMORY' not in captured['prompt']
    experience = {
        'items': [{
            'kind': 'incidents',
            'id': 'inc',
            'score': 0.8,
            'summary': 'Do not invent a shareholder count',
            'untrusted': True,
        }],
    }
    with pytest.raises(RuntimeError, match='stop-after-prompt'):
        provider.build_plan(duration=12, language='en', transcript=[{'text': 'profit'}], experience=experience)
    assert 'ADVISORY EXPERIENCE MEMORY' in captured['prompt']
    assert 'Do not override source transcript facts' in captured['prompt']
    assert 'Do not invent a shareholder count' in captured['prompt']


def test_asset_feedback_keeps_human_and_automated_apart():
    _ready()
    project_id = 'asset_' + uuid.uuid4().hex
    generation_id = 'gen_' + uuid.uuid4().hex
    remember_generation(project_id=project_id, generation_id=generation_id, plan={
        'visualSeed': 42,
        'scenes': [{'sceneId': 'hook', 'query': 'family relocation', 'speaker': {'layout': 'speaker_fullscreen'}}],
    })
    user_id = add_asset_feedback(
        project_id=project_id, asset_id='pm_family', review_source='user',
        user_quality_rating=4, comments='matches the move', issue_category='relevance',
        generation_id=generation_id,
    )
    with pytest.raises(Exception):
        add_asset_feedback(
            project_id=project_id, asset_id='pm_family', review_source='user',
            user_quality_rating=4, automated_qa_score=90,
        )
    with connect() as db:
        row = db.execute('SELECT * FROM asset_feedback WHERE id=?', (user_id,)).fetchone()
        history = db.execute('SELECT visual_seed, model_config FROM generation_history WHERE id=?', (generation_id,)).fetchone()
    assert row['user_quality_rating'] == 4
    assert row['automated_qa_score'] is None
    assert row['issue_category'] == 'relevance'
    assert history['visual_seed'] == '42'
    assert 'clip-ViT-B-32' in history['model_config']


def test_director_context_skips_unapproved_3d(monkeypatch):
    _ready()
    from backend.experience_embeddings import content_hash
    spec = {
        'embedding': _axis(6),
        'embedding_model': settings.experience_image_model,
        'model_version': 'clip-vit-b-32',
        'vector_dimension': 512,
        'modality': 'image',
        'content_hash': content_hash(b'experimental-3d'),
    }
    store_asset_embedding(asset_id='l3d_v2_passport', modality='image', spec=spec, scope='library')
    project_id = 'gate_' + uuid.uuid4().hex
    context = bounded_context(project_id, 'passport', query_embedding=_axis(6))
    assert all(item.get('assetId') != 'l3d_v2_passport' for item in context['items'])
    monkeypatch.setattr(settings, 'visual_experience_memory_enabled', False)
    monkeypatch.setattr(settings, 'visual_intelligence_enabled', False)
    assert context_for_transcript(project_id, [{'text': 'passport'}]) is None
    monkeypatch.setattr(settings, 'visual_intelligence_enabled', True)
    opened = context_for_transcript(project_id, [{'text': 'passport'}], domain='immigration')
    assert opened is not None
    assert opened['overridesSourceFacts'] is False
