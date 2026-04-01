from __future__ import annotations

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
    openai_compatible_api_key: str = ""
    openai_compatible_base_url: str = "https://llm.chiasegpu.vn/v1"
    openai_compatible_timeout_sec: float = 25.0
    phase8_judge_api_key: str = ""
    phase8_judge_api_base_url: str = "https://llm.chiasegpu.vn/v1"
    phase8_judge_api_timeout_sec: float = 25.0
    phase8_judge_api_retry_count: int | None = None
    phase8_ocr_api_key: str = ""
    phase8_ocr_api_base_url: str = "https://llm.chiasegpu.vn/v1"
    phase8_ocr_api_timeout_sec: float = 40.0
    phase8_ocr_api_retry_count: int | None = None
    ai_rate_limit_cooldown_sec: float = 60.0
    anthropic_api_key: str = ""
    anthropic_fallback_model: str = "claude-haiku-4-5"
    ai_provider_retry_count: int = 1
    planner_retry_count: int = 2
    planner_retry_backoff_sec: float = 1.0
    keyword_analysis_model: str = "gpt-4o"
    keyword_analysis_thinking: bool = False
    plan_generation_model: str = "gpt-4o"
    plan_generation_thinking: bool = False
    plan_refinement_model: str = "gpt-4o"
    plan_refinement_thinking: bool = False
    validity_spec_model: str = "gpt-4o"
    validity_spec_thinking: bool = False
    content_judge_model: str = "gpt-4o-mini"
    content_judge_thinking: bool = False
    image_fallback_model: str = "gpt-4o-mini"
    image_fallback_thinking: bool = False
    theme_analysis_model: str = "gpt-4o"
    content_labeling_model: str = "gpt-4o"
    label_taxonomy_version: str = "v1"
    label_batch_size: int = 20
    retrieval_batch_size: int = 20
    retrieval_continue_accepted_ratio: float = 0.25
    retrieval_weak_accepted_ratio: float = 0.10
    retrieval_weak_uncertain_ratio: float = 0.20
    retrieval_strong_accept_count: int = 3
    retrieval_max_consecutive_weak_batches: int = 2
    retrieval_max_zero_accept_batches: int = 2
    retrieval_min_accepted_per_path: int = 3
    retrieval_max_scanned_per_path: int = 60
    retrieval_max_query_variants: int = 2
    pre_ai_mode: str = "strict"
    judge_high_confidence_threshold: float = 0.75
    step_heartbeat_interval_sec: float = 10.0
    search_posts_timeout_sec: float = 300.0
    search_in_group_timeout_sec: float = 240.0
    crawl_feed_timeout_sec: float = 240.0
    crawl_comments_timeout_sec: float = 240.0
    search_groups_timeout_sec: float = 120.0
    group_membership_timeout_sec: float = 120.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
