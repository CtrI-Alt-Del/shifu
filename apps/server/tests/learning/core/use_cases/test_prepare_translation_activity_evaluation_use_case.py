from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, create_autospec
from decimal import Decimal

import pytest
from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    SingleChoiceAnswer,
    TranslationAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.prepare_translation_activity_evaluation_use_case import (
    PrepareTranslationActivityEvaluationUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumTranslationInconclusiveCommentSnapshot,
    CurriculumTranslationQuestionSnapshot,
    CurriculumTranslationRubricCommentSnapshot,
    CurriculumTranslationRubricCriterionSnapshot,
    CurriculumTranslationRubricPartSnapshot,
)

_ATTEMPT_ID = '01J000000000000000000000001'
_RUN_ID = '01J000000000000000000000002'


def _rubric_criterion(
    key: str, weight: int
) -> CurriculumTranslationRubricCriterionSnapshot:
    return CurriculumTranslationRubricCriterionSnapshot(
        key=key,
        name=key.replace('_', ' ').title(),
        description=f'Evaluate {key}',
        weight_percentage=weight,
        required=True,
        fixed_comments=tuple(
            CurriculumTranslationRubricCommentSnapshot(
                id=f'{key}-level-{level}', level=level, text=f'Feedback at {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumTranslationInconclusiveCommentSnapshot(
            id=f'{key}-unknown', text='Evidence is inconclusive'
        ),
    )


def _translation_question(question_key: str) -> CurriculumTranslationQuestionSnapshot:
    return CurriculumTranslationQuestionSnapshot(
        key=question_key,
        prompt=f'Translate for {question_key}',
        source_language='pt-BR',
        target_language='en-US',
        source_text='Bom dia',
        reference_translations=('Good morning',),
        concept_criteria=(),
    )


def _choice_question(question_key: str) -> CurriculumChoiceQuestionSnapshot:
    return CurriculumChoiceQuestionSnapshot(
        key=question_key,
        kind='single_choice',
        prompt=f'Choose for {question_key}',
        options=(
            CurriculumChoiceOptionSnapshot(
                key='correct', text='Correct', is_correct=True
            ),
            CurriculumChoiceOptionSnapshot(
                key='incorrect', text='Incorrect', is_correct=False
            ),
        ),
        correct_explanation='Correct answer.',
        incorrect_explanation='Try again.',
    )


def _mixed_snapshot() -> CurriculumLearningActivitySnapshot:
    questions = (
        _translation_question('q1'),
        _choice_question('q2'),
        _translation_question('q3'),
    )
    return CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Mixed translation activity',
        questions=questions,
        parts=(
            CurriculumTranslationRubricPartSnapshot(
                question_key='q1',
                weight_percentage=Decimal(30),
                criteria=(
                    _rubric_criterion('semantic_preservation', 70),
                    _rubric_criterion('grammatical_adequacy', 30),
                ),
            ),
            CurriculumChoicePartSnapshot(
                question_key='q2', weight_percentage=Decimal(30)
            ),
            CurriculumTranslationRubricPartSnapshot(
                question_key='q3',
                weight_percentage=Decimal(40),
                criteria=(
                    _rubric_criterion('semantic_preservation', 70),
                    _rubric_criterion('grammatical_adequacy', 30),
                ),
            ),
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='revision-1',
    )


def _choice_only_snapshot() -> CurriculumLearningActivitySnapshot:
    questions = tuple(_choice_question(f'q{number}') for number in (1, 2, 3))
    return CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Choice activity',
        questions=questions,
        parts=tuple(
            CurriculumChoicePartSnapshot(
                question_key=f'q{number}', weight_percentage=Decimal(weight)
            )
            for number, weight in ((1, 30), (2, 30), (3, 40))
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='revision-1',
    )


def _answers() -> tuple[TranslationAnswer | SingleChoiceAnswer, ...]:
    return (
        TranslationAnswer(question_key='q1', text='Good morning'),
        SingleChoiceAnswer(question_key='q2', selected_option_key='correct'),
        TranslationAnswer(question_key='q3', text='Good morning'),
    )


def _attempt(
    snapshot: CurriculumLearningActivitySnapshot | None = None,
    answers: tuple[TranslationAnswer | SingleChoiceAnswer, ...] | None = None,
    *,
    include_snapshot: bool = True,
) -> ActivityAttempt:
    saved_snapshot = snapshot if snapshot is not None else _mixed_snapshot()
    return ActivityAttempt(
        id=_ATTEMPT_ID,
        skill_experience_id='experience-1',
        competency_id=saved_snapshot.competency_id,
        activity_id=saved_snapshot.id,
        kind=ActivityAttemptKind.LEARNING,
        answers=answers if answers is not None else _answers(),
        submitted_at=datetime(2026, 1, 1, tzinfo=UTC),
        grading_snapshot=saved_snapshot if include_snapshot else None,
    )


def _evaluation(
    *,
    run_id: str = _RUN_ID,
    status: ActivityEvaluationStatus = ActivityEvaluationStatus.PENDING,
) -> SimpleNamespace:
    return SimpleNamespace(run_id=run_id, status=status)


def _subject(
    attempt: ActivityAttempt | None,
    evaluation: SimpleNamespace | None,
) -> tuple[PrepareTranslationActivityEvaluationUseCase, LearningDatabaseRepositories]:
    database = create_autospec(LearningDatabase, instance=True)
    repositories = create_autospec(LearningDatabaseRepositories, instance=True)
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.activity_attempts.find_by_id.return_value = attempt
    repositories.activity_evaluations.find_by_attempt_id.return_value = evaluation
    return PrepareTranslationActivityEvaluationUseCase(database), repositories


def test_should_prepare_only_translation_questions_for_the_current_pending_run() -> (
    None
):
    attempt = _attempt()
    subject, repositories = _subject(attempt, _evaluation())

    result = subject.execute(_ATTEMPT_ID, _RUN_ID)

    assert result is not None
    assert result.attempt_id == _ATTEMPT_ID
    assert result.run_id == _RUN_ID
    assert tuple(item.question_key for item in result.questions) == ('q1', 'q3')
    assert result.questions[0].assessment_input.submitted_text == 'Good morning'
    assert result.questions[0].assessment_input.source_text == 'Bom dia'
    assert result.questions[0].assessment_input.rubric_criteria[0].key == (
        'semantic_preservation'
    )
    cast('Mock', repositories.activity_attempts.find_by_id).assert_called_once_with(
        _ATTEMPT_ID
    )
    cast('Mock', repositories.events.add).assert_not_called()


@pytest.mark.parametrize(
    ('attempt', 'evaluation'),
    (
        (None, _evaluation()),
        (_attempt(), None),
        (_attempt(), _evaluation(run_id='older-run')),
        (_attempt(), _evaluation(status=ActivityEvaluationStatus.FAILED)),
        (_attempt(include_snapshot=False), _evaluation()),
    ),
    ids=(
        'missing-attempt',
        'missing-evaluation',
        'wrong-run-id',
        'stale-non-pending-evaluation',
        'attempt-without-a-mixed-snapshot',
    ),
)
def test_should_return_none_for_missing_wrong_or_stale_attempt_state(
    attempt: ActivityAttempt | None,
    evaluation: SimpleNamespace | None,
) -> None:
    subject, _repositories = _subject(attempt, evaluation)

    assert subject.execute(_ATTEMPT_ID, _RUN_ID) is None


def test_should_reject_incomplete_answer_sets() -> None:
    attempt = _attempt(answers=_answers()[:-1])
    subject, _repositories = _subject(attempt, _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


def test_should_reject_a_non_translation_answer_for_a_translation_question() -> None:
    answers = list(_answers())
    answers[0] = SingleChoiceAnswer(question_key='q1', selected_option_key='correct')
    subject, _repositories = _subject(_attempt(answers=tuple(answers)), _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


def test_should_reject_a_malformed_part_for_a_translation_question() -> None:
    snapshot = _mixed_snapshot()
    object.__setattr__(
        snapshot,
        'parts',
        (
            CurriculumChoicePartSnapshot(
                question_key='q1', weight_percentage=Decimal(30)
            ),
            snapshot.parts[1],
            snapshot.parts[2],
        ),
    )
    subject, _repositories = _subject(_attempt(snapshot=snapshot), _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


def test_should_reject_activities_without_translation_questions() -> None:
    snapshot = _choice_only_snapshot()
    answers = tuple(
        SingleChoiceAnswer(question_key=f'q{number}', selected_option_key='correct')
        for number in (1, 2, 3)
    )
    subject, _repositories = _subject(_attempt(snapshot, answers), _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)
