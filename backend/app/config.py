"""Configuration lue depuis les variables d'environnement et le fichier .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Hoe-aona?"
    data_dir: Path = BACKEND_DIR / "data"
    frontend_dist: Path = BACKEND_DIR.parent / "frontend" / "dist" / "hoe-aona" / "browser"
    cors_origins: list[str] = ["http://localhost:4200"]
    max_upload_mb: int = 20

    # Comptes : le premier inscrit devient administrateur.
    allow_registration: bool = True
    session_days: int = 30
    cookie_secure: bool = False  # à passer à true derrière HTTPS

    # LLM compatibles OpenAI
    llm_priority: str = "gemini,groq"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_whisper_model: str = "whisper-large-v3-turbo"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Sources de preuves et détecteurs
    tavily_api_key: str | None = None
    newsdata_api_key: str | None = None
    sightengine_api_user: str | None = None
    sightengine_api_secret: str | None = None
    ocr_space_api_key: str | None = None

    # Vérification physique (application mobile) : PostgreSQL + PostGIS
    postgis_url: str | None = None  # ex. postgresql://hoe:hoe@localhost:5432/hoe_aona
    verification_radius_m: int = 2000
    verification_hours: int = 24  # durée de vie d'une demande sans preneur
    location_max_age_minutes: int = 120  # une position plus ancienne n'est plus prise en compte
    max_open_verifications: int = 5  # demandes ouvertes simultanées par compte

    # MCP
    mcp_mode: str = "mcp"  # "mcp" ou "direct"
    mcp_config_file: Path = BACKEND_DIR / "mcp_servers.json"

    # Pipeline
    http_timeout: float = 20.0
    max_claims: int = 5
    max_evidence_per_claim: int = 8
    max_pages_fetched_per_claim: int = 6
    user_agent: str = "HoeAonaBot/1.0 (outil de verification des faits; contact: admin@example.org)"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "posts").mkdir(parents=True, exist_ok=True)
    (settings.data_dir / "verifications").mkdir(parents=True, exist_ok=True)
    return settings
