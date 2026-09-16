import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal


DEFAULT_DATABASE_URL = 'postgresql+psycopg://shifu:shifu-local@localhost:54344/shifu'
ServerAppMode = Literal['local', 'staging', 'production']
SERVER_APP_MODES = frozenset(('local', 'staging', 'production'))


def _read_server_app_mode(values: Mapping[str, str]) -> ServerAppMode:
    raw_mode = values.get('SHIFU_SERVER_APP_MODE', 'local')
    if raw_mode not in SERVER_APP_MODES:
        raise ValueError(
            'SHIFU_SERVER_APP_MODE must be one of: local, staging, production.'
        )
    return raw_mode


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'DatabaseSettings':
        values = environment if environment is not None else os.environ
        return cls(url=values.get('DATABASE_URL', DEFAULT_DATABASE_URL))


@dataclass(frozen=True, slots=True)
class SeedSettings:
    database_url: str
    server_app_mode: ServerAppMode

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'SeedSettings':
        values = environment if environment is not None else os.environ
        return cls(
            database_url=values.get('DATABASE_URL', DEFAULT_DATABASE_URL),
            server_app_mode=_read_server_app_mode(values),
        )
