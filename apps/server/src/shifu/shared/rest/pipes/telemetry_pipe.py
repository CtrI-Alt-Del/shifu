from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import Request  # noqa: TC002 - FastAPI resolves dependency annotations at runtime.

if TYPE_CHECKING:
    from shifu.shared.core.interfaces.telemetry_provider import (
        TelemetryEventInput,
        TelemetryProvider,
    )


class TelemetryPipe:
    """Resolve the one provider composed on ``request.app.state``.

    The application composition seam is intentionally optional while the root
    ``FastAPIApp`` integration is being completed by the Orchestrator. A
    missing or failing telemetry sink must never change an HTTP outcome.
    """

    @staticmethod
    def get_telemetry_provider(request: Request) -> TelemetryProvider | None:
        provider = getattr(request.app.state, 'telemetry_provider', None)
        return cast('TelemetryProvider | None', provider)

    @staticmethod
    def get_provider(request: Request) -> TelemetryProvider | None:
        """Compatibility alias for explicit dependency composition."""
        return TelemetryPipe.get_telemetry_provider(request)

    @staticmethod
    def get_request_id(request: Request) -> str | None:
        value = getattr(request.state, 'request_id', None)
        return value if isinstance(value, str) else None

    @staticmethod
    def emit(
        provider: TelemetryProvider | None,
        event: TelemetryEventInput,
    ) -> None:
        if provider is None:
            return
        try:
            provider.emit(event)
        except Exception:  # noqa: BLE001 - telemetry never changes business work.
            return
