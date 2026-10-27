"""Application configuration.

WHAT: one typed object (`Settings`) holding every value the app needs that can
      differ between machines (database URL, secrets, provider keys).
WHY:  configuration must come from the environment, never from source code, so
      the same image can run locally and in production and no secret is committed.
HOW:  pydantic-settings reads the process environment (and a local .env file in
      development), validates types, and fails loudly at startup if something
      required is missing. Everything else imports the cached `get_settings()`.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- general -------------------------------------------------------------
    app_name: str = "Sorya"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api"
    log_level: str = "INFO"
    log_json: bool = False

    # --- security ------------------------------------------------------------
    # Dev-only default. Phase 5 validates that production supplies a real secret.
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Comma-separated in the environment: CORS_ORIGINS=http://localhost:5173,http://localhost:3000
    # `NoDecode` is required: without it pydantic-settings tries to JSON-decode any
    # list-typed field coming from the environment, so a plain comma-separated
    # string raises before our validator below ever runs.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )

    # --- infrastructure (used from Phase 2/4 onwards) ------------------------
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5435/ai_video_studio"
    db_echo: bool = False
    redis_url: str = "redis://localhost:6381/0"

    # --- object storage (MinIO locally, S3 later) ----------------------------
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ai-video-studio"
    s3_region: str = "us-east-1"
    # URL the BROWSER uses to fetch media. Must be reachable from the user's machine.
    s3_public_base_url: str = "http://localhost:9100"
    # URL the RENDERER process uses. Inside Docker the worker cannot reach
    # `localhost:9100` (that is the worker container itself), so it needs the
    # in-network endpoint. Empty means "same as s3_endpoint_url".
    s3_renderer_base_url: str = ""

    # --- AI providers --------------------------------------------------------
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # gemini falls back to openrouter while GEMINI_API_KEY is empty.
    llm_provider: Literal["mock", "openrouter", "gemini"] = "openrouter"

    # gemini = Gemini TTS: natural Khmer speech, per-scene delivery direction,
    #          and subtitles aligned to the audio by Gemini (needs GEMINI_API_KEY;
    #          falls back to edge while the key is empty)
    # edge = Microsoft Edge neural voices (real speech, no API key, has Khmer)
    # mock = silent audio of the correct duration (offline / tests)
    tts_provider: Literal["gemini", "edge", "mock"] = "edge"
    tts_api_key: str = ""
    # Edge TTS prosody. Short-form video holds attention better with brisk
    # narration; use e.g. "-10%" to slow it down for learners.
    tts_rate: str = "+10%"
    tts_volume: str = "+0%"

    # --- Gemini (story, voice and subtitle timing) ---------------------------
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    # Story scripts and subtitle alignment (reads the generated audio).
    gemini_model: str = "gemini-3.8-flash"
    gemini_tts_model: str = "gemini-3.8-flash-tts"
    # Model that times the subtitles against the audio. Empty = gemini_model.
    # When it is unavailable (quota), timing falls back to the audio's pauses.
    gemini_align_model: str = ""
    # Second pass that proofreads a generated Khmer script (spelling, natural
    # phrasing, numbers as words). Doubles story-generation time.
    gemini_review_script: bool = True
    # Requests per minute allowed per model. Free-tier keys allow 5; raise it on
    # a paid tier to generate long videos faster. 0 disables pacing.
    gemini_requests_per_minute: int = 5
    # Prebuilt voice for the presenter; a project's voice ("male"/"female" or
    # a Gemini voice name) overrides it.
    gemini_tts_voice: str = "Puck"
    # Baseline delivery; each scene's own direction (whisper, excited...) is
    # added on top of it.
    gemini_tts_style: str = (
        "a warm, lively native Cambodian storyteller talking to camera in a short "
        "video; clear, natural Khmer pronunciation; brisk but easy to follow"
    )

    image_provider: Literal["mock", "replicate"] = "mock"
    image_api_key: str = ""

    # --- rendering -----------------------------------------------------------
    # Directory containing the Remotion project (src/render.ts). Relative paths
    # are resolved from the backend's working directory.
    renderer_dir: str = "../renderer"
    # Five-minute 1080p lessons can contain 9,000 frames at 30 fps. Allow an
    # hour on modest development machines before treating the render as stuck.
    render_timeout_seconds: int = 3600
    max_upload_size_mb: int = 100

    # --- telemetry -----------------------------------------------------------
    # Events are not stored here: they are written to a Redis stream that the separate
    # telemetry service consumes (see /telemetry). Setting this false stops emitting.
    telemetry_enabled: bool = True
    telemetry_stream_key: str = "sorya:telemetry:events"
    # Approximate cap on the stream, a safety valve if the service is down for long.
    telemetry_stream_maxlen: int = 500_000
    # Optional price list for the cost estimate, as JSON, keyed "<service>.<provider>":
    #   {"llm.gemini": {"input_per_1m": 0.30, "output_per_1m": 2.50},
    #    "tts.gemini": {"per_1m_chars": 15.0}, "image.replicate": {"per_call": 0.003}}
    # Empty means "unknown": events then carry no cost rather than a guess.
    telemetry_prices: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow CORS_ORIGINS to be given as a comma-separated string."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def renderer_media_base_url(self) -> str:
        """Base URL for media URLs placed in the render payload."""
        return (self.s3_renderer_base_url or self.s3_endpoint_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the environment is parsed exactly once per process."""
    return Settings()
