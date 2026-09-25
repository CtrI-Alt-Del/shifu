import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

from pydantic import PostgresDsn, TypeAdapter


DEFAULT_DATABASE_URL = 'postgresql+psycopg://shifu:shifu-local@localhost:54344/shifu'
ServerAppMode = Literal['dev', 'local', 'staging', 'production']
POSTGRES_DSN_ADAPTER = TypeAdapter(PostgresDsn)
SERVER_APP_MODES = frozenset({'dev', 'local', 'staging', 'production'})


def _environment_values(
    environment: Mapping[str, str] | None,
) -> Mapping[str, str]:
    return environment if environment is not None else os.environ


def _database_url(values: Mapping[str, str]) -> str:
    value = values.get('DATABASE_URL', DEFAULT_DATABASE_URL)
    POSTGRES_DSN_ADAPTER.validate_python(value)
    return value


def _server_app_mode(values: Mapping[str, str]) -> ServerAppMode:
    value = values.get('SHIFU_SERVER_APP_MODE', 'local')
    if value not in SERVER_APP_MODES:
        raise ValueError(f'Invalid server application mode: {value}')
    return cast('ServerAppMode', value)


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'DatabaseSettings':
        return cls(url=_database_url(_environment_values(environment)))


@dataclass(frozen=True, slots=True)
class SeedSettings:
    database_url: str
    server_app_mode: ServerAppMode

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'SeedSettings':
        values = _environment_values(environment)
        return cls(
            database_url=_database_url(values),
            server_app_mode=_server_app_mode(values),
        )
