from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_trusted_proxy_ips(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [ip.strip() for ip in value.split(',') if ip.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.local', extra='ignore')

    redis_url: str
    diagnostic_revision_hmac_key: SecretStr | None = None
    openrouter_api_key: str | None = None
    openrouter_prompt_logging_disabled: bool = False
    mentor_title_prompt_logging_disabled: bool = False
    mentor_generation_limit_per_hour: int = Field(default=30, ge=0, le=1000)
    mentor_telemetry_enabled: bool = False
    mentor_telemetry_content_enabled: bool = False
    langfuse_public_key: SecretStr | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_base_url: HttpUrl = HttpUrl('http://localhost:7003')
    agentos_database_url: PostgresDsn | None = None
    agentos_intelligence_queue_max_concurrency: int = Field(default=4, ge=1, le=128)
    agentos_intelligence_queue_max_depth: int = Field(default=1000, ge=1, le=100_000)
    agentos_intelligence_queue_timeout_seconds: int = Field(
        default=600, ge=1, le=86_400
    )
    agentos_learning_queue_max_concurrency: int = Field(default=4, ge=1, le=128)
    agentos_learning_queue_max_depth: int = Field(default=1000, ge=1, le=100_000)
    agentos_learning_queue_timeout_seconds: int = Field(default=600, ge=1, le=86_400)
    mentor_attachment_storage_bucket: str = Field(
        default='shifu-mentor-attachments', min_length=3, max_length=63
    )
    mentor_attachment_storage_region: str = Field(default='us-east-1', min_length=1)
    mentor_attachment_storage_endpoint_url: HttpUrl | None = None
    mentor_attachment_storage_addressing_style: Literal['auto', 'path', 'virtual'] = (
        'auto'
    )
    mentor_attachment_storage_access_key: SecretStr | None = None
    mentor_attachment_storage_secret_key: SecretStr | None = None
    mentor_attachment_max_image_pixels: int = Field(
        default=20_000_000, ge=1, le=100_000_000
    )
    mentor_attachment_max_pdf_pages: int = Field(default=40, ge=1, le=1000)
    mentor_attachment_max_extracted_chars: int = Field(
        default=200_000, ge=1, le=1_000_000
    )
    mentor_attachment_pdf_processing_timeout_seconds: int = Field(
        default=10, ge=1, le=120
    )
    mentor_attachment_max_pdf_rendered_bytes: int = Field(
        default=20_000_000, ge=1, le=100_000_000
    )
    openrouter_decisions_url: HttpUrl = HttpUrl(
        'https://openrouter.ai/api/alpha/decisions'
    )
    jev_model: Literal['typesafe/jev-1.13'] = 'typesafe/jev-1.13'
    planning_session_ttl_seconds: int = Field(default=7200, ge=60, le=86_400)
    planning_operation_timeout_seconds: int = Field(default=180, ge=10, le=3600)
    max_activity_payload_bytes: int = Field(
        default=512 * 1024, ge=1, le=4 * 1024 * 1024
    )
    max_code_assessment_input_bytes: int = Field(
        default=256 * 1024, ge=1, le=4 * 1024 * 1024
    )
    trusted_proxy_ips: Annotated[
        list[str], NoDecode, BeforeValidator(_parse_trusted_proxy_ips)
    ] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
