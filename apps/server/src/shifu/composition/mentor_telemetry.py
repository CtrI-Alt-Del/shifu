from contextlib import suppress
from typing import TYPE_CHECKING

from langfuse import Langfuse

if TYPE_CHECKING:
    from shifu.shared.settings import Settings


def build_mentor_telemetry_client(settings: 'Settings') -> Langfuse | None:
    if not settings.mentor_telemetry_enabled:
        return None
    if settings.langfuse_public_key is None or settings.langfuse_secret_key is None:
        return None
    with suppress(Exception):
        return Langfuse(
            public_key=settings.langfuse_public_key.get_secret_value(),
            secret_key=settings.langfuse_secret_key.get_secret_value(),
            base_url=str(settings.langfuse_base_url).rstrip('/'),
            additional_headers={'x-langfuse-ingestion-version': '4'},
        )
    return None


def close_mentor_telemetry_client(client: Langfuse | None) -> None:
    if client is not None:
        with suppress(Exception):
            client.shutdown()
