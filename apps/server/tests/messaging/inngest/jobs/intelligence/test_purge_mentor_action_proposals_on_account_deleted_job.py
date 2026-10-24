from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from shifu.identity.core.domain.events import AccountDeletedEvent, AccountDeletedPayload
from shifu.intelligence.core.domain.enums import (
    MentorActionKind,
    MentorActionProposalOutcome,
    MentorActionProposalStatus,
)
from shifu.intelligence.database.sqlalchemy.models import (
    MentorActionProposalModel,
    MentorResponseEventModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.mentor_action_proposal_seed import seed_mentor_action_proposal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.fixtures.inngest_fixture import InngestFixture

_DELETED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _proposal_count(session: 'Session', account_id: str) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(MentorActionProposalModel)
            .where(MentorActionProposalModel.account_id == account_id)
        )
        or 0
    )


def _action_events(session: 'Session') -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(MentorResponseEventModel)
            .where(MentorResponseEventModel.kind == 'action')
        )
        or 0
    )


def _total_proposals(session: 'Session') -> int:
    return (
        session.scalar(select(func.count()).select_from(MentorActionProposalModel)) or 0
    )


def _publish_account_deleted(
    fixture: 'InngestFixture',
    ids: SystemIdentifierProvider,
    account_id: str,
    **extra: str,
) -> str:
    event = AccountDeletedEvent(
        payload=AccountDeletedPayload(
            account_id=account_id,
            deleted_at=_DELETED_AT.isoformat().replace('+00:00', 'Z'),
        )
    )
    event_id = ids.generate()
    fixture.publish(
        event.name,
        {
            'account_id': event.payload.account_id,
            'deleted_at': event.payload.deleted_at,
            **extra,
        },
        event_id=event_id,
    )
    return event_id


class TestPurgeMentorActionProposalsOnAccountDeletedJob:
    def test_should_purge_every_proposal_of_the_deleted_account_only(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        for status, outcome in (
            (MentorActionProposalStatus.PENDING, None),
            (MentorActionProposalStatus.DECLINED, None),
            (
                MentorActionProposalStatus.COMPLETED,
                MentorActionProposalOutcome.REMOVED,
            ),
        ):
            seed_mentor_action_proposal(
                inngest_fixture,
                ids,
                account_id,
                kind=MentorActionKind.REMOVE_SKILL,
                status=status,
                outcome=outcome,
                resolved_goal_id='goal' if outcome else None,
                resolved_skill_experience_id='experience' if outcome else None,
            )
        kept = seed_mentor_action_proposal(inngest_fixture, ids, other_account_id)
        with inngest_fixture.inspection_session() as session:
            assert _proposal_count(session, account_id) == 3
            assert _action_events(session) == 4

        _publish_account_deleted(inngest_fixture, ids, account_id)

        inngest_fixture.wait_for_database(
            lambda session: _proposal_count(session, account_id) == 0
        )
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorActionProposalModel, kept.id) is not None
            assert _proposal_count(session, other_account_id) == 1
            # The action events go with their proposals; the kept one stays.
            assert _action_events(session) == 1

    def test_should_succeed_without_effect_on_duplicate_delivery(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id, other_account_id = ids.generate(), ids.generate()
        seed_mentor_action_proposal(inngest_fixture, ids, account_id)
        seed_mentor_action_proposal(inngest_fixture, ids, other_account_id)

        _publish_account_deleted(inngest_fixture, ids, account_id)
        inngest_fixture.wait_for_database(
            lambda session: _proposal_count(session, account_id) == 0
        )
        _publish_account_deleted(inngest_fixture, ids, account_id)
        # Deliveries are handled in order, so the other account's purge proves the
        # duplicate for the first account completed without a failure.
        _publish_account_deleted(inngest_fixture, ids, other_account_id)
        inngest_fixture.wait_for_database(
            lambda session: _total_proposals(session) == 0
        )

    def test_should_reject_invalid_payloads_as_non_retriable_without_purging(
        self, inngest_fixture: 'InngestFixture'
    ) -> None:
        ids = SystemIdentifierProvider()
        account_id = ids.generate()
        proposal = seed_mentor_action_proposal(inngest_fixture, ids, account_id)

        event_id = _publish_account_deleted(
            inngest_fixture, ids, account_id, unexpected='must be rejected'
        )

        failure_log = inngest_fixture.wait_for_log(
            f'"event":"job.failed","event_id":"{event_id}",'
            '"exception_type":"NonRetriableError",'
            '"job":"intelligence.purge_mentor_action_proposals_on_account_deleted"'
        )
        assert (
            '"job":"intelligence.purge_mentor_action_proposals_on_account_deleted"'
            in failure_log
        )
        assert '"exception_type":"NonRetriableError"' in failure_log
        with inngest_fixture.inspection_session() as session:
            assert session.get(MentorActionProposalModel, proposal.id) is not None
            assert _proposal_count(session, account_id) == 1
