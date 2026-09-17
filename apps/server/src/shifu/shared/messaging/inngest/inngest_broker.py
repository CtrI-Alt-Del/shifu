"""Durable PostgreSQL outbox relay for Inngest."""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from datetime import timedelta
import secrets
from threading import Event as ThreadEvent
from threading import Lock, Thread, current_thread
from typing import ClassVar, Literal, Protocol, cast
from importlib import import_module

from sqlalchemy.engine import Engine

from shifu.shared.core.interfaces import (
    ClockProvider,
    EventsRepository,
    EventsRepositoryListener,
    IdentifierProvider,
    OutboxEvent,
)
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


RepositoryScope = Callable[[], AbstractContextManager[EventsRepository]]


class _InngestClient(Protocol):
    def send_sync(self, event: object) -> object: ...


class InngestBroker:
    """Relay committed outbox rows without holding database locks over I/O."""

    _DRAIN_LIMIT: ClassVar[int] = 100
    _RESERVATION_DURATION: ClassVar[timedelta] = timedelta(minutes=5)
    _MAX_IDLE_SECONDS: ClassVar[float] = 30.0
    _MAX_ATTEMPTS: ClassVar[int] = 10
    _DELIVERY_BACKOFF_SECONDS: ClassVar[
        tuple[
            Literal[5],
            Literal[10],
            Literal[20],
            Literal[40],
            Literal[80],
            Literal[160],
            Literal[300],
        ]
    ] = (5, 10, 20, 40, 80, 160, 300)
    _RECONNECT_BACKOFF_SECONDS: ClassVar[
        tuple[Literal[1], Literal[2], Literal[4], Literal[8], Literal[16], Literal[30]]
    ] = (1, 2, 4, 8, 16, 30)

    def __init__(
        self,
        inngest_client: object,
        repository_scope: RepositoryScope | None = None,
        *,
        engine: Engine | None = None,
        events_repository: EventsRepository | None = None,
        id_provider: IdentifierProvider | None = None,
        instance_id: str | None = None,
        clock_provider: ClockProvider | None = None,
    ) -> None:
        if repository_scope is not None and (
            engine is not None or events_repository is not None
        ):
            raise ValueError(
                'repository_scope cannot be combined with engine or events_repository'
            )
        if engine is not None and events_repository is not None:
            raise ValueError('engine cannot be combined with events_repository')
        if repository_scope is None:
            if events_repository is not None:
                repository_scope = self._fixed_repository_scope(events_repository)
            elif engine is not None:
                repository_scope = self._sqlalchemy_repository_scope(engine)
            else:
                raise ValueError(
                    'An events repository scope or SQLAlchemy engine is required'
                )

        self._inngest_client = cast('_InngestClient', inngest_client)
        self._repository_scope = repository_scope
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )
        self._instance_id = instance_id or f'shifu-inngest-{secrets.token_hex(8)}'
        self._clock_provider = clock_provider or SystemClockProvider()
        self._stop = ThreadEvent()
        self._wake = ThreadEvent()
        self._listener_lock = Lock()
        self._listener: EventsRepositoryListener | None = None
        self._thread: Thread | None = None

    @staticmethod
    def _fixed_repository_scope(repository: EventsRepository) -> RepositoryScope:
        @contextmanager
        def scope() -> Generator[EventsRepository]:
            yield repository

        return cast('RepositoryScope', scope)

    def _sqlalchemy_repository_scope(self, engine: Engine) -> RepositoryScope:
        @contextmanager
        def scope() -> Generator[EventsRepository]:
            with Session.database_session(engine) as session:
                yield SqlalchemyEventsRepository(
                    session,
                    engine,
                    id_provider=self._id_provider,
                )

        return cast('RepositoryScope', scope)

    def start(self) -> None:
        """Start the listener and relay thread once."""

        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._wake.clear()
        self._thread = Thread(
            target=self._run,
            name='shifu-inngest-broker',
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the relay, unlisten, and release the listener connection."""

        self._stop.set()
        self._wake.set()
        self._close_listener()
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        reconnect_attempt = 0
        while not self._stop.is_set():
            try:
                self._connect_listener()
                reconnect_attempt = 0
                self._drain()
                self._wait_for_work()
            except Exception:  # noqa: BLE001 - reconnect must survive transport/database failures.
                self._close_listener()
                if self._stop.is_set():
                    return
                delay = InngestBroker._RECONNECT_BACKOFF_SECONDS[
                    min(
                        reconnect_attempt,
                        len(InngestBroker._RECONNECT_BACKOFF_SECONDS) - 1,
                    )
                ]
                reconnect_attempt += 1
                self._stop.wait(delay)

    def _connect_listener(self) -> None:
        with self._repository_scope() as repository:
            listener = repository.listen(self._on_notification)
        with self._listener_lock:
            self._listener = listener

    def _on_notification(self, _event_id: str) -> None:
        self._wake.set()

    def _wait_for_work(self) -> None:
        while not self._stop.is_set():
            now = self._clock_provider.now()
            with self._repository_scope() as repository:
                deadline = repository.find_earliest_wakeup(now=now)
            timeout = InngestBroker._MAX_IDLE_SECONDS
            if deadline is not None:
                timeout = min(timeout, max(0.0, (deadline - now).total_seconds()))
            self._wake.wait(timeout)
            self._wake.clear()
            if self._stop.is_set():
                return
            self._drain()

    def _drain(self) -> None:
        while not self._stop.is_set():
            now = self._clock_provider.now()
            with self._repository_scope() as repository:
                repository.release_expired_reservations(now=now)
                events = repository.reserve_available(
                    now=now,
                    reserved_by=self._instance_id,
                    reservation_expires_at=now + InngestBroker._RESERVATION_DURATION,
                    limit=InngestBroker._DRAIN_LIMIT,
                )
            if not events:
                return
            for event in events:
                if self._stop.is_set():
                    return
                self._deliver(event)

    def _deliver(self, event: OutboxEvent) -> None:
        try:
            self._inngest_client.send_sync(self._build_inngest_event(event))
        except Exception:  # noqa: BLE001 - failed delivery is persisted for retry.
            self._mark_delivery_failed(event, 'inngest_delivery_error')
            return
        with self._repository_scope() as repository:
            repository.mark_published(
                event_id=event.id,
                reserved_by=self._instance_id,
                published_at=self._clock_provider.now(),
            )

    @staticmethod
    def _build_inngest_event(event: OutboxEvent) -> object:
        sdk = import_module('inngest')
        event_type = getattr(sdk, 'Event')  # noqa: B009 - optional SDK import
        return event_type(name=event.name, data=dict(event.payload), id=event.id)

    def _mark_delivery_failed(self, event: OutboxEvent, error_code: str) -> None:
        terminal = event.attempts >= InngestBroker._MAX_ATTEMPTS
        if terminal:
            available_at = self._clock_provider.now()
        else:
            backoff_index = min(
                event.attempts - 1,
                len(InngestBroker._DELIVERY_BACKOFF_SECONDS) - 1,
            )
            available_at = self._clock_provider.now() + timedelta(
                seconds=InngestBroker._DELIVERY_BACKOFF_SECONDS[max(0, backoff_index)]
            )
        with self._repository_scope() as repository:
            repository.mark_delivery_failed(
                event_id=event.id,
                reserved_by=self._instance_id,
                available_at=available_at,
                error_code=error_code,
                terminal=terminal,
            )
        self._wake.set()

    def _close_listener(self) -> None:
        with self._listener_lock:
            listener = self._listener
            self._listener = None
        if listener is not None:
            listener.unlisten()
