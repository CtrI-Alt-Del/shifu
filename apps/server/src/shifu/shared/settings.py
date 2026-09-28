from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, HttpUrl, SecretStr
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
    openrouter_decisions_url: HttpUrl = HttpUrl(
        'https://openrouter.ai/api/alpha/decisions'
    )
    jev_model: Literal['typesafe/jev-1.13'] = 'typesafe/jev-1.13'
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
