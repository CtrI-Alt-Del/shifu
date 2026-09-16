import ipaddress
import json
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from shifu.shared.core.domain.errors import RateLimitError

if TYPE_CHECKING:
    from shifu.shared.core.interfaces import CacheProvider

_EXCLUDED_PATHS = frozenset({'/health'})
_CAPACITY = 10
_REFILL_PER_SECOND = 60 / 60

_IpNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, trusted_proxy_ips: list[str]) -> None:
        super().__init__(app)
        self._trusted_networks = _parse_trusted_networks(trusted_proxy_ips)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        cache_provider: CacheProvider = request.app.state.cache_provider
        client_ip = self._resolve_client_ip(request)
        decision = await cache_provider.consume_rate_limit_token(
            key=f'rate-limit:{client_ip}',
            capacity=_CAPACITY,
            refill_per_second=_REFILL_PER_SECOND,
        )

        if not decision.allowed:
            error = RateLimitError(
                message='Você excedeu o limite de solicitações. Tente novamente em '
                f'{decision.retry_after_seconds} segundo(s).'
            )
            return Response(
                status_code=429,
                content=json.dumps({'title': error.title, 'message': error.message}),
                media_type='application/json',
                headers={'Retry-After': str(decision.retry_after_seconds)},
            )

        return await call_next(request)

    def _resolve_client_ip(self, request: Request) -> str:
        peer_ip = request.client.host if request.client else ''
        if not self._is_trusted_proxy(peer_ip):
            return peer_ip

        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip.strip()

        return peer_ip

    def _is_trusted_proxy(self, peer_ip: str) -> bool:
        if not peer_ip or not self._trusted_networks:
            return False
        try:
            address = ipaddress.ip_address(peer_ip)
        except ValueError:
            return False
        return any(address in network for network in self._trusted_networks)


def _parse_trusted_networks(trusted_proxy_ips: list[str]) -> list[_IpNetwork]:
    networks: list[_IpNetwork] = []
    for raw in trusted_proxy_ips:
        try:
            networks.append(ipaddress.ip_network(raw, strict=False))
        except ValueError:
            continue
    return networks
