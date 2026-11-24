import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
import inspect
from collections.abc import Callable
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest

from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
    MentorActionProposalStatus,
)
from shifu.intelligence.database.sqlalchemy.models import MentorActionProposalModel
from shifu.identity.core.domain.enums import AccountDeletionReason, AccountStatus
from shifu.identity.database.sqlalchemy.models import AccountModel
from shifu.intelligence.messaging.inngest.jobs import RecordMentorActionOutcomeJob
from shifu.learning.core.domain.events import (
    MentorSkillActionResolvedEvent,
    MentorSkillActionResolvedPayload,
)
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.interfaces import AccountActivityProvider
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.mentor_action_proposal_seed import seed_mentor_action_proposal

if TYPE_CHECKING:
    from inngest import Inngest

    from sqlalchemy.orm import Session

    from shifu.intelligence.core.domain.entities import MentorActionProposal
    from tests.fixtures.inngest_fixture import InngestFixture

_RESOLVED_AT = datetime(2026, 1, 2, tzinfo=UTC)
_GOAL_ID = '01J00000000000000000000GOA'
_EXPERIENCE_ID = '01J00000000000000000000EXP'


class _DeniedActivityScope:
    async def __aenter__(self) -> None:
        raise AuthorizationError

    async def __aexit__(self, *_: object) -> None:
        return None


class _RegistrationFake:
    def create_function(self, **_: object) -> Callable[[Callable[..., Any]], Any]:
        return lambda function: function


class _StepRunner:
    def __init__(self) -> None:
        self.outputs: dict[str, object] = {}

    async def run(
        self, step_name: str, callback: Callable[..., Any], *args: Any
    ) -> Any:
        result = callback(*args)
        if inspect.isawaitable(result):
            result = await result
        self.outputs[step_name] = result
        return result


def _state(session: 'Session', proposal_id: str) -> MentorActionProposalModel:
    session.expire_all()
    model = session.get(MentorActionProposalModel, proposal_id)
    assert model is not None
    return model


def _seed_identity_account(
    fixture: 'InngestFixture', account_id: str, *, deleted: bool = False
) -> None:
    now = datetime.now(UTC)
    with fixture.inspection_session() as session:
        session.add(
            AccountModel(
                id=account_id,
                display_name='Test learner',
                email=f'{account_id}@example.test',
                password_hash='!disabled!' if deleted else 'test-password-hash',
                status=(
                    AccountStatus.DELETED.value
                    if deleted
                    else AccountStatus.ACTIVE.value
                ),
                access_version=2 if deleted else 1,
                created_at=now,
                updated_at=now,
                confirmed_at=None if deleted else now,
                deleted_at=now if deleted else None,
                deletion_reason=(
                    AccountDeletionReason.USER_REQUESTED.value if deleted else None
                ),
            )
        )
        session.commit()


def _seed_active_mentor_action_proposal(
    fixture: 'InngestFixture',
    ids: SystemIdentifierProvider,
    account_id: str,
    **kwargs: Any,
) -> 'MentorActionProposal':
    _seed_identity_account(fixture, account_id)
    return seed_mentor_action_proposal(fixture, ids, account_id, **kwargs)


def _publish_outcome(
    fixture: 'InngestFixture',
    ids: SystemIdentifierProvider,
    proposal: 'MentorActionProposal',
    **changes: Any,
) -> str:
    """Publish the Learning event for ``proposal`` with the given payload overrides."""
    values: dict[str, Any] = {
        'account_id': proposal.account_id,
        'confirmation_id': proposal.id,
        'operation': proposal.kind.value,
        'outcome': 'added',
        'rejection_reason': None,
        'goal_id': proposal.goal_id or _GOAL_ID,
        'skill_id': proposal.skill_id,
        'skill_experience_id': _EXPERIENCE_ID,
        'resolved_at': _RESOLVED_AT.isoformat().replace('+00:00', 'Z'),
    }
    values.update(changes)
    event = MentorSkillActionResolvedEvent(
        payload=MentorSkillActionResolvedPayload(**values)
    )
    event_id = ids.generate()
    fixture.publish(event.name, asdict(event.payload), event_id=event_id)
    return event_id


def _finish_with_sentinel(
    fixture: 'InngestFixture', ids: SystemIdentifierProvider
) -> None:
    """Publish a valid outcome for a sentinel proposal and wait until it is recorded.

    Deliveries are handled in order, so the earlier events were processed by then.
    """
    sentinel = _seed_active_mentor_action_proposal(fixture, ids, ids.generate())
    _publish_outcome(fixture, ids, sentinel)
    fixture.wait_for_database(
        lambda session: (
            _state(session, sentinel.id).status
            == MentorActionProposalStatus.COMPLETED.value
        )
    )


class TestRecordMentorActionOutcomeJob:
    def test_should_skip_closed_account_and_keep_account_id_out_of_step_output(
        self,
    ) -> None:
        account_id = 'closed-account'
        data: dict[str, object] = {
            'account_id': account_id,
            'confirmation_id': 'confirmation',
            'operation': 'add_skill',
            'outcome': 'added',
            'rejection_reason': None,
            'goal_id': 'goal',
            'skill_id': 'skill',
            'skill_experience_id': 'experience',
            'resolved_at': '2026-01-02T00:00:00Z',
        }
        activity_provider = Mock(spec=AccountActivityProvider)
        activity_provider.async_activity.return_value = _DeniedActivityScope()
        use_case = Mock()
        handler = cast(
            'Callable[..., Any]',
            RecordMentorActionOutcomeJob.handle(
                cast('Inngest', _RegistrationFake()),
                use_case,
                outcome_event_name='learning/mentor-skill-action-resolved',
                account_activity_provider=activity_provider,
                telemetry_provider=Mock(spec=TelemetryProvider),
            ),
        )
        context = SimpleNamespace(
            attempt=0,
            run_id='run-id',
            event=SimpleNamespace(id='event-id', data=data),
            step=_StepRunner(),
        )

        asyncio.run(handler(context))

        activity_provider.async_activity.assert_called_once_with(account_id)
        use_case.execute.assert_not_called()
        normalized = context.step.outputs['normalize_payload']
        assert isinstance(normalized, dict)
        assert 'account_id' not in normalized

    def test_should_complete_a_pending_addition(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = _seed_active_mentor_action_proposal(
            inngest_fixture, ids, ids.generate()
        )

        _publish_outcome(inngest_fixture, ids, proposal)

        inngest_fixture.wait_for_database(
            lambda session: (
                _state(session, proposal.id).status
                == MentorActionProposalStatus.COMPLETED.value
            )
        )
        with inngest_fixture.inspection_session() as session:
            model = _state(session, proposal.id)
            assert model.outcome == MentorActionProposalOutcome.ADDED.value
            assert model.rejection_reason is None
            assert model.resolved_goal_id == proposal.goal_id
            assert model.resolved_skill_experience_id == _EXPERIENCE_ID

    def test_should_complete_a_pending_removal_with_its_experience(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        removal = _seed_active_mentor_action_proposal(
            inngest_fixture,
            ids,
            ids.generate(),
            kind=MentorActionKind.REMOVE_SKILL,
        )

        _publish_outcome(
            inngest_fixture,
            ids,
            removal,
            outcome='removed',
            skill_experience_id=removal.skill_experience_id,
        )

        inngest_fixture.wait_for_database(
            lambda session: (
                _state(session, removal.id).status
                == MentorActionProposalStatus.COMPLETED.value
            )
        )
        with inngest_fixture.inspection_session() as session:
            model = _state(session, removal.id)
            assert model.outcome == MentorActionProposalOutcome.REMOVED.value
            assert model.resolved_skill_experience_id == removal.skill_experience_id

    def test_should_reject_a_pending_proposal_with_the_reason(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = _seed_active_mentor_action_proposal(
            inngest_fixture, ids, ids.generate()
        )

        _publish_outcome(
            inngest_fixture,
            ids,
            proposal,
            outcome='rejected',
            rejection_reason=MentorActionProposalRejectionReason.SKILL_UNAVAILABLE.value,
            skill_experience_id=None,
        )

        inngest_fixture.wait_for_database(
            lambda session: (
                _state(session, proposal.id).status
                == MentorActionProposalStatus.REJECTED.value
            )
        )
        with inngest_fixture.inspection_session() as session:
            model = _state(session, proposal.id)
            assert model.outcome is None
            assert (
                model.rejection_reason
                == MentorActionProposalRejectionReason.SKILL_UNAVAILABLE.value
            )

    def test_should_let_the_outcome_replace_a_declined_proposal(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        declined = _seed_active_mentor_action_proposal(
            inngest_fixture,
            ids,
            ids.generate(),
            status=MentorActionProposalStatus.DECLINED,
        )

        _publish_outcome(inngest_fixture, ids, declined, outcome='already_present')

        inngest_fixture.wait_for_database(
            lambda session: (
                _state(session, declined.id).status
                == MentorActionProposalStatus.COMPLETED.value
            )
        )
        with inngest_fixture.inspection_session() as session:
            assert (
                _state(session, declined.id).outcome
                == MentorActionProposalOutcome.ALREADY_PRESENT.value
            )

    def test_should_ignore_unknown_ids_other_accounts_and_mismatched_values(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        proposal = _seed_active_mentor_action_proposal(inngest_fixture, ids, account_id)

        _publish_outcome(inngest_fixture, ids, proposal, confirmation_id=ids.generate())
        _publish_outcome(inngest_fixture, ids, proposal, account_id=ids.generate())
        _publish_outcome(
            inngest_fixture,
            ids,
            proposal,
            operation='remove_skill',
            outcome='removed',
        )
        _publish_outcome(inngest_fixture, ids, proposal, skill_id=ids.generate())
        _publish_outcome(inngest_fixture, ids, proposal, goal_id=ids.generate())
        _finish_with_sentinel(inngest_fixture, ids)

        with inngest_fixture.inspection_session() as session:
            model = _state(session, proposal.id)
            assert model.status == MentorActionProposalStatus.PENDING.value
            assert model.outcome is None
            assert model.resolved_goal_id is None

    def test_should_leave_pending_proposal_unchanged_after_account_closes(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, account_id)
        _seed_identity_account(inngest_fixture, account_id, deleted=True)

        _publish_outcome(inngest_fixture, ids, proposal)
        _finish_with_sentinel(inngest_fixture, ids)

        with inngest_fixture.inspection_session() as session:
            model = _state(session, proposal.id)
            assert model.status == MentorActionProposalStatus.PENDING.value
            assert model.outcome is None

    def test_should_change_nothing_on_a_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = _seed_active_mentor_action_proposal(
            inngest_fixture, ids, ids.generate()
        )
        _publish_outcome(inngest_fixture, ids, proposal)
        inngest_fixture.wait_for_database(
            lambda session: (
                _state(session, proposal.id).status
                == MentorActionProposalStatus.COMPLETED.value
            )
        )
        with inngest_fixture.inspection_session() as session:
            recorded_at = _state(session, proposal.id).updated_at

        _publish_outcome(inngest_fixture, ids, proposal)
        _publish_outcome(
            inngest_fixture,
            ids,
            proposal,
            outcome='rejected',
            rejection_reason='goal_unavailable',
            skill_experience_id=None,
        )
        _finish_with_sentinel(inngest_fixture, ids)

        with inngest_fixture.inspection_session() as session:
            model = _state(session, proposal.id)
            assert model.status == MentorActionProposalStatus.COMPLETED.value
            assert model.outcome == MentorActionProposalOutcome.ADDED.value
            assert model.updated_at == recorded_at

    def test_should_reject_invalid_payloads_as_non_retriable_without_recording(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = _seed_active_mentor_action_proposal(
            inngest_fixture, ids, ids.generate()
        )
        event = MentorSkillActionResolvedEvent(
            payload=MentorSkillActionResolvedPayload(
                account_id=proposal.account_id,
                confirmation_id=proposal.id,
                operation=proposal.kind.value,
                outcome='added',
                rejection_reason=None,
                goal_id=_GOAL_ID,
                skill_id=proposal.skill_id,
                skill_experience_id=_EXPERIENCE_ID,
                resolved_at=_RESOLVED_AT.isoformat().replace('+00:00', 'Z'),
            )
        )
        event_id = ids.generate()

        inngest_fixture.publish(
            event.name,
            {**asdict(event.payload), 'unexpected': 'must be rejected'},
            event_id=event_id,
        )

        failure_log = inngest_fixture.wait_for_log(
            f'"event":"job.failed","event_id":"{event_id}",'
            '"exception_type":"NonRetriableError",'
            '"job":"intelligence.record_mentor_action_outcome"'
        )
        assert '"job":"intelligence.record_mentor_action_outcome"' in failure_log
        assert '"exception_type":"NonRetriableError"' in failure_log
        with inngest_fixture.inspection_session() as session:
            model = _state(session, proposal.id)
            assert model.status == MentorActionProposalStatus.PENDING.value

    @pytest.mark.parametrize(
        'changes',
        [
            {'resolved_at': '2026-01-02T00:00:00'},
            {'resolved_at': '2026-01-02T00:00:00+03:00'},
            {'operation': 'archive_skill'},
            {'outcome': 'rejected'},
            {'rejection_reason': 'goal_unavailable'},
            {'confirmation_id': ' '},
        ],
    )
    def test_should_reject_values_outside_the_contract(
        self, inngest_fixture: 'InngestFixture', changes: dict[str, str]
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = _seed_active_mentor_action_proposal(
            inngest_fixture, ids, ids.generate()
        )

        event_id = _publish_outcome(inngest_fixture, ids, proposal, **changes)

        failure_log = inngest_fixture.wait_for_log(
            f'"event":"job.failed","event_id":"{event_id}",'
            '"exception_type":"NonRetriableError",'
            '"job":"intelligence.record_mentor_action_outcome"'
        )
        assert '"job":"intelligence.record_mentor_action_outcome"' in failure_log
        assert '"exception_type":"NonRetriableError"' in failure_log
        with inngest_fixture.inspection_session() as session:
            assert (
                _state(session, proposal.id).status
                == MentorActionProposalStatus.PENDING.value
            )
