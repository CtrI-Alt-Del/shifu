import os
from collections.abc import Mapping
from typing import ClassVar, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PostgresDsn,
    TypeAdapter,
    field_validator,
)


DEFAULT_SERVER_APP_PORT = 7777
DEFAULT_SERVER_APP_MODE = 'local'
DEFAULT_DATABASE_URL = 'postgresql+psycopg://shifu:shifu-local@localhost:54344/shifu'
DEFAULT_AUTH_ISSUER = 'http://localhost:7000'
DEFAULT_AUTH_AUDIENCE = 'shifu-api'
DEFAULT_AUTH_JWKS_URL = 'http://localhost:7000/api/auth/jwks'
ServerAppMode = Literal['dev', 'local', 'staging', 'production']
POSTGRES_DSN_ADAPTER = TypeAdapter(PostgresDsn)


class EnvironmentSettings(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        validate_default=True,
    )

    server_app_port: int = Field(
        default=DEFAULT_SERVER_APP_PORT,
        ge=1,
        le=65535,
    )
    server_app_mode: ServerAppMode = DEFAULT_SERVER_APP_MODE
    database_url: str = DEFAULT_DATABASE_URL
    auth_issuer: str = DEFAULT_AUTH_ISSUER
    auth_audience: str = DEFAULT_AUTH_AUDIENCE
    auth_jwks_url: str = DEFAULT_AUTH_JWKS_URL

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
                'auth_issuer': values.get('SHIFU_AUTH_ISSUER', DEFAULT_AUTH_ISSUER),
                'auth_audience': values.get(
                    'SHIFU_AUTH_AUDIENCE',
                    DEFAULT_AUTH_AUDIENCE,
                ),
                'auth_jwks_url': values.get(
                    'SHIFU_AUTH_JWKS_URL',
                    DEFAULT_AUTH_JWKS_URL,
                ),
            }
        )


ENVIRONMENT = EnvironmentSettings.from_environment()
