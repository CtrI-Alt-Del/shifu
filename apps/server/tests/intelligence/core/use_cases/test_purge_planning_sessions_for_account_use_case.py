from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest
from pydantic import TypeAdapter
from redis import Redis

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.intelligence.core.use_cases import PurgePlanningSessionsForAccountUseCase
from shifu.intelligence.providers.planning.redis.redis_planning_sessions_repository import (
    RedisPlanningSessionsRepository,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from tests.fixtures.redis_fixture import RedisFixture


class TestPurgePlanningSessionsForAccountUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.subject = PurgePlanningSessionsForAccountUseCase(self.sessions)

    def test_should_remove_all_sessions_for_the_account(self) -> None:
        self.sessions.remove_by_account_id.return_value = 3

        count = self.subject.execute('account-1')

        assert count == 3
        self.sessions.remove_by_account_id.assert_called_once_with('account-1')

    def test_should_reject_a_blank_account_id(self) -> None:
        with pytest.raises(ValueError, match='account id is required'):
            self.subject.execute('  ')

        self.sessions.remove_by_account_id.assert_not_called()

    def test_should_purge_indexed_and_legacy_sessions_for_only_one_account(
        self, redis_fixture: 'RedisFixture'
    ) -> None:
        identifiers = SystemIdentifierProvider()
        account_id = identifiers.generate()
        other_account_id = identifiers.generate()
        client = redis_fixture.client
        sessions = RedisPlanningSessionsRepository(client, 3600)
        indexed_session = _planning_session(identifiers.generate(), account_id)
        other_session = _planning_session(identifiers.generate(), other_account_id)
        legacy_session = _planning_session(identifiers.generate(), account_id)
        sessions.add(indexed_session)
        sessions.add(other_session)
        _add_legacy_session(client, legacy_session)
        subject = PurgePlanningSessionsForAccountUseCase(sessions)

        removed = subject.execute(account_id)

        assert removed == 2
        assert sessions.find_by_id(indexed_session.id) is None
        assert sessions.find_by_id(legacy_session.id) is None
        assert sessions.find_by_id(other_session.id) == other_session


def _planning_session(planning_id: str, account_id: str) -> PlanningSession:
    return PlanningSession.start(
        planning_id,
        account_id,
        'revision-1',
        'Study Python',
        'operation-1',
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def _add_legacy_session(client: Redis, session: PlanningSession) -> None:
    document = TypeAdapter(PlanningSession).dump_json(session).decode()
    client.hset(
        f'shifu:planning:{session.id}',
        mapping={'version': session.version, 'document': document},
    )
    client.expire(f'shifu:planning:{session.id}', 3600)
