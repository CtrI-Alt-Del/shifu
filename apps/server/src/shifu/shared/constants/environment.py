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
    model_validator,
)


DEFAULT_SERVER_APP_PORT = 7777
DEFAULT_SERVER_APP_MODE = 'local'
DEFAULT_DATABASE_URL = 'postgresql+psycopg://shifu:shifu-local@localhost:54344/shifu'
DEFAULT_AUTH_ISSUER = 'http://localhost:7000'
DEFAULT_AUTH_AUDIENCE = 'shifu-api'
DEFAULT_AUTH_JWKS_URL = 'http://localhost:7000/api/auth/jwks'
DEFAULT_EMAIL_PROVIDER = 'smtp'
DEFAULT_SMTP_HOST = 'localhost'
DEFAULT_SMTP_PORT = 1026
DEFAULT_EMAIL_FROM = 'no-reply@shifu.local'
DEFAULT_CONFIRMATION_ACTION_ORIGIN = 'http://localhost:7000'
DEFAULT_EMAIL_TIMEOUT_SECONDS = 10.0
DEFAULT_LOCAL_BFF_SHARED_SECRET = 'shifu-local-bff-shared-secret-change-me'
ServerAppMode = Literal['dev', 'local', 'staging', 'production']
EmailProvider = Literal['smtp', 'resend']
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
    email_provider: EmailProvider = DEFAULT_EMAIL_PROVIDER
    smtp_host: str = DEFAULT_SMTP_HOST
    smtp_port: int = Field(default=DEFAULT_SMTP_PORT, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_start_tls: bool = False
    smtp_use_tls: bool = False
    email_from: str = DEFAULT_EMAIL_FROM
    resend_api_key: str | None = None
    resend_from: str | None = None
    email_timeout_seconds: float = Field(
        default=DEFAULT_EMAIL_TIMEOUT_SECONDS,
        gt=0,
        le=60,
    )
    confirmation_action_origin: str = DEFAULT_CONFIRMATION_ACTION_ORIGIN
    bff_shared_secret: str = DEFAULT_LOCAL_BFF_SHARED_SECRET
    communication_encryption_keys: tuple[str, ...] = ()

    @field_validator('database_url')
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        POSTGRES_DSN_ADAPTER.validate_python(value)
        return value

    @model_validator(mode='after')
    def validate_email_configuration(self) -> 'EnvironmentSettings':
        if not self.bff_shared_secret.strip():
            raise ValueError('BFF shared secret is required')
        if not self.communication_encryption_keys:
            raise ValueError('Communication encryption keys are required')
        if not self.confirmation_action_origin.startswith(('http://', 'https://')):
            raise ValueError('Confirmation action origin must be an HTTP URL')
        if self.email_provider == 'resend' and (
            not self.resend_api_key or not self.resend_from
        ):
            raise ValueError('Resend requires an API key and sender address')
        if self.server_app_mode == 'production' and self.email_provider != 'resend':
            raise ValueError('Production e-mail delivery must use Resend')
        if self.server_app_mode == 'production' and not self.resend_api_key:
            raise ValueError('Production Resend configuration is incomplete')
        return self

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'EnvironmentSettings':
        values = environment if environment is not None else os.environ
        server_app_mode = values.get('SHIFU_SERVER_APP_MODE', DEFAULT_SERVER_APP_MODE)
        email_provider = values.get('SHIFU_EMAIL_PROVIDER', DEFAULT_EMAIL_PROVIDER)
        raw_encryption_keys = values.get('SHIFU_COMMUNICATION_ENCRYPTION_KEYS')
        if raw_encryption_keys is None or not raw_encryption_keys.strip():
            encryption_keys = ()
        else:
            encryption_keys = tuple(
                key.strip() for key in raw_encryption_keys.split(',') if key.strip()
            )
        return cls.model_validate(
            {
                'server_app_port': values.get(
                    'SHIFU_SERVER_APP_PORT',
                    str(DEFAULT_SERVER_APP_PORT),
                ),
                'server_app_mode': server_app_mode,
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
                'email_provider': email_provider,
                'smtp_host': values.get('SHIFU_SMTP_HOST', DEFAULT_SMTP_HOST),
                'smtp_port': values.get('SHIFU_SMTP_PORT', str(DEFAULT_SMTP_PORT)),
                'smtp_username': values.get('SHIFU_SMTP_USERNAME') or None,
                'smtp_password': values.get('SHIFU_SMTP_PASSWORD') or None,
                'smtp_start_tls': values.get('SHIFU_SMTP_START_TLS', '0')
                in {'1', 'true', 'True'},
                'smtp_use_tls': values.get('SHIFU_SMTP_USE_TLS', '0')
                in {'1', 'true', 'True'},
                'email_from': values.get('SHIFU_EMAIL_FROM', DEFAULT_EMAIL_FROM),
                'resend_api_key': values.get('SHIFU_RESEND_API_KEY') or None,
                'resend_from': values.get('SHIFU_RESEND_FROM') or None,
                'email_timeout_seconds': values.get(
                    'SHIFU_EMAIL_TIMEOUT_SECONDS',
                    str(DEFAULT_EMAIL_TIMEOUT_SECONDS),
                ),
                'confirmation_action_origin': values.get(
                    'SHIFU_CONFIRMATION_ACTION_ORIGIN',
                    DEFAULT_CONFIRMATION_ACTION_ORIGIN,
                ),
                'bff_shared_secret': values.get(
                    'SHIFU_BFF_SHARED_SECRET',
                    DEFAULT_LOCAL_BFF_SHARED_SECRET,
                ),
                'communication_encryption_keys': encryption_keys,
            }
        )


ENVIRONMENT = EnvironmentSettings.from_environment()
