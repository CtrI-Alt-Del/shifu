"""Real registered jobs with an intentionally unavailable telemetry sink."""

from fastapi import FastAPI

from shifu.app import FastAPIApp
from shifu.shared.core.interfaces.telemetry_provider import TelemetryEventInput
from shifu.shared.providers.console_telemetry_provider import ConsoleTelemetryProvider


class _FailingStartedTelemetry(ConsoleTelemetryProvider):
    def emit(self, event: TelemetryEventInput) -> None:
        super().emit(event)
        if event['event'] == 'job.started':
            raise RuntimeError('telemetry sink unavailable')


def create_app() -> FastAPI:
    return FastAPIApp.register(
        telemetry_provider=_FailingStartedTelemetry(
            service='shifu-api', environment='local', version='test'
        )
    )
