from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalRejectionReason,
    MentorActionProposalStatus,
)
from shifu.intelligence.database.sqlalchemy.models import MentorActionProposalModel
from shifu.learning.core.domain.events import (
    MentorSkillActionResolvedEvent,
    MentorSkillActionResolvedPayload,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.mentor_action_proposal_seed import seed_mentor_action_proposal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from shifu.intelligence.core.domain.entities import MentorActionProposal
    from tests.fixtures.inngest_fixture import InngestFixture

_RESOLVED_AT = datetime(2026, 1, 2, tzinfo=UTC)
_GOAL_ID = '01J00000000000000000000GOA'
_EXPERIENCE_ID = '01J00000000000000000000EXP'


def _state(session: 'Session', proposal_id: str) -> MentorActionProposalModel:
    session.expire_all()
    model = session.get(MentorActionProposalModel, proposal_id)
    assert model is not None
    return model


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
    sentinel = seed_mentor_action_proposal(fixture, ids, ids.generate())
    _publish_outcome(fixture, ids, sentinel)
    fixture.wait_for_database(
        lambda session: (
            _state(session, sentinel.id).status
            == MentorActionProposalStatus.COMPLETED.value
        )
    )


class TestRecordMentorActionOutcomeJob:
    def test_should_complete_a_pending_addition(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, ids.generate())

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
        removal = seed_mentor_action_proposal(
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
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, ids.generate())

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
        declined = seed_mentor_action_proposal(
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
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, account_id)

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

    def test_should_change_nothing_on_a_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, ids.generate())
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
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, ids.generate())
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

        inngest_fixture.wait_for_log(
            f'mentor_action_outcome_payload_rejected event_id={event_id}'
        )
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
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, ids.generate())

        event_id = _publish_outcome(inngest_fixture, ids, proposal, **changes)

        inngest_fixture.wait_for_log(
            f'mentor_action_outcome_payload_rejected event_id={event_id}'
        )
        with inngest_fixture.inspection_session() as session:
            assert (
                _state(session, proposal.id).status
                == MentorActionProposalStatus.PENDING.value
            )
