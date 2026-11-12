from unittest.mock import Mock, create_autospec

import pytest

from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    PlanningOperationKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    AiQuotaExhaustedError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.events import (
    PlanningOperationRequestedEvent,
    PlanningOperationRequestedPayload,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    PlanningSessionsRepository,
)
from shifu.intelligence.core.use_cases import StartPlanningUseCase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)

from tests.fixtures.curriculum_planning_boundary_fixture import (
    BOUNDARY_NOW,
    BOUNDARY_OPERATION_ID,
    BOUNDARY_PLANNING_ID,
    boundary_session,
    boundary_start,
)
from tests.intelligence.core.use_cases.ai_quota_test_setup import (
    QUOTA_LIMIT,
    QUOTA_MONTH,
    AiQuotaTestSetup,
)
from tests.intelligence.core.use_cases.planning_test_setup import (
    ACCESS_REVISION,
    ACCOUNT_ID,
    NOW,
    OPERATION_ID,
    PLANNING_ID,
)


class TestStartPlanningUseCase(AiQuotaTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.sessions = create_autospec(PlanningSessionsRepository, instance=True)
        self.database = create_autospec(IntelligenceDatabase, instance=True)
        self.repositories = create_autospec(
            IntelligenceDatabaseRepositories, instance=True
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.prepare_quota(self.repositories, account_id=ACCOUNT_ID)
        self.access = create_autospec(MentorAccessProvider, instance=True)
        self.access.authorize.return_value = MentorAccessGrant(
            account_id=ACCOUNT_ID,
            access_revision=ACCESS_REVISION,
            operation_key=PLANNING_ID,
        )
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.identifiers.generate.side_effect = [PLANNING_ID, OPERATION_ID]
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.use_case = StartPlanningUseCase(
            self.sessions,
            self.database,
            self.access,
            self.identifiers,
            self.clock,
            self.quota_policy,
            self.quota_calendar,
        )

    def test_should_store_a_processing_planning_and_request_its_first_operation(
        self,
    ) -> None:
        session = self.use_case.execute(ACCOUNT_ID, '  Quero aprender  web ')

        assert session.id == PLANNING_ID
        assert session.account_id == ACCOUNT_ID
        assert session.access_revision == ACCESS_REVISION
        assert session.intent == 'Quero aprender web'
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.generation == 1
        assert session.version == 0
        assert session.batch is None
        assert session.answered_batch_count == 0
        assert session.operation is not None
        assert session.operation.id == OPERATION_ID
        assert session.operation.kind is PlanningOperationKind.START
        assert session.created_at == NOW
        self.access.authorize.assert_called_once_with(ACCOUNT_ID, PLANNING_ID)
        self.sessions.add.assert_called_once_with(session)
        self.repositories.events.add.assert_called_once_with(
            PlanningOperationRequestedEvent(
                payload=PlanningOperationRequestedPayload(
                    planning_id=PLANNING_ID, operation_id=OPERATION_ID, generation=1
                )
            )
        )

    def test_should_not_request_an_operation_when_the_planning_cannot_be_stored(
        self,
    ) -> None:
        self.sessions.add.side_effect = PlanningStateConflictError

        with pytest.raises(PlanningStateConflictError):
            self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.repositories.events.add.assert_not_called()

    def test_should_not_store_anything_when_the_account_is_not_authorized(
        self,
    ) -> None:
        self.access.authorize.side_effect = AuthorizationError

        with pytest.raises(AuthorizationError):
            self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.sessions.add.assert_not_called()
        self.database.transaction.assert_not_called()

    @pytest.mark.parametrize('intent', ['', '   ', 'x' * 4001])
    def test_should_reject_invalid_intent_without_storing_or_publishing(
        self, intent: str
    ) -> None:
        with pytest.raises(ValueError, match='intent'):
            self.use_case.execute(ACCOUNT_ID, intent)

        self.sessions.add.assert_not_called()
        self.database.transaction.assert_not_called()

    def test_should_admit_the_first_operation_before_the_planning_reaches_redis(
        self,
    ) -> None:
        effects = Mock()
        effects.attach_mock(self.quota_months.ensure_and_lock, 'lock_month')
        effects.attach_mock(self.quota_charges.add, 'add_charge')
        effects.attach_mock(self.database.transaction.return_value.__exit__, 'commit')
        effects.attach_mock(self.sessions.add, 'redis_write')
        effects.attach_mock(self.repositories.events.add, 'add_event')

        self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        assert [entry[0] for entry in effects.mock_calls] == [
            'lock_month',
            'add_charge',
            'commit',
            'redis_write',
            'add_event',
            'commit',
        ]
        self.quota_months.ensure_and_lock.assert_called_once_with(
            ACCOUNT_ID, QUOTA_MONTH, QUOTA_LIMIT, NOW
        )
        charge = self.quota_charges.add.call_args.args[0]
        assert charge.request_kind is AiQuotaRequestKind.PLANNING_OPERATION
        assert charge.request_id == OPERATION_ID
        assert charge.account_id == ACCOUNT_ID
        assert charge.month == QUOTA_MONTH
        assert charge.charged_units == 0

    @pytest.mark.parametrize(
        'used_units', [QUOTA_LIMIT, QUOTA_LIMIT + 1, 5 * QUOTA_LIMIT]
    )
    def test_should_refuse_at_or_above_the_limit_without_storing_or_publishing(
        self, used_units: int
    ) -> None:
        self.quota_month.used_units = used_units

        with pytest.raises(AiQuotaExhaustedError):
            self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.sessions.add.assert_not_called()
        self.quota_charges.add.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_admit_a_start_while_the_use_is_still_below_the_limit(self) -> None:
        self.quota_month.used_units = QUOTA_LIMIT - 1

        self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.quota_charges.add.assert_called_once()
        self.sessions.add.assert_called_once()
        self.repositories.events.add.assert_called_once()

    def test_should_not_open_the_month_for_an_unauthorized_account(self) -> None:
        self.access.authorize.side_effect = AuthorizationError

        with pytest.raises(AuthorizationError):
            self.use_case.execute(ACCOUNT_ID, 'Quero aprender web')

        self.quota_months.ensure_and_lock.assert_not_called()


class TestStartPlanningMigratedTransitions:
    def test_should_start_processing_with_a_normalized_intent(self) -> None:
        session = boundary_session()
        assert session.intent == 'Quero aprender web'
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.generation == 1
        assert session.version == 0
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.START
        assert session.batch is None
        assert session.answered_batch_count == 0

    @pytest.mark.parametrize('intent', ['', '   ', 'x' * 4001])
    def test_should_reject_a_blank_or_oversized_intent(self, intent: str) -> None:
        with pytest.raises(ValueError, match='intent'):
            boundary_start(
                BOUNDARY_PLANNING_ID,
                'account-1',
                'rev',
                intent,
                BOUNDARY_OPERATION_ID,
                BOUNDARY_NOW,
            )
