"""Configuration settings for CrowdGen Playwright automation."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application global settings and runtime credentials."""

    login_url: str = os.getenv("MAVEN_LOGIN_URL", "https://dq0uw9vf3nt8l.cloudfront.net")
    timeout_ms: int = int(os.getenv("CROWDGEN_TIMEOUT_MS", "40000"))
    max_tasks: int = int(os.getenv("CROWDGEN_MAX_TASKS", "250"))
    aht_min_wait_sec: int = int(os.getenv("CROWDGEN_AHT_MIN_WAIT_SEC", "30"))
    target_remaining_sec: int = int(os.getenv("CROWDGEN_TARGET_REMAINING_SEC", "0"))
    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    openrouter_vision_model: str = (
        os.getenv("OPENROUTER_VISION_MODEL")
        or os.getenv("OPENROUTER_MODEL")
        or "dots-studio/dots-3-note-preview:free"
    )
    openrouter_fallback_model: str = os.getenv(
        "OPENROUTER_FALLBACK_MODEL", "qwen/qwen3.8-27b:free"
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")


config = Settings()
