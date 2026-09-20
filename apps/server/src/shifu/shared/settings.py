from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_trusted_proxy_ips(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return value
    return [ip.strip() for ip in value.split(',') if ip.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env.local', extra='ignore')

    redis_url: str
    trusted_proxy_ips: Annotated[
        list[str], NoDecode, BeforeValidator(_parse_trusted_proxy_ips)
    ] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
