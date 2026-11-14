from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import UUID, uuid4

from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from shifu.shared.core.interfaces.telemetry_provider import (
    TelemetryEventInput,
    TelemetryProvider,
)
from shifu.shared.rest.pipes.telemetry_pipe import TelemetryPipe


class TelemetryMiddleware(BaseHTTPMiddleware):
    """Add request correlation and emit one safe HTTP completion event."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = self._resolve_request_id(request)
        request.state.request_id = request_id
        started_at = perf_counter()
        provider = TelemetryPipe.get_telemetry_provider(request)

        try:
            response = await call_next(request)
        except Exception:
            self._emit_http_event(
                provider=provider,
                request=request,
                request_id=request_id,
                status_code=500,
                duration_ms=self._duration_ms(started_at),
            )
            raise

        response.headers['X-Request-ID'] = request_id
        self._emit_http_event(
            provider=provider,
            request=request,
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=self._duration_ms(started_at),
        )
        return response

    @staticmethod
    def _resolve_request_id(request: Request) -> str:
        candidate = request.headers.get('X-Request-ID', '').strip()
        if candidate:
            try:
                if UUID(candidate).version == 4:
                    return candidate
            except ValueError:
                pass
        return str(uuid4())

    @staticmethod
    def _duration_ms(started_at: float) -> float:
        return round(max(0.0, (perf_counter() - started_at) * 1000), 3)

    @staticmethod
    def _route_template(request: Request) -> str:
        route = request.scope.get('route')
        if isinstance(route, APIRoute):
            return route.path_format
        return 'unmatched'

    @staticmethod
    def _emit_http_event(
        *,
        provider: TelemetryProvider | None,
        request: Request,
        request_id: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        failed = status_code >= 400
        event: TelemetryEventInput = {
            'level': 'ERROR' if status_code >= 500 else 'WARNING' if failed else 'INFO',
            'event': 'http.request.failed' if failed else 'http.request.completed',
            'request_id': request_id,
            'method': request.method,
            'route': TelemetryMiddleware._route_template(request),
            'status_code': status_code,
            'duration_ms': duration_ms,
            'operation': 'http.request',
            'result': 'failure' if failed else 'success',
        }
        TelemetryPipe.emit(provider, event)
