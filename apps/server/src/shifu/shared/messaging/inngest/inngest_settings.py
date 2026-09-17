"""Validated environment settings for the Inngest client."""

from collections.abc import Mapping
from dataclasses import dataclass
import os


DEFAULT_INNGEST_APP_ID = 'shifu'
DEFAULT_INNGEST_BASE_URL = 'http://localhost:18288'


@dataclass(frozen=True, slots=True)
class InngestSettings:
    """Validated values needed to construct the SDK client."""

    app_id: str
    api_base_url: str
    event_api_base_url: str
    is_production: bool
    event_key: str | None = None
    signing_key: str | None = None

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> 'InngestSettings':
        values = environment if environment is not None else os.environ
        app_id = values.get('INNGEST_APP_ID', DEFAULT_INNGEST_APP_ID).strip()
        if not app_id:
            raise ValueError('INNGEST_APP_ID must not be empty')

        base_url = values.get('INNGEST_BASE_URL', DEFAULT_INNGEST_BASE_URL).rstrip('/')
        is_production = values.get('INNGEST_DEV', '1').lower() not in {
            '1',
            'true',
            'yes',
        }
        event_key = values.get('INNGEST_EVENT_KEY', '').strip() or None
        signing_key = values.get('INNGEST_SIGNING_KEY', '').strip() or None
        if is_production and (event_key is None or signing_key is None):
            raise ValueError(
                'INNGEST_EVENT_KEY and INNGEST_SIGNING_KEY are required in production'
            )

        return cls(
            app_id=app_id,
            api_base_url=values.get('INNGEST_API_BASE_URL', base_url).rstrip('/'),
            event_api_base_url=values.get(
                'INNGEST_EVENT_API_BASE_URL', base_url
            ).rstrip('/'),
            is_production=is_production,
            event_key=event_key,
            signing_key=signing_key,
        )
