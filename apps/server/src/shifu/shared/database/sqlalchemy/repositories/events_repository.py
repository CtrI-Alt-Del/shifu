from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, cast

import psycopg
from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult, Engine
from sqlalchemy.orm import Session

from shifu.shared.core.domain.events import Event
from shifu.shared.core.interfaces import (
    EventsRepositoryListener,
    IdentifierProvider,
    OutboxEvent,
)
from shifu.shared.database.sqlalchemy.serialization import Serialization
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.database.sqlalchemy.repositories.listeners import (
    PostgresListenerConnection,
    SqlalchemyEventsRepositoryListener,
)


class SqlalchemyEventsRepository:
    def __init__(
        self,
        session: Session,
        engine: Engine | None = None,
        *,
        id_provider: IdentifierProvider | None = None,
    ) -> None:
        self._session = session
        self._engine = engine
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )

    def add[Payload](self, event: Event[Payload]) -> None:
        payload = Serialization.serialize_value(event.payload)
        if not isinstance(payload, dict):
            raise TypeError('Event payload must serialize to a JSON object')
        payload = cast('dict[str, object]', payload)
        event_id: object = payload.get('event_id')
        row_id = (
            event_id
            if isinstance(event_id, str) and event_id
            else self._id_provider.generate()
        )

        self._session.add(
            EventModel(
                id=row_id,
                name=event.name,
                payload=payload,
            )
        )
        self._session.flush()

    def listen(self, on_event: Callable[[str], None]) -> EventsRepositoryListener:
        if self._engine is not None:
            connection = psycopg.connect(
                self._engine.url.set(drivername='postgresql').render_as_string(
                    hide_password=False
                )
            )
        else:
            bind = self._session.get_bind()
            if not isinstance(bind, Engine):
                raise TypeError('An Engine is required to create an event listener')
            connection = bind.raw_connection()
        listener_connection = cast('PostgresListenerConnection', connection)
        return SqlalchemyEventsRepositoryListener(
            listener_connection,
            on_event,
        )

    def release_expired_reservations(self, *, now: datetime) -> int:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                update(EventModel)
                .where(
                    EventModel.status == 'publishing',
                    EventModel.reservation_expires_at <= now,
                )
                .values(
                    status='failed',
                    available_at=now,
                    reserved_by=None,
                    reservation_expires_at=None,
                    updated_at=now,
                )
            ),
        )
        self._session.flush()
        return result.rowcount

    def reserve_available(
        self,
        *,
        now: datetime,
        reserved_by: str,
        reservation_expires_at: datetime,
        limit: int,
    ) -> list[OutboxEvent]:
        models = self._session.scalars(
            select(EventModel)
            .where(
                EventModel.status.in_(['pending', 'failed']),
                EventModel.available_at <= now,
            )
            .order_by(EventModel.available_at, EventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        for model in models:
            model.status = 'publishing'
            model.attempts += 1
            model.reserved_by = reserved_by
            model.reservation_expires_at = reservation_expires_at
            model.updated_at = now
        self._session.flush()
        return [self._to_outbox_event(model) for model in models]

    def find_earliest_wakeup(self, *, now: datetime) -> datetime | None:
        available_at = self._session.scalar(
            select(func.min(EventModel.available_at)).where(
                EventModel.status.in_(['pending', 'failed']),
                EventModel.available_at > now,
            )
        )
        reservation_expires_at = self._session.scalar(
            select(func.min(EventModel.reservation_expires_at)).where(
                EventModel.status == 'publishing',
                EventModel.reservation_expires_at > now,
            )
        )
        values = [
            value
            for value in (available_at, reservation_expires_at)
            if isinstance(value, datetime)
        ]
        return min(values) if values else None

    def mark_published(
        self,
        *,
        event_id: str,
        reserved_by: str,
        published_at: datetime,
    ) -> bool:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                update(EventModel)
                .where(
                    EventModel.id == event_id,
                    EventModel.status == 'publishing',
                    EventModel.reserved_by == reserved_by,
                )
                .values(
                    status='published',
                    reserved_by=None,
                    reservation_expires_at=None,
                    published_at=published_at,
                    updated_at=published_at,
                )
            ),
        )
        self._session.flush()
        return result.rowcount == 1

    def mark_delivery_failed(
        self,
        *,
        event_id: str,
        reserved_by: str,
        available_at: datetime,
        error_code: str,
        terminal: bool,
    ) -> bool:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                update(EventModel)
                .where(
                    EventModel.id == event_id,
                    EventModel.status == 'publishing',
                    EventModel.reserved_by == reserved_by,
                )
                .values(
                    status='terminal' if terminal else 'failed',
                    available_at=available_at,
                    reserved_by=None,
                    reservation_expires_at=None,
                    last_error_code=error_code,
                    updated_at=available_at,
                )
            ),
        )
        self._session.flush()
        return result.rowcount == 1

    @staticmethod
    def _to_outbox_event(model: EventModel) -> OutboxEvent:
        payload = cast('Mapping[str, object]', model.payload)
        return OutboxEvent(
            id=model.id,
            name=model.name,
            payload=payload,
            status=model.status,
            attempts=model.attempts,
            available_at=model.available_at,
            reserved_by=model.reserved_by,
            reservation_expires_at=model.reservation_expires_at,
            last_error_code=model.last_error_code,
            created_at=model.created_at,
            updated_at=model.updated_at,
            published_at=model.published_at,
        )
