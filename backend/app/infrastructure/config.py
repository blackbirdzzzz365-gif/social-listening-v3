from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Social Listening v3"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str | None = None
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    sqlite_db_path: str = "app.db"
    browser_profile_dir: str = str(Path.home() / ".social-listening" / "browser_profile")
    opaque_id_secret: str = "social-listening-v3-dev-secret"
    browser_mock_mode: bool = True
    browser_mock_user_id: str = "dev-facebook-user"
    camoufox_headless: bool = False
    browser_screen_width: int = 1600
    browser_screen_height: int = 900
    static_dir: str = "static"
    platform_auth_enabled: bool = True
    platform_auth_session_url: str = "https://blackbirdzzzz.art/v1/auth/session"
    platform_auth_login_url: str = "https://blackbirdzzzz.art/login"
    platform_auth_cookie_name: str = "__Secure-bb_session"
    platform_auth_cookie_fallback_name: str = "bb_session"
    platform_auth_timeout_sec: float = 5.0
    openai_compatible_api_key: str = ""
    openai_compatible_base_url: str = "https://llm.chiasegpu.vn/v1"
    openai_compatible_timeout_sec: float = 25.0
    anthropic_api_key: str = ""
    anthropic_fallback_model: str = "claude-haiku-4-5"
    keyword_analysis_model: str = "gpt-4o"
    keyword_analysis_thinking: bool = False
    plan_generation_model: str = "gpt-4o"
    plan_generation_thinking: bool = False
    plan_refinement_model: str = "gpt-4o"
    plan_refinement_thinking: bool = False
    theme_analysis_model: str = "gpt-4o"
    content_labeling_model: str = "gpt-4o"
    label_taxonomy_version: str = "v1"
    label_batch_size: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
