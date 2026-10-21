"""Durable outbox relay for one module-owned AgentOS queue."""

import secrets
from collections.abc import Callable, Generator, Mapping
from contextlib import AbstractContextManager, contextmanager
from datetime import timedelta
from threading import Event as ThreadEvent
from threading import Lock, Thread, current_thread
from typing import ClassVar, Literal, cast

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
from shifu.shared.messaging.agentos.agentos_client import AgentOSClient
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

RepositoryScope = Callable[[], AbstractContextManager[EventsRepository]]
WorkflowEventProjector = Callable[[OutboxEvent], tuple[str, Mapping[str, str]] | None]
AgentOSModule = Literal['intelligence', 'learning']


class AgentOSBroker:
    """Submit only this module's reserved events to its durable AgentOS queue."""

    _DRAIN_LIMIT: ClassVar[int] = 100
    _RESERVATION_DURATION: ClassVar[timedelta] = timedelta(minutes=5)
    _MAX_IDLE_SECONDS: ClassVar[float] = 30.0
    _RETRY_DELAY: ClassVar[timedelta] = timedelta(seconds=5)
    _MAX_RETRY_DELAY: ClassVar[timedelta] = timedelta(minutes=5)

    def __init__(
        self,
        module: AgentOSModule,
        client: AgentOSClient,
        workflow_event_projector: WorkflowEventProjector,
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

        self._module = module
        self._destination = f'agentos:{module}'
        self._client = client
        self._project_event = workflow_event_projector
        self._repository_scope = repository_scope
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )
        self._instance_id = (
            instance_id or f'shifu-agentos-{module}-{secrets.token_hex(8)}'
        )
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
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._wake.clear()
        self._thread = Thread(
            target=self._run,
            name=f'shifu-agentos-{self._module}-broker',
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self._close_listener()
        thread = self._thread
        if thread is not None and thread is not current_thread():
            thread.join(timeout=2)
        self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect_listener()
                self._drain()
                self._wait_for_work()
            except Exception:  # noqa: BLE001 - reconnect after DB/transport failure.
                self._close_listener()
                if self._stop.is_set():
                    return
                self._stop.wait(1)

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
                deadline = repository.find_earliest_wakeup(
                    destination=self._destination,
                    now=now,
                )
            timeout = AgentOSBroker._MAX_IDLE_SECONDS
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
                repository.release_expired_reservations(
                    destination=self._destination,
                    now=now,
                )
                events = repository.reserve_available(
                    destination=self._destination,
                    now=now,
                    reserved_by=self._instance_id,
                    reservation_expires_at=(now + AgentOSBroker._RESERVATION_DURATION),
                    limit=AgentOSBroker._DRAIN_LIMIT,
                )
            if not events:
                return
            for event in events:
                if self._stop.is_set():
                    return
                self._deliver(event)

    def _deliver(self, event: OutboxEvent) -> None:
        try:
            self._submit_event(event)
        except Exception:  # noqa: BLE001 - only a static error code is persisted.
            self._mark_delivery_failed(event)
            return
        with self._repository_scope() as repository:
            repository.mark_published(
                event_id=event.id,
                destination=self._destination,
                reserved_by=self._instance_id,
                published_at=self._clock_provider.now(),
            )

    def _submit_event(self, event: OutboxEvent) -> None:
        projection = self._project_event(event)
        if projection is None:
            raise ValueError('No registered workflow for event')
        workflow_id, fields = projection
        receipt = self._client.submit_workflow(
            workflow_id=workflow_id,
            fields=fields,
            background=True,
            session_id=event.id,
        )
        run_id = receipt.get('run_id')
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('AgentOS admission returned no run identifier')

    def _mark_delivery_failed(self, event: OutboxEvent) -> None:
        now = self._clock_provider.now()
        with self._repository_scope() as repository:
            repository.mark_delivery_failed(
                event_id=event.id,
                destination=self._destination,
                reserved_by=self._instance_id,
                available_at=now + self._retry_delay(event.attempts),
                error_code='agentos_submission_error',
                terminal=False,
            )
        self._wake.set()

    @staticmethod
    def _retry_delay(attempts: int) -> timedelta:
        """Back off exponentially up to a ceiling; admission failures stay retryable."""
        exponent = min(max(attempts - 1, 0), 16)
        return min(
            AgentOSBroker._RETRY_DELAY * (2**exponent),
            AgentOSBroker._MAX_RETRY_DELAY,
        )

    def _close_listener(self) -> None:
        with self._listener_lock:
            listener = self._listener
            self._listener = None
        if listener is not None:
            listener.unlisten()
