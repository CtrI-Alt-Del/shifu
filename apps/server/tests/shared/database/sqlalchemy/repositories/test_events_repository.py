from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from shifu.shared.core.domain.events import Event
from shifu.shared.database.sqlalchemy.repositories.events_repository import (
    SqlalchemyEventsRepository,
)
from sqlalchemy.dialects import postgresql


def test_add_preserves_a_scheduled_outbox_availability_time() -> None:
    session = Mock()
    repository = SqlalchemyEventsRepository(session)
    available_at = datetime(2030, 1, 1, tzinfo=UTC)

    repository.add(
        Event(
            name='intelligence.mentor-attachment.cleanup-requested',
            payload={'event_id': '01JGFJJZ1K8TN92JCC77TZV8JQ'},
        ),
        available_at=available_at,
    )

    event_model = session.add.call_args.args[0]
    assert event_model.available_at == available_at
    assert event_model.destination == 'unrouted'


def test_unrouted_scan_does_not_return_events_before_their_deadline() -> None:
    session = Mock()
    session.scalars.return_value.all.return_value = []
    repository = SqlalchemyEventsRepository(session)
    now = datetime(2030, 1, 1, tzinfo=UTC)

    assert repository.find_unrouted(now=now, limit=10) == []

    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    assert 'events.available_at <= ' in str(compiled)
    assert now in compiled.params.values()


def test_add_rejects_payloads_that_do_not_serialize_to_an_object() -> None:
    repository = SqlalchemyEventsRepository(Mock())

    with pytest.raises(TypeError, match='JSON object'):
        repository.add(Event(name='test.event', payload=['invalid']))


def test_listen_requires_an_engine_when_the_session_has_no_engine() -> None:
    repository = SqlalchemyEventsRepository(Mock())

    with pytest.raises(TypeError, match='An Engine is required'):
        repository.listen(lambda _event_id: None)


def test_listen_uses_the_configured_engine_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine('sqlite+pysqlite:///:memory:')
    connection = Mock()
    connection.notifies.return_value = iter(())
    connect = Mock(return_value=connection)
    monkeypatch.setattr(
        'shifu.shared.database.sqlalchemy.repositories.events_repository.psycopg.connect',
        connect,
    )

    try:
        repository = SqlalchemyEventsRepository(Mock(), engine=engine)
        listener = repository.listen(lambda _event_id: None)

        assert listener is not None
        connect.assert_called_once()
        assert connect.call_args.args[0].startswith('postgresql://')
        listener.unlisten()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ('rowcount', 'expected'),
    ((0, False), (1, True)),
)
def test_assign_destination_only_notifies_when_the_event_was_routed(
    rowcount: int,
    expected: bool,
) -> None:
    session = Mock()
    session.execute.return_value.rowcount = rowcount
    repository = SqlalchemyEventsRepository(session)

    assert (
        repository.assign_destination(event_id='event-1', destination='agentos')
        is expected
    )

    assert session.execute.call_count == (2 if expected else 1)
    assert session.flush.called is expected


@pytest.mark.parametrize(
    ('terminal', 'rowcount', 'expected_status', 'expected_result'),
    ((False, 1, 'failed', True), (True, 0, 'terminal', False)),
)
def test_mark_delivery_failed_records_retry_or_terminal_state(
    terminal: bool,
    rowcount: int,
    expected_status: str,
    expected_result: bool,
) -> None:
    session = Mock()
    session.execute.return_value.rowcount = rowcount
    repository = SqlalchemyEventsRepository(session)
    available_at = datetime(2030, 1, 1, tzinfo=UTC)

    result = repository.mark_delivery_failed(
        event_id='event-1',
        destination='agentos',
        reserved_by='relay-1',
        available_at=available_at,
        error_code='remote_unavailable',
        terminal=terminal,
    )

    statement = session.execute.call_args.args[0]
    assert statement.compile(dialect=postgresql.dialect()).params['status'] == (
        expected_status
    )
    assert result is expected_result
    session.flush.assert_called_once()
