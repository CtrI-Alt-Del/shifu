from collections.abc import Mapping
from dataclasses import dataclass

from shifu.shared.constants.environment import (
    ENVIRONMENT,
    EnvironmentSettings,
    ServerAppMode,
)


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    url: str

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'DatabaseSettings':
        settings = (
            EnvironmentSettings.from_environment(environment)
            if environment is not None
            else ENVIRONMENT
        )
        return cls(url=str(settings.database_url))


@dataclass(frozen=True, slots=True)
class SeedSettings:
    database_url: str
    server_app_mode: ServerAppMode

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'SeedSettings':
        settings = (
            EnvironmentSettings.from_environment(environment)
            if environment is not None
            else ENVIRONMENT
        )
        return cls(
            database_url=str(settings.database_url),
            server_app_mode=settings.server_app_mode,
        )
