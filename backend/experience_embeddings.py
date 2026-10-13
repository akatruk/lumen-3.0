"""Pretrained embeddings for experience memory.

Text uses ``sentence-transformers/clip-ViT-B-32-multilingual-v1`` (DistilBERT
aligned into CLIP space; the model card lists ru, en, zh-cn, zh-tw).

Images and video keyframes use the original CLIP vision encoder
``sentence-transformers/clip-ViT-B-32``. A text-only vector is never stored
as an image or keyframe embedding.

Both models emit 512-d vectors in one shared space. Weights are cached on
disk and are not committed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .config import settings

TEXT_MODEL_ID = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'
IMAGE_MODEL_ID = 'sentence-transformers/clip-ViT-B-32'
VECTOR_DIM = 512
TEXT_LANGUAGES = ('ru', 'en', 'zh-cn', 'zh-tw')

_TEXT = None
_IMAGE = None
_VERSIONS: dict[str, str] = {}


class EmbeddingError(RuntimeError):
    pass


def cache_dir() -> Path:
    raw = (settings.experience_embedding_cache or '').strip()
    if raw:
        path = Path(raw)
    else:
        volume = Path('/mnt/volume_nyc1_1791446889637/embedding-models')
        path = volume if volume.parent.is_dir() else settings.data_dir / 'embedding-models'
    path.mkdir(parents=True, exist_ok=True)
    return path


def content_hash(payload: bytes | str) -> str:
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _revision(model, model_id: str) -> str:
    try:
        commit = model[0].auto_model.config._commit_hash
        if commit:
            return str(commit)
    except Exception:
        pass
    snapshots = cache_dir() / f"models--{model_id.replace('/', '--')}" / 'snapshots'
    if snapshots.is_dir():
        names = sorted(path.name for path in snapshots.iterdir() if path.is_dir() and len(path.name) >= 12)
        if names:
            return names[-1]
    return model_id


def _load(model_id: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingError('sentence-transformers is not installed') from exc
    model = SentenceTransformer(model_id, cache_folder=str(cache_dir()), device='cpu')
    _VERSIONS[model_id] = _revision(model, model_id)
    return model


def release_models():
    """Drop CLIP weights after a plan is built so render does not keep them resident."""
    global _TEXT, _IMAGE
    _TEXT = None
    _IMAGE = None
    import gc
    gc.collect()


def text_model():
    global _TEXT
    if _TEXT is None:
        model_id = settings.experience_text_model or TEXT_MODEL_ID
        if model_id != TEXT_MODEL_ID:
            raise EmbeddingError('unsupported text embedding model')
        _TEXT = _load(model_id)
    return _TEXT


def image_model():
    global _IMAGE
    if _IMAGE is None:
        model_id = settings.experience_image_model or IMAGE_MODEL_ID
        if model_id != IMAGE_MODEL_ID:
            raise EmbeddingError('unsupported image embedding model')
        _IMAGE = _load(model_id)
    return _IMAGE


def _as_list(vector) -> list[float]:
    values = [float(v) for v in vector]
    expected = int(settings.experience_vector_dimension or VECTOR_DIM)
    if len(values) != expected:
        raise EmbeddingError(f'vector_dimension:{len(values)}')
    return values


def _rows(vectors, count: int):
    array = vectors
    try:
        import numpy as np
        array = np.asarray(vectors)
        if array.ndim == 1:
            array = array.reshape(1, -1)
    except Exception:
        if count == 1:
            return [vectors]
    if len(array) != count:
        raise EmbeddingError(f'batch_size:{len(array)}')
    return array


def embed_text(text: str) -> dict:
    cleaned = ' '.join((text or '').split())
    if not cleaned:
        raise EmbeddingError('empty_text')
    vector = text_model().encode(cleaned, normalize_embeddings=True, show_progress_bar=False)
    model_id = settings.experience_text_model or TEXT_MODEL_ID
    return {
        'embedding': _as_list(vector),
        'embedding_model': model_id,
        'model_version': _VERSIONS.get(model_id) or model_id,
        'vector_dimension': len(vector),
        'modality': 'text',
        'content_hash': content_hash(cleaned),
    }


def embed_image(path: Path) -> dict:
    from PIL import Image

    file = Path(path)
    raw = file.read_bytes()
    with Image.open(file) as image:
        frame = image.convert('RGB')
        vector = image_model().encode(frame, normalize_embeddings=True, show_progress_bar=False)
    model_id = settings.experience_image_model or IMAGE_MODEL_ID
    return {
        'embedding': _as_list(vector),
        'embedding_model': model_id,
        'model_version': _VERSIONS.get(model_id) or model_id,
        'vector_dimension': len(vector),
        'modality': 'image',
        'content_hash': content_hash(raw),
    }


def sample_video_frames(path: Path, limit: int = 3) -> list[dict]:
    """Read representative frames. Does not write the source file."""
    import cv2
    from PIL import Image

    raw = Path(path).read_bytes()
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise EmbeddingError('video_unreadable')
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        total = 1
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    indexes = sorted({min(total - 1, max(0, int(round(p)))) for p in (
        0, total * 0.5, total - 1)})[:limit]
    frames = []
    try:
        for index in indexes:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            seconds = (index / fps) if fps > 1 else None
            frames.append({
                'image': Image.fromarray(rgb),
                'frame_index': index,
                'frame_seconds': seconds,
                'content_hash': content_hash(raw + f':{index}'.encode()),
            })
    finally:
        capture.release()
    if not frames:
        raise EmbeddingError('video_has_no_frames')
    return frames


def embed_frames(frames: list[dict]) -> list[dict]:
    if not frames:
        return []
    model_id = settings.experience_image_model or IMAGE_MODEL_ID
    vectors = _rows(image_model().encode(
        [frame['image'] for frame in frames],
        batch_size=16,
        normalize_embeddings=True,
        show_progress_bar=False,
    ), len(frames))
    encoded = []
    for frame, vector in zip(frames, vectors):
        encoded.append({
            'embedding': _as_list(vector),
            'embedding_model': model_id,
            'model_version': _VERSIONS.get(model_id) or model_id,
            'vector_dimension': len(vector),
            'modality': 'video_keyframe',
            'frame_index': frame['frame_index'],
            'frame_seconds': frame.get('frame_seconds'),
            'content_hash': frame['content_hash'],
        })
    return encoded


def embed_video_keyframes(path: Path, limit: int = 3) -> list[dict]:
    return embed_frames(sample_video_frames(path, limit=limit))


def embed_texts(texts: list[str]) -> list[dict]:
    if not texts:
        return []
    model_id = settings.experience_text_model or TEXT_MODEL_ID
    vectors = _rows(
        text_model().encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False),
        len(texts),
    )
    encoded = []
    for text, vector in zip(texts, vectors):
        encoded.append({
            'embedding': _as_list(vector),
            'embedding_model': model_id,
            'model_version': _VERSIONS.get(model_id) or model_id,
            'vector_dimension': len(vector),
            'modality': 'text',
            'content_hash': content_hash(text),
        })
    return encoded


def embed_image_batch(paths: list[Path]) -> list[dict]:
    if not paths:
        return []
    import io
    from PIL import Image

    model_id = settings.experience_image_model or IMAGE_MODEL_ID
    images = []
    hashes = []
    for path in paths:
        raw = Path(path).read_bytes()
        images.append(Image.open(io.BytesIO(raw)).convert('RGB'))
        hashes.append(content_hash(raw))
    vectors = _rows(
        image_model().encode(images, batch_size=16, normalize_embeddings=True, show_progress_bar=False),
        len(paths),
    )
    for image in images:
        image.close()
    encoded = []
    for digest, vector in zip(hashes, vectors):
        encoded.append({
            'embedding': _as_list(vector),
            'embedding_model': model_id,
            'model_version': _VERSIONS.get(model_id) or model_id,
            'vector_dimension': len(vector),
            'modality': 'image',
            'content_hash': digest,
        })
    return encoded


def vector_literal(values: list[float]) -> str:
    expected = int(settings.experience_vector_dimension or VECTOR_DIM)
    if len(values) != expected:
        raise EmbeddingError(f'vector_dimension:{len(values)}')
    return '[' + ','.join(format(float(v), '.7f') for v in values) + ']'
