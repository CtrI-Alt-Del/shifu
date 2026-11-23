from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import create_autospec

import pytest
from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.core.domain.errors import MentorSessionNotFoundError
from shifu.intelligence.core.domain.structures import (
    MentorMessageAiCharge,
    MentorMessageAiUsage,
    MentorSessionAiUsage,
)
from shifu.intelligence.core.interfaces import (
    AiQuotaChargesRepository,
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorSessionsRepository,
)
from shifu.intelligence.core.use_cases import GetMentorSessionAiUsageUseCase
from shifu.shared.core.domain.errors import AuthorizationError, ServiceUnavailableError
from shifu.shared.core.interfaces import MentorAccessProvider


def _charge(message_id: str, units: int, limit: int = 1000) -> MentorMessageAiCharge:
    return MentorMessageAiCharge(
        message_id=message_id,
        attempt_id=f'attempt-{message_id}',
        charged_units=units,
        limit_units=limit,
    )


def _usage(message_id: str, percentage: str) -> MentorMessageAiUsage:
    return MentorMessageAiUsage(
        message_id=message_id,
        attempt_id=f'attempt-{message_id}',
        percentage=Decimal(percentage),
    )


class TestGetMentorSessionAiUsageUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        now = datetime(2026, 10, 10, tzinfo=UTC)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.sessions = create_autospec(MentorSessionsRepository, instance=True)
        self.charges = create_autospec(AiQuotaChargesRepository, instance=True)
        self.repositories.mentor_sessions = self.sessions
        self.repositories.ai_quota_charges = self.charges
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.sessions.find_by_id.return_value = MentorSession(
            id='session',
            account_id='account',
            title='title',
            created_at=now,
            updated_at=now,
            last_activity_at=now,
        )
        self.charges.find_many_by_mentor_session.return_value = ()
        self.subject = GetMentorSessionAiUsageUseCase(self.database, self.access)

    def test_should_return_the_share_of_the_month_limit_of_each_answer(self) -> None:
        self.charges.find_many_by_mentor_session.return_value = (
            _charge('m02', 42),
            _charge('m04', 250),
        )

        usage = self.subject.execute('account', 'session')

        assert usage == MentorSessionAiUsage(
            items=(
                _usage('m02', '4.20'),
                _usage('m04', '25.00'),
            )
        )
        self.access.authorize.assert_called_once_with('account', 'read:session')
        self.sessions.find_by_id.assert_called_once_with('account', 'session')
        self.charges.find_many_by_mentor_session.assert_called_once_with(
            'account', 'session'
        )

    def test_should_round_a_tiny_share_up_so_it_never_reads_zero(self) -> None:
        self.charges.find_many_by_mentor_session.return_value = (
            _charge('m02', 3, limit=1_000_000),
        )

        usage = self.subject.execute('account', 'session')

        assert usage.items == (_usage('m02', '0.01'),)

    def test_should_use_the_limit_of_each_charge_month_and_add_them(self) -> None:
        self.charges.find_many_by_mentor_session.return_value = (
            _charge('m02', 100, limit=1000),
            _charge('m02', 100, limit=2000),
        )

        usage = self.subject.execute('account', 'session')

        assert usage.items == (_usage('m02', '15.00'),)

    def test_should_leave_out_answers_that_spent_nothing(self) -> None:
        self.charges.find_many_by_mentor_session.return_value = (_charge('m02', 0),)

        assert self.subject.execute('account', 'session').items == ()

    def test_should_refuse_a_session_the_account_does_not_own(self) -> None:
        self.sessions.find_by_id.return_value = None

        with pytest.raises(MentorSessionNotFoundError):
            self.subject.execute('account', 'session')

        self.charges.find_many_by_mentor_session.assert_not_called()

    def test_should_not_read_anything_when_access_is_revoked(self) -> None:
        self.access.assert_current.side_effect = AuthorizationError()

        with pytest.raises(AuthorizationError):
            self.subject.execute('account', 'session')

        self.database.transaction.assert_not_called()

    def test_should_not_read_anything_when_access_is_unavailable(self) -> None:
        self.access.authorize.side_effect = ServiceUnavailableError()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('account', 'session')

        self.database.transaction.assert_not_called()
