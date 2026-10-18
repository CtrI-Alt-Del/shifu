from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event
from typing import TYPE_CHECKING, Protocol, cast

import pytest
from sqlalchemy import create_engine

from shifu.shared.core.interfaces import (
    ClockProvider,
    EventsRepository,
    EventsRepositoryListener,
    OutboxEvent,
)
from shifu.shared.messaging.agentos.agentos_broker import AgentOSBroker
from shifu.shared.messaging.inngest.inngest_broker import InngestBroker

if TYPE_CHECKING:
    from shifu.shared.messaging.agentos.agentos_client import AgentOSClient

_NOW = datetime(2026, 2, 3, 4, 5, tzinfo=UTC)


class _InngestEvent(Protocol):
    name: str
    id: str
    data: Mapping[str, object]


class _Clock:
    def now(self) -> datetime:
        return _NOW


class _Listener:
    def __init__(self) -> None:
        self.closed = False
        self._on_event: Callable[[str], None] | None = None

    def subscribe(self, on_event: Callable[[str], None]) -> None:
        self._on_event = on_event

    def notify(self, event_id: str) -> None:
        if self._on_event is not None:
            self._on_event(event_id)

    def unlisten(self) -> None:
        self.closed = True


class _Repository:
    def __init__(self, events: list[OutboxEvent]) -> None:
        self._events = events.copy()
        self._unrouted = [event for event in events if event.destination == 'unrouted']
        self._destinations: dict[str, str] = {}
        self._unrouted_read = False
        self.unrouted_scanned = Event()
        self.listener = _Listener()
        self.listener_ready = Event()
        self.wakeup_at: datetime | None = None
        self.wakeup_checked = Event()
        self.published: list[tuple[str, str, str, datetime]] = []
        self.failures: list[tuple[str, str, str, datetime, str, bool]] = []
        self.reserved_destinations: list[str] = []
        self.reservation_checked = Event()
        self.completed = Event()

    def listen(self, on_event: Callable[[str], None]) -> EventsRepositoryListener:
        self.listener.subscribe(on_event)
        self.listener_ready.set()
        return cast('EventsRepositoryListener', self.listener)

    def find_unrouted(self, *, now: datetime, limit: int) -> list[OutboxEvent]:
        del now, limit
        if self._unrouted_read:
            return []
        self._unrouted_read = True
        self.unrouted_scanned.set()
        return self._unrouted

    def assign_destination(self, *, event_id: str, destination: str) -> bool:
        self._destinations[event_id] = destination
        return True

    def release_expired_reservations(self, *, destination: str, now: datetime) -> int:
        del destination, now
        return 0

    def reserve_available(
        self,
        *,
        destination: str,
        now: datetime,
        reserved_by: str,
        reservation_expires_at: datetime,
        limit: int,
    ) -> list[OutboxEvent]:
        del now, reserved_by, reservation_expires_at
        self.reserved_destinations.append(destination)
        self.reservation_checked.set()
        selected = [
            event
            for event in self._events
            if self._destinations.get(event.id, event.destination) == destination
        ][:limit]
        self._events = [event for event in self._events if event not in selected]
        return selected

    def find_earliest_wakeup(
        self, *, destination: str, now: datetime
    ) -> datetime | None:
        del destination, now
        self.wakeup_checked.set()
        return self.wakeup_at

    def mark_published(
        self,
        *,
        event_id: str,
        destination: str,
        reserved_by: str,
        published_at: datetime,
    ) -> bool:
        self.published.append((event_id, destination, reserved_by, published_at))
        self.completed.set()
        return True

    def mark_delivery_failed(
        self,
        *,
        event_id: str,
        destination: str,
        reserved_by: str,
        available_at: datetime,
        error_code: str,
        terminal: bool,
    ) -> bool:
        self.failures.append(
            (event_id, destination, reserved_by, available_at, error_code, terminal)
        )
        self.completed.set()
        return True

    @property
    def assigned_destinations(self) -> dict[str, str]:
        return self._destinations.copy()


def _event(
    event_id: str,
    *,
    destination: str = 'unrouted',
    attempts: int = 1,
) -> OutboxEvent:
    return OutboxEvent(
        id=event_id,
        name='intelligence/mentor-attachment.cleanup.requested',
        payload={'account_id': 'account-1'},
        destination=destination,
        status='pending',
        attempts=attempts,
        available_at=_NOW,
        reserved_by=None,
        reservation_expires_at=None,
        last_error_code=None,
        created_at=_NOW,
        updated_at=_NOW,
        published_at=None,
    )


@contextmanager
def _repository_scope(repository: _Repository) -> Generator[EventsRepository]:
    yield cast('EventsRepository', repository)


class _InngestClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.events: list[object] = []
        self._fail = fail

    def send_sync(self, event: object) -> None:
        if self._fail:
            raise RuntimeError('transport unavailable')
        self.events.append(event)


class _AgentOSClient:
    def __init__(self, *, receipt: Mapping[str, object] | None = None) -> None:
        self.submissions: list[dict[str, object]] = []
        self._receipt = dict({'run_id': 'run-1'} if receipt is None else receipt)

    def submit_workflow(self, **request: object) -> dict[str, object]:
        self.submissions.append(request)
        return self._receipt


class TestOutboxBrokers:
    def test_brokers_require_one_repository_scope_source(self) -> None:
        repository = cast('EventsRepository', _Repository([]))
        client = _InngestClient()
        with pytest.raises(ValueError, match='repository_scope cannot be combined'):
            InngestBroker(
                client,
                lambda: _repository_scope(cast('_Repository', repository)),
                events_repository=repository,
                destination_resolver=lambda _event: 'inngest',
            )
        with pytest.raises(ValueError, match='An events repository scope'):
            InngestBroker(client, destination_resolver=lambda _event: 'inngest')
        with pytest.raises(ValueError, match='An events repository scope'):
            AgentOSBroker(
                'intelligence',
                cast('AgentOSClient', _AgentOSClient()),
                lambda _event: None,
            )

        engine = create_engine('sqlite+pysqlite:///:memory:')
        try:
            with pytest.raises(ValueError, match='engine cannot be combined'):
                InngestBroker(
                    client,
                    engine=engine,
                    events_repository=repository,
                    destination_resolver=lambda _event: 'inngest',
                )
            with pytest.raises(ValueError, match='repository_scope cannot be combined'):
                AgentOSBroker(
                    'learning',
                    cast('AgentOSClient', _AgentOSClient()),
                    lambda _event: None,
                    lambda: _repository_scope(cast('_Repository', repository)),
                    engine=engine,
                )
        finally:
            engine.dispose()

    def test_brokers_can_open_a_fixed_repository_scope(self) -> None:
        fake_repository = _Repository([])
        repository = cast('EventsRepository', fake_repository)
        inngest = InngestBroker(
            _InngestClient(),
            events_repository=repository,
            destination_resolver=lambda _event: 'inngest',
        )
        agentos = AgentOSBroker(
            'learning',
            cast('AgentOSClient', _AgentOSClient()),
            lambda _event: None,
            events_repository=repository,
        )

        inngest.start()
        agentos.start()
        try:
            assert fake_repository.reservation_checked.wait(timeout=2)
        finally:
            inngest.stop()
            agentos.stop()

        assert fake_repository.listener.closed

    def test_inngest_broker_routes_and_publishes_with_the_outbox_identity(self) -> None:
        repository = _Repository([_event('event-1')])
        repository.wakeup_at = _NOW + timedelta(seconds=10)
        client = _InngestClient()
        broker = InngestBroker(
            client,
            lambda: _repository_scope(repository),
            destination_resolver=lambda _event: 'inngest',
            instance_id='test-inngest-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )

        broker.start()
        broker.start()
        try:
            assert repository.listener_ready.wait(timeout=2)
            repository.listener.notify('event-1')
            assert repository.completed.wait(timeout=2)
            assert repository.wakeup_checked.wait(timeout=2)
        finally:
            broker.stop()

        assert repository.assigned_destinations == {'event-1': 'inngest'}
        assert repository.published == [
            ('event-1', 'inngest', 'test-inngest-relay', _NOW)
        ]
        assert len(client.events) == 1
        event = cast('_InngestEvent', client.events[0])
        assert event.name == 'intelligence/mentor-attachment.cleanup.requested'
        assert event.id == 'event-1'
        assert event.data == {'account_id': 'account-1'}
        assert repository.listener.closed
        broker.stop()

    @pytest.mark.parametrize(
        ('attempts', 'available_at', 'terminal'),
        [
            (3, _NOW + timedelta(seconds=20), False),
            (10, _NOW, True),
        ],
    )
    def test_inngest_broker_persists_retryable_and_terminal_delivery_failures(
        self,
        attempts: int,
        available_at: datetime,
        terminal: bool,
    ) -> None:
        repository = _Repository(
            [_event('event-2', destination='inngest', attempts=attempts)]
        )
        broker = InngestBroker(
            _InngestClient(fail=True),
            lambda: _repository_scope(repository),
            destination_resolver=lambda _event: 'inngest',
            instance_id='test-inngest-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )

        broker.start()
        broker.start()
        try:
            assert repository.listener_ready.wait(timeout=2)
            repository.listener.notify('event-4')
            assert repository.completed.wait(timeout=2)
        finally:
            broker.stop()

        assert repository.published == []
        assert repository.failures == [
            (
                'event-2',
                'inngest',
                'test-inngest-relay',
                available_at,
                'inngest_delivery_error',
                terminal,
            )
        ]

    def test_inngest_broker_keeps_unresolved_destinations_unrouted(self) -> None:
        repository = _Repository([_event('event-3'), _event('event-6')])

        def unresolved_destination(event: OutboxEvent) -> str | None:
            return None if event.id == 'event-3' else 'unrouted'

        def fail_resolution(_event: OutboxEvent) -> str | None:
            raise RuntimeError('event type not yet registered')

        broker = InngestBroker(
            _InngestClient(),
            lambda: _repository_scope(repository),
            destination_resolver=unresolved_destination,
            instance_id='test-inngest-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )
        broker.start()
        try:
            assert repository.unrouted_scanned.wait(timeout=2)
        finally:
            broker.stop()

        assert repository.assigned_destinations == {}

        error_repository = _Repository([_event('event-7')])
        error_broker = InngestBroker(
            _InngestClient(),
            lambda: _repository_scope(error_repository),
            destination_resolver=fail_resolution,
            instance_id='test-inngest-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )
        error_broker.start()
        try:
            assert error_repository.unrouted_scanned.wait(timeout=2)
        finally:
            error_broker.stop()
        assert error_repository.assigned_destinations == {}

    def test_agentos_broker_submits_only_the_module_queue_envelope(self) -> None:
        repository = _Repository([_event('event-4', destination='agentos:learning')])
        repository.wakeup_at = _NOW + timedelta(seconds=10)
        client = _AgentOSClient()
        broker = AgentOSBroker(
            'learning',
            cast('AgentOSClient', client),
            lambda event: ('evaluate-code-activity', {'event_id': event.id}),
            lambda: _repository_scope(repository),
            instance_id='test-learning-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )

        broker.start()
        try:
            assert repository.completed.wait(timeout=2)
            assert repository.wakeup_checked.wait(timeout=2)
        finally:
            broker.stop()

        assert repository.reserved_destinations == [
            'agentos:learning',
            'agentos:learning',
        ]
        assert client.submissions == [
            {
                'workflow_id': 'evaluate-code-activity',
                'fields': {'event_id': 'event-4'},
                'background': True,
                'session_id': 'event-4',
            }
        ]
        assert repository.published == [
            ('event-4', 'agentos:learning', 'test-learning-relay', _NOW)
        ]
        assert repository.listener.closed
        broker.stop()

    def test_agentos_broker_rejects_events_without_registered_workflows(self) -> None:
        repository = _Repository(
            [_event('event-8', destination='agentos:intelligence')]
        )
        client = _AgentOSClient()
        broker = AgentOSBroker(
            'intelligence',
            cast('AgentOSClient', client),
            lambda _event: None,
            lambda: _repository_scope(repository),
            instance_id='test-intelligence-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )

        broker.start()
        try:
            assert repository.completed.wait(timeout=2)
        finally:
            broker.stop()

        assert client.submissions == []
        assert repository.published == []
        assert repository.failures == [
            (
                'event-8',
                'agentos:intelligence',
                'test-intelligence-relay',
                _NOW + timedelta(seconds=5),
                'agentos_submission_error',
                False,
            )
        ]

    @pytest.mark.parametrize(
        ('receipt', 'attempts', 'available_at'),
        [
            ({}, 1, _NOW + timedelta(seconds=5)),
            ({'run_id': ''}, 2, _NOW + timedelta(seconds=10)),
            ({}, 3, _NOW + timedelta(seconds=20)),
            ({}, 7, _NOW + timedelta(seconds=300)),
            ({'run_id': ''}, 500, _NOW + timedelta(seconds=300)),
        ],
    )
    def test_agentos_broker_keeps_failed_admission_retryable_with_bounded_backoff(
        self,
        receipt: Mapping[str, object],
        attempts: int,
        available_at: datetime,
    ) -> None:
        repository = _Repository(
            [_event('event-5', destination='agentos:intelligence', attempts=attempts)]
        )
        broker = AgentOSBroker(
            'intelligence',
            cast('AgentOSClient', _AgentOSClient(receipt=receipt)),
            lambda _event: ('prepare-mentor-attachment', {'attachment_id': 'att-1'}),
            lambda: _repository_scope(repository),
            instance_id='test-intelligence-relay',
            clock_provider=cast('ClockProvider', _Clock()),
        )

        broker.start()
        try:
            assert repository.completed.wait(timeout=2)
        finally:
            broker.stop()

        assert repository.published == []
        assert repository.failures == [
            (
                'event-5',
                'agentos:intelligence',
                'test-intelligence-relay',
                available_at,
                'agentos_submission_error',
                False,
            )
        ]
