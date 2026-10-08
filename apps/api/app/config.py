from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = API_DIR.parent.parent
DATA_DIR = REPO_ROOT / "data"

API_VERSION = "0.2.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=API_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    gemini_api_key: str = ""
    gemini_model_fast: str = "gemini-3.5-flash-lite"
    gemini_model_smart: str = "gemini-3.8-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    ollama_url: str = ""
    ollama_model: str = "llama3.2"
    github_token: str = ""
    database_url: str = "sqlite:///./dev.db"
    supabase_jwt_secret: str = ""  # HS256 projects; asymmetric projects use SUPABASE_URL (JWKS) instead
    supabase_url: str = ""
    # development | production. Production refuses DEV_AUTH and needs a way to verify tokens.
    environment: str = "development"
    # Comma-separated emails or Supabase user ids that may see cohort data (placement staff).
    placement_staff: str = ""
    dev_auth: bool = False
    log_level: str = "INFO"
    log_format: str = "json"  # json | text
    max_body_kb: int = 1024  # any request body except a document upload
    max_upload_kb: int = 6144  # document upload: a 5 MB file plus multipart overhead
    # 0 = off. Some poolers reject the startup option this needs; see apps/api/README.md.
    db_statement_timeout_ms: int = 0
    # Wait between verify quizzes on one project (docs/QUIZ.md): 1 h for the hackathon, 24 h in production.
    quiz_cooldown_minutes: int = 60
    # Comma-separated; extension origins are allowed by regex in main.py.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def staff_set(self) -> frozenset[str]:
        return frozenset(v.strip().lower() for v in self.placement_staff.split(",") if v.strip())

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def llm_provider(self) -> str | None:
        if self.gemini_api_key:
            return "gemini"
        if self.groq_api_key:
            return "groq"
        if self.ollama_url:
            return "ollama"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def check_settings(settings: Settings) -> None:
    """Refuse to start in a configuration that would be unsafe in production."""
    if not settings.is_production:
        return
    problems = []
    if settings.dev_auth:
        problems.append("DEV_AUTH=1 would accept every request as the demo user")
    if not (settings.supabase_jwt_secret or settings.supabase_url):
        problems.append("set SUPABASE_JWT_SECRET (HS256) or SUPABASE_URL (JWKS) so tokens can be verified")
    if problems:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
