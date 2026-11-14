"""Builders shared by the Planner use-case tests."""

from datetime import UTC, datetime

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.enums import PlanningQuestionKind
from shifu.intelligence.core.domain.structures import (
    PlanningOperationResult,
    PlanningOption,
    PlanningProposal,
    PlanningProposalSkill,
    PlanningQuestion,
    PlanningQuestionBatch,
)

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
ACCOUNT_ID = '01JACCOUNT000000000000TEST'
OTHER_ACCOUNT_ID = '01JACCOUNT00000000000OTHER'
PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
NEXT_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAX'
ACCESS_REVISION = 'revision-1'


def batch(batch_id: str = 'batch-1') -> PlanningQuestionBatch:
    return PlanningQuestionBatch(
        id=batch_id,
        questions=(
            PlanningQuestion(
                id='q1',
                text='O que você quer construir?',
                kind=PlanningQuestionKind.SINGLE,
                options=(
                    PlanningOption(id='o1', text='Sites'),
                    PlanningOption(id='o2', text='APIs'),
                    PlanningOption.unknown(),
                ),
            ),
        ),
    )


def proposal() -> PlanningProposal:
    return PlanningProposal(
        title='Aprender web',
        description='Do HTML ao React.',
        skills=(
            PlanningProposalSkill(
                skill_id='skill-html', name='HTML e CSS', justification='Base.'
            ),
        ),
    )


def started_session(account_id: str = ACCOUNT_ID) -> PlanningSession:
    return PlanningSession.start(
        PLANNING_ID,
        account_id,
        ACCESS_REVISION,
        'Quero aprender web',
        OPERATION_ID,
        NOW,
    )


def interviewing_session(account_id: str = ACCOUNT_ID) -> PlanningSession:
    session = started_session(account_id)
    assert session.complete(
        OPERATION_ID, 1, PlanningOperationResult.for_batch(batch()), NOW
    )
    return session


def failed_session(account_id: str = ACCOUNT_ID) -> PlanningSession:
    session = started_session(account_id)
    assert session.complete(OPERATION_ID, 1, PlanningOperationResult.failed(), NOW)
    return session
