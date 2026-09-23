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
    google_sso_only: bool = True
    openrouter_api_key: str = ''
    analysis_model: str = 'google/gemini-3.8-flash'
    dubbing_model: str = 'minimax/speech-2.8-hd'
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

settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
