from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / '.env'), extra='ignore')
    tikhub_api_key: str = ''
    tikhub_base_url: str = 'https://api.tikhub.io'
    tikhub_daily_requests: int = 100
    google_client_id: str = ''
    google_client_secret: str = ''
    google_allowed_emails: str = 'andreykatruk@gmail.com'
    google_sso_only: bool = False
    openrouter_api_key: str = ''
    analysis_model: str = 'google/gemini-3.8-flash'
    dubbing_model: str = 'qwen/qwen3-tts-12hz-1.7b-customvoice'
    dubbing_price_per_million: float = 100.0
    generation_model: str = 'google/veo-3.1-fast'
    image_model: str = 'google/gemini-2.5-flash-image'
    lumen_session_secret: str = ''
    lumen_invite_code: str = ''
    database_url: str = ''
    data_dir: Path = ROOT / 'data'
    secure_cookies: bool = False
    public_origin: str = 'http://127.0.0.1:8018'
    daily_budget_usd: float = 20.0
    max_upload_mb: int = 250
    max_duration_seconds: int = 420
    max_storage_gb: int = 8
    # When true (default V5), Create Video uses Director V4 + Remotion for supported
    # projects. Project «e» always Remotion. Hypit is explicit legacy when this is off
    # or picture_engine=hypit is forced — never a silent fallback on Remotion failure.
    remotion_engine_enabled: bool = True
    # Fast project creation: upload → metadata → ready. No LLM / analyze job on create.
    fast_project_creation_enabled: bool = True
    # LLM for Director/DNA. Default none — OpenRouter/RunPod optional at generation only.
    # Values: none | openrouter | runpod. runpod is fail-closed (RUNPOD_LLM_UNAVAILABLE).
    llm_provider: str = 'none'
    runpod_llm_model: str = 'qwen2.5:7b-instruct'
    runpod_llm_base_url: str = ''
    runpod_llm_port: int = 11434
    runpod_llm_api_key: str = 'lumen-runpod'
    # Transcript at generation: auto | whisperx | placeholder
    # auto loads the CPU faster-whisper path. It does not invent a silence grid.
    transcript_provider: str = 'auto'
    # CPU ASR. Weights go to asr_model_cache (media volume when mounted).
    asr_model: str = 'small'
    asr_model_cache: str = ''
    asr_config_version: str = 'cpu-int8-vad-1'
    # When true, Create Video fails if semantic-plan.json is missing or invalid.
    # It does not substitute HeuristicDirectorProvider and call that success.
    semantic_planner_required: bool = False
    semantic_planner_command: str = ''
    # Used only when semantic_planner_required is explicitly on. Does not replace analysis_model.
    semantic_director_model: str = 'qwen/qwen3-30b-a3b-instruct-2507'
    # Persistent visual experience memory (pgvector). Default off so Director
    # generation stays unchanged until retrieval is validated.
    visual_experience_memory_enabled: bool = False
    # Hybrid media retrieval + Director experience. Default off. Does not
    # replace keyword search until this process sets it to 1.
    visual_intelligence_enabled: bool = False
    # Premium semantic motion V14. Default off — V11.2 path stays the production picture.
    semantic_motion_v14_enabled: bool = False
    # V15 library expansion. Default off. Does not replace V14 or V11.2.
    semantic_motion_v15_enabled: bool = False
    # V16 scene composer. Default off. Does not change V11.2, V14, or V15.
    scene_composer_v16_enabled: bool = False
    # V17 motion quality. Default off. Does not turn on experience memory or visual intelligence.
    motion_quality_v17_enabled: bool = False
    # Empty uses the media volume when mounted, otherwise data/embedding-models.
    experience_embedding_cache: str = ''
    experience_text_model: str = 'sentence-transformers/clip-ViT-B-32-multilingual-v1'
    experience_image_model: str = 'sentence-transformers/clip-ViT-B-32'
    experience_vector_dimension: int = 512

settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
