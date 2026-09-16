import os
from collections.abc import Mapping
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PostgresDsn,
    TypeAdapter,
    field_validator,
)


DEFAULT_SERVER_APP_PORT = 3333
DEFAULT_SERVER_APP_MODE = 'local'
DEFAULT_DATABASE_URL = 'postgresql+psycopg://shifu:shifu-local@localhost:54344/shifu'
ServerAppMode = Literal['dev', 'local', 'staging', 'production']
POSTGRES_DSN_ADAPTER = TypeAdapter(PostgresDsn)


class EnvironmentSettings(BaseModel):
    model_config = ConfigDict(frozen=True, validate_default=True)

    server_app_port: int = Field(
        default=DEFAULT_SERVER_APP_PORT,
        ge=1,
        le=65535,
    )
    server_app_mode: ServerAppMode = DEFAULT_SERVER_APP_MODE
    database_url: str = DEFAULT_DATABASE_URL

    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        POSTGRES_DSN_ADAPTER.validate_python(value)
        return value

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'EnvironmentSettings':
        values = environment if environment is not None else os.environ
        return cls.model_validate(
            {
                'server_app_port': values.get(
                    'SHIFU_SERVER_APP_PORT',
                    str(DEFAULT_SERVER_APP_PORT),
                ),
                'server_app_mode': values.get(
                    'SHIFU_SERVER_APP_MODE',
                    DEFAULT_SERVER_APP_MODE,
                ),
                'database_url': values.get('DATABASE_URL', DEFAULT_DATABASE_URL),
            }
        )


ENVIRONMENT = EnvironmentSettings.from_environment()
