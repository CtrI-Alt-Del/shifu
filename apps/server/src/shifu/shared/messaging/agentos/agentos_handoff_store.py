"""Short-lived private inputs and results kept out of durable AgentOS records."""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock


@dataclass(slots=True)
class _Handoff:
    capability: str
    input_value: object
    expires_at: datetime
    result_value: object | None = None


class AgentOSHandoffStore:
    """Keep private inference material in-process behind one-use opaque handles."""

    _DEFAULT_TTL: timedelta = timedelta(minutes=2)

    def __init__(self) -> None:
        self._lock = RLock()
        self._items: dict[str, _Handoff] = {}

    def create(
        self,
        *,
        capability: str,
        input_value: object,
        ttl: timedelta | None = None,
    ) -> str:
        if not capability:
            raise ValueError('A handoff capability is required')
        now = datetime.now(UTC)
        effective_ttl = ttl if ttl is not None else AgentOSHandoffStore._DEFAULT_TTL
        expires_at = now + effective_ttl
        if expires_at <= now:
            raise ValueError('Handoff lifetime must be positive')
        reference = secrets.token_urlsafe(32)
        with self._lock:
            self._expire(now)
            self._items[reference] = _Handoff(capability, input_value, expires_at)
        return reference

    def read_input(self, reference: str, *, capability: str) -> object:
        with self._lock:
            item = self._find(reference, capability)
            value = item.input_value
            item.input_value = None
            return value

    def complete(
        self, reference: str, *, capability: str, result_value: object
    ) -> bool:
        with self._lock:
            item = self._find(reference, capability)
            item.input_value = None
            item.result_value = result_value
            return True

    def take_result(self, reference: str, *, capability: str) -> object | None:
        with self._lock:
            item = self._find(reference, capability)
            result = item.result_value
            self._items.pop(reference, None)
            return result

    def discard(self, reference: str) -> None:
        with self._lock:
            self._items.pop(reference, None)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def _find(self, reference: str, capability: str) -> _Handoff:
        item = self._items.get(reference)
        if item is None or item.expires_at <= datetime.now(UTC):
            self._items.pop(reference, None)
            raise KeyError('Handoff is unavailable')
        if not secrets.compare_digest(item.capability, capability):
            raise KeyError('Handoff is unavailable')
        return item

    def _expire(self, now: datetime) -> None:
        expired = [
            reference
            for reference, item in self._items.items()
            if item.expires_at <= now
        ]
        for reference in expired:
            self._items.pop(reference, None)
