from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from shifu.shared.core.domain.events import Event
from shifu.shared.core.interfaces.events_repository_listener import (
    EventsRepositoryListener,
)
from shifu.shared.core.interfaces.outbox_event import OutboxEvent


class EventsRepository(Protocol):
    def add[Payload](
        self, event: Event[Payload], *, available_at: datetime | None = None
    ) -> None: ...

    def remove_by_account_id_and_names(
        self, account_id: str, event_names: set[str]
    ) -> int:
        """Remove outbox payloads owned by an account for the named events."""
        ...

    def remove_by_payload_values(
        self, event_name: str, field_name: str, values: set[str]
    ) -> int:
        """Remove rows for one event when a payload field matches owned IDs."""
        ...

    def listen(self, on_event: Callable[[str], None]) -> EventsRepositoryListener: ...

    def find_unrouted(self, *, now: datetime, limit: int) -> list[OutboxEvent]: ...

    def assign_destination(self, *, event_id: str, destination: str) -> bool: ...

    def release_expired_reservations(
        self, *, destination: str, now: datetime
    ) -> int: ...

    def reserve_available(
        self,
        *,
        destination: str,
        now: datetime,
        reserved_by: str,
        reservation_expires_at: datetime,
        limit: int,
    ) -> list[OutboxEvent]: ...

    def find_earliest_wakeup(
        self, *, destination: str, now: datetime
    ) -> datetime | None: ...

    def mark_published(
        self,
        *,
        event_id: str,
        destination: str,
        reserved_by: str,
        published_at: datetime,
    ) -> bool: ...

    def mark_delivery_failed(
        self,
        *,
        event_id: str,
        destination: str,
        reserved_by: str,
        available_at: datetime,
        error_code: str,
        terminal: bool,
    ) -> bool: ...
