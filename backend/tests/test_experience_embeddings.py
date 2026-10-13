"""Multilingual and cross-modal retrieval. Downloads the pinned CLIP models once."""
import os
import uuid

import numpy as np
import pytest

from backend.db import init_db
from backend.experience_embeddings import IMAGE_MODEL_ID, TEXT_MODEL_ID, embed_image, embed_text, embed_video_keyframes
from backend.experience_memory import add_engineering_memory, bounded_context, store_asset_embedding

pytestmark = pytest.mark.skipif(
    not os.environ.get('LUMEN_TEST_POSTGRES_URL'),
    reason='requires LUMEN_TEST_POSTGRES_URL (lumen_qa)',
)

QUERIES = {
    'en-US': 'rising profit arrow on a financial chart',
    'ru-RU': 'стрелка роста прибыли на финансовом графике',
    'zh-CN': '财务图表上的利润上升箭头',
}
DISTRACTOR = {
    'en-US': 'passport stamp and visa document',
    'ru-RU': 'штамп в паспорте и визовый документ',
    'zh-CN': '护照印章和签证文件',
}


def _cosine(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def _models():
    pytest.importorskip('sentence_transformers')
    init_db()
    sample = embed_text('profit')
    assert sample['embedding_model'] == TEXT_MODEL_ID
    assert sample['vector_dimension'] == 512
    return sample


def test_multilingual_queries_retrieve_the_same_memory():
    _models()
    project_id = 'lang_' + uuid.uuid4().hex
    profit_id = add_engineering_memory(
        project_id=project_id,
        title='Profit arrow',
        body='When the host says profit or growth, show an arrow moving up on a financial chart.',
        locale='en-US',
        domain='investment',
    )
    add_engineering_memory(
        project_id=project_id,
        title='Passport stamp',
        body='A passport stamp and visa document for an immigration scene.',
        locale='en-US',
        domain='immigration',
    )
    scores = {}
    for locale, query in QUERIES.items():
        context = bounded_context(project_id, query)
        kinds = [item for item in context['items'] if item['kind'] == 'engineering_memory']
        assert kinds, locale
        assert kinds[0]['id'] == profit_id, (locale, kinds)
        scores[locale] = kinds[0]['score']
        distractor = bounded_context(project_id, DISTRACTOR[locale])
        top = [item for item in distractor['items'] if item['kind'] == 'engineering_memory'][0]
        assert top['id'] != profit_id
    assert min(scores.values()) > 0.2


def test_image_and_video_use_the_clip_vision_encoder(tmp_path):
    _models()
    import cv2
    from PIL import Image

    red = Image.new('RGB', (64, 64), (220, 20, 20))
    blue = Image.new('RGB', (64, 64), (20, 20, 220))
    red_path = tmp_path / 'red.png'
    blue_path = tmp_path / 'blue.png'
    red.save(red_path)
    blue.save(blue_path)
    red_spec = embed_image(red_path)
    blue_spec = embed_image(blue_path)
    assert red_spec['embedding_model'] == IMAGE_MODEL_ID
    assert red_spec['modality'] == 'image'
    assert red_spec['vector_dimension'] == 512
    assert red_spec['embedding_model'] != TEXT_MODEL_ID
    assert _cosine(red_spec['embedding'], red_spec['embedding']) > _cosine(red_spec['embedding'], blue_spec['embedding'])

    video = tmp_path / 'red.avi'
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'MJPG'), 5, (64, 64))
    assert writer.isOpened()
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[:] = (20, 20, 220)  # BGR red
    for _ in range(6):
        writer.write(frame)
    writer.release()
    keyframes = embed_video_keyframes(video, limit=2)
    assert keyframes
    assert {item['modality'] for item in keyframes} == {'video_keyframe'}
    assert {item['embedding_model'] for item in keyframes} == {IMAGE_MODEL_ID}
    assert _cosine(keyframes[0]['embedding'], red_spec['embedding']) > _cosine(keyframes[0]['embedding'], blue_spec['embedding'])

    project_id = 'vis_' + uuid.uuid4().hex
    store_asset_embedding(asset_id='red-square', modality='image', spec=red_spec, project_id=project_id)
    store_asset_embedding(asset_id='red-clip', modality='video_keyframe', spec=keyframes[0], project_id=project_id)
    text = embed_text(QUERIES['en-US'])
    context = bounded_context(project_id, QUERIES['ru-RU'])
    assert context['overridesSourceFacts'] is False
    assert text['embedding_model'] == TEXT_MODEL_ID
