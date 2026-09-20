from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from shifu.communication.core.domain.entities import Communication
from shifu.communication.core.domain.enums import (
    CommunicationChannel,
    CommunicationStatus,
    CommunicationType,
)
from shifu.communication.core.domain.errors import CommunicationTransitionError
from shifu.communication.core.domain.structures import MessageContent
from shifu.curriculum.core.domain.entities import Competency
from shifu.curriculum.core.domain.errors import (
    InvalidActivityError,
    InvalidCompetencyError,
    InvalidEvaluationRuleError,
)
from shifu.curriculum.core.domain.factories import create_competencies
from shifu.curriculum.core.domain.structures import (
    ActivitySequenceItem,
    ChoiceOption,
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    SingleChoiceQuestion,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.fakers.learning.entities import CompetencyProgressFaker
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.core.domain.errors import (
    AccountConfirmationNotAllowedError,
    InvalidDisplayNameError,
    InvalidPasswordError,
)
from shifu.identity.core.domain.structures import AuthCredentials
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import (
    EvaluationAlreadyCompletedError,
    InvalidAttemptError,
    SkillExperienceTransitionError,
)
from shifu.learning.core.domain.structures import SingleChoiceAnswer
from shifu.learning.core.domain.structures import SkillCompletionSummary

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_account_normalizes_email_and_pending_account_can_be_confirmed() -> None:
    account = AccountFaker.fake(
        status=AccountStatus.PENDING_CONFIRMATION,
        email='  Learner@Example.COM ',
        confirmed_at=None,
    )

    assert account.email == 'learner@example.com'
    account.confirm(NOW)
    assert account.status is AccountStatus.ACTIVE
    assert account.confirmed_at == NOW


def test_account_rejects_empty_display_name_and_invalid_password() -> None:
    with pytest.raises(InvalidDisplayNameError):
        AccountFaker.fake(display_name='   ')
    with pytest.raises(InvalidPasswordError):
        AuthCredentials.create(email='learner@example.com', password='x' * 5)


def test_account_rejects_confirming_an_active_account() -> None:
    account = AccountFaker.fake(status=AccountStatus.ACTIVE)

    with pytest.raises(AccountConfirmationNotAllowedError):
        account.confirm(NOW)


def test_competencies_require_unique_positions_per_skill() -> None:
    competencies = (
        Competency.create(
            id='c1',
            skill_id='s1',
            name='One',
            description='First',
            position=1,
        ),
        Competency.create(
            id='c2',
            skill_id='s1',
            name='Two',
            description='Second',
            position=1,
        ),
    )

    with pytest.raises(InvalidCompetencyError):
        create_competencies(competencies)


def test_curriculum_structures_protect_answer_and_weight_invariants() -> None:
    with pytest.raises(InvalidActivityError):
        SingleChoiceQuestion(
            key='question',
            prompt='Choose one',
            options=(
                ChoiceOption(key='a', text='A', is_correct=True),
                ChoiceOption(key='b', text='B', is_correct=True),
            ),
        )
    with pytest.raises(InvalidEvaluationRuleError):
        EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key='question', weight_percentage=99
                ),
            )
        )


def test_curriculum_sequence_rejects_duplicate_activity() -> None:
    with pytest.raises(InvalidActivityError):
        CurriculumSequence(
            competency_id='competency',
            items=(
                ActivitySequenceItem(position=1, activity_id='activity'),
                ActivitySequenceItem(position=2, activity_id='activity'),
            ),
        )


def test_progress_uses_bounded_scores_and_hard_result_for_mastery() -> None:
    progress = CompetencyProgressFaker.fake(
        initial_progress=Decimal('80'),
        current_progress=Decimal('80'),
    )

    progress.record_result(
        score=Decimal('100'),
        difficulty=ActivityDifficulty.HARD,
        updated_at=NOW,
    )

    assert progress.current_progress == Decimal('86.0')
    assert progress.status is CompetencyProgressStatus.MASTERED

    with pytest.raises(InvalidAttemptError):
        CompetencyProgressFaker.fake(current_progress=Decimal('101'))


def test_skill_experience_transitions_and_freezes_completed_progress() -> None:
    experience = SkillExperience(
        id='experience',
        goal_id='goal',
        skill_id='skill',
        inclusion_reason=None,
        status=SkillExperienceStatus.NOT_STARTED,
        created_at=NOW,
        updated_at=NOW,
    )
    experience.start_diagnosis(NOW)
    experience.start_learning(NOW + timedelta(minutes=1))
    experience.complete(
        summary=SkillCompletionSummary(
            competencies=(),
            initial_progress=Decimal('80'),
            final_progress=Decimal('90'),
            started_at=NOW,
            completed_at=NOW + timedelta(minutes=2),
        ),
        completed_at=NOW + timedelta(minutes=2),
    )

    assert experience.status is SkillExperienceStatus.COMPLETED
    assert not experience.accepts_progress_updates
    with pytest.raises(SkillExperienceTransitionError):
        experience.start_diagnosis(NOW)


def test_activity_evaluation_has_terminal_completed_state() -> None:
    evaluation = ActivityEvaluation(
        id='evaluation',
        attempt_id='attempt',
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=NOW,
    )
    evaluation.complete(Decimal('100'), NOW, ())

    with pytest.raises(EvaluationAlreadyCompletedError):
        evaluation.complete(Decimal('90'), NOW, ())


def test_submitted_attempt_is_immutable() -> None:
    attempt = ActivityAttempt.create(
        id='attempt',
        skill_experience_id='experience',
        competency_id='competency',
        activity_id='activity',
        kind=ActivityAttemptKind.LEARNING,
        answers=(SingleChoiceAnswer(question_key='q1', selected_option_key='a'),),
        submitted_at=NOW,
    )

    with pytest.raises(AttributeError):
        attempt.answers = ()  # type: ignore[misc]


def test_communication_status_machine_supports_retry_and_rejects_invalid_transition() -> (
    None
):
    communication = Communication.create(
        id='communication',
        account_id='account',
        type=CommunicationType.ACCOUNT_CONFIRMATION,
        channel=CommunicationChannel.EMAIL,
        recipient_email='User@Example.com',
        recipient_name='User',
        content=MessageContent(
            subject='Confirm', html='<p>Confirm</p>', text='Confirm'
        ),
        status=CommunicationStatus.PENDING,
        idempotency_key='idempotency-key',
        created_at=NOW,
        updated_at=NOW,
    )
    communication.start_processing(NOW)
    communication.mark_failed(NOW, 'temporary', retryable=True)
    communication.start_processing(NOW + timedelta(minutes=1))
    communication.mark_sent(NOW + timedelta(minutes=2), 'provider-message')

    assert communication.status is CommunicationStatus.SENT
    with pytest.raises(CommunicationTransitionError):
        communication.mark_sent(NOW, 'another-provider-message')
