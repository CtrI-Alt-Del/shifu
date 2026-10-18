"""Own the optional process-wide Langfuse export client."""

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langfuse import Langfuse
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from shifu.shared.settings import Settings


@dataclass(frozen=True, slots=True)
class AgentMonitoringClient:
    client: Langfuse
    tracer_provider: TracerProvider


def build_agent_monitoring_client(settings: 'Settings') -> AgentMonitoringClient | None:
    if not settings.mentor_telemetry_enabled:
        return None
    public_key = settings.langfuse_public_key
    secret_key = settings.langfuse_secret_key
    if public_key is None or secret_key is None:
        return None
    if not public_key.get_secret_value() or not secret_key.get_secret_value():
        return None

    tracer_provider = TracerProvider(shutdown_on_exit=False)
    try:
        client = Langfuse(
            public_key=public_key.get_secret_value(),
            secret_key=secret_key.get_secret_value(),
            base_url=str(settings.langfuse_base_url).rstrip('/'),
            additional_headers={'x-langfuse-ingestion-version': '4'},
            tracer_provider=tracer_provider,
            timeout=2,
            flush_at=32,
            flush_interval=1,
        )
        return AgentMonitoringClient(client, tracer_provider)
    except Exception:  # noqa: BLE001 - monitoring cannot prevent agent execution.
        with suppress(Exception):
            tracer_provider.shutdown()
        return None


def close_agent_monitoring_client(monitoring: AgentMonitoringClient | None) -> None:
    if monitoring is None:
        return
    try:
        with suppress(Exception):
            monitoring.client.shutdown()
    finally:
        with suppress(Exception):
            monitoring.tracer_provider.shutdown()
