from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, create_autospec

import pytest
from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
)
from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    CodeSubmittedFile,
    SingleChoiceAnswer,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.prepare_code_activity_evaluation_use_case import (
    PrepareCodeActivityEvaluationUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumJavascriptInitialFileSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumReactQuestionSnapshot,
    CurriculumReactFastifyQuestionSnapshot,
)
from tests.learning.core.use_cases.test_preview_activity_question_feedback_use_case import (
    mixed_snapshot,
    code_answer_at_size,
)

_ATTEMPT_ID = '01J000000000000000000000001'
_RUN_ID = '01J000000000000000000000002'


def _rubric_criterion(question_key: str) -> CurriculumCodeRubricCriterionSnapshot:
    return CurriculumCodeRubricCriterionSnapshot(
        key=f'{question_key}-correctness',
        name='Correctness',
        description=f'Output for {question_key}',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CurriculumCodeRubricCommentSnapshot(
                id=f'{question_key}-level-{level}',
                level=level,
                text=f'Feedback at {level}',
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
            id=f'{question_key}-unknown',
            text='Evidence is inconclusive',
        ),
    )


def _code_question(question_key: str) -> CurriculumJavascriptStdinQuestionSnapshot:
    entrypoint = f'src/{question_key}.js'
    return CurriculumJavascriptStdinQuestionSnapshot(
        key=question_key,
        prompt=f'Implement {question_key}',
        initial_files=(
            CurriculumJavascriptInitialFileSnapshot(
                path=entrypoint,
                content=f'console.log("starter-{question_key}")',
                editable=True,
            ),
            CurriculumJavascriptInitialFileSnapshot(
                path='src/support.js',
                content='export const fixed = true',
                editable=False,
            ),
        ),
        entrypoint=entrypoint,
        fixed_dependencies=(),
        permitted_commands=(),
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
        _code_question('q1'),
        _choice_question('q2'),
        _code_question('q3'),
    )
    return CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Mixed code activity',
        questions=questions,
        parts=(
            CurriculumCodeRubricPartSnapshot(
                question_key='q1',
                weight_percentage=Decimal(30),
                criteria=(_rubric_criterion('q1'),),
            ),
            CurriculumChoicePartSnapshot(
                question_key='q2', weight_percentage=Decimal(30)
            ),
            CurriculumCodeRubricPartSnapshot(
                question_key='q3',
                weight_percentage=Decimal(40),
                criteria=(_rubric_criterion('q3'),),
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
                question_key=f'q{number}',
                weight_percentage=Decimal(weight),
            )
            for number, weight in ((1, 30), (2, 30), (3, 40))
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='revision-1',
    )


def _answers() -> tuple[CodeAnswer | SingleChoiceAnswer, ...]:
    return (
        CodeAnswer(
            question_key='q1',
            files=(
                CodeSubmittedFile(
                    path='src/q1.js', content='console.log("submitted-q1")'
                ),
            ),
        ),
        SingleChoiceAnswer(question_key='q2', selected_option_key='correct'),
        CodeAnswer(
            question_key='q3',
            files=(
                CodeSubmittedFile(
                    path='src/q3.js', content='console.log("submitted-q3")'
                ),
            ),
        ),
    )


def _attempt(
    snapshot: CurriculumLearningActivitySnapshot | None = None,
    answers: tuple[CodeAnswer | SingleChoiceAnswer, ...] | None = None,
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
    *,
    max_input_bytes: int = 100_000,
) -> tuple[PrepareCodeActivityEvaluationUseCase, LearningDatabaseRepositories]:
    database = create_autospec(LearningDatabase, instance=True)
    repositories = create_autospec(LearningDatabaseRepositories, instance=True)
    database.transaction.return_value.__enter__.return_value = repositories
    repositories.activity_attempts.find_by_id.return_value = attempt
    repositories.activity_evaluations.find_by_attempt_id.return_value = evaluation
    return (
        PrepareCodeActivityEvaluationUseCase(database, max_input_bytes),
        repositories,
    )


def test_should_prepare_only_code_questions_for_the_current_pending_run() -> None:
    attempt = _attempt()
    subject, repositories = _subject(attempt, _evaluation())

    result = subject.execute(_ATTEMPT_ID, _RUN_ID)

    assert result is not None
    assert result.attempt_id == _ATTEMPT_ID
    assert result.run_id == _RUN_ID
    assert tuple(item.question_key for item in result.questions) == ('q1', 'q3')
    assert tuple(item.assessment_input.prompt for item in result.questions) == (
        'Implement q1',
        'Implement q3',
    )
    assert tuple(
        item.assessment_input.rubric_criteria[0].key for item in result.questions
    ) == ('q1-correctness', 'q3-correctness')
    assert result.questions[0].assessment_input.project_files == (
        ('src/q1.js', 'console.log("submitted-q1")'),
        ('src/support.js', 'export const fixed = true'),
    )
    cast('Mock', repositories.activity_attempts.find_by_id).assert_called_once_with(
        _ATTEMPT_ID
    )
    cast(
        'Mock', repositories.activity_evaluations.find_by_attempt_id
    ).assert_called_once_with(_ATTEMPT_ID)
    cast('Mock', repositories.events.add).assert_not_called()


def test_should_prepare_react_question_with_saved_project_files() -> None:
    snapshot = mixed_snapshot(react=True)
    answers = (
        SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
        SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
        CodeAnswer(
            question_key='q3',
            files=(CodeSubmittedFile(path='src/main.tsx', content='submitted'),),
        ),
    )
    subject, _repositories = _subject(
        _attempt(snapshot=snapshot, answers=answers), _evaluation()
    )

    result = subject.execute(_ATTEMPT_ID, _RUN_ID)

    assert result is not None
    assert tuple(item.question_key for item in result.questions) == ('q3',)
    assert result.questions[0].assessment_input.project_files == (
        ('src/fixed.css', 'fixed'),
        ('src/main.tsx', 'submitted'),
    )


@pytest.mark.parametrize(
    ('attempt', 'evaluation'),
    (
        (None, _evaluation()),
        (_attempt(), None),
        (_attempt(), _evaluation(run_id='older-run')),
        (
            _attempt(),
            _evaluation(status=ActivityEvaluationStatus.FAILED),
        ),
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


def test_should_reject_a_non_code_answer_for_a_code_question() -> None:
    answers = list(_answers())
    answers[0] = SingleChoiceAnswer(question_key='q1', selected_option_key='correct')
    subject, _repositories = _subject(_attempt(answers=tuple(answers)), _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


def test_should_reject_code_answers_with_missing_editable_files() -> None:
    answers = list(_answers())
    answers[0] = CodeAnswer(question_key='q1', files=())
    subject, _repositories = _subject(_attempt(answers=tuple(answers)), _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


def test_should_reject_a_malformed_part_for_a_code_question() -> None:
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


def test_should_reject_activities_without_code_questions() -> None:
    snapshot = _choice_only_snapshot()
    answers = tuple(
        SingleChoiceAnswer(question_key=f'q{number}', selected_option_key='correct')
        for number in (1, 2, 3)
    )
    subject, _repositories = _subject(_attempt(snapshot, answers), _evaluation())

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


def test_should_reject_code_project_over_the_configured_input_limit() -> None:
    subject, _repositories = _subject(_attempt(), _evaluation(), max_input_bytes=1)

    with pytest.raises(EvaluationUnavailableError):
        subject.execute(_ATTEMPT_ID, _RUN_ID)


class TestPrepareCodeActivityEvaluationConfiguredLimit:
    @pytest.mark.parametrize(
        'react', (False, True, 'integrated'), ids=('javascript', 'react', 'integrated')
    )
    @pytest.mark.parametrize(
        'limit', (128, 256 * 1024, 512 * 1024), ids=('lower', 'default', 'higher')
    )
    @pytest.mark.parametrize('extra_byte', (0, 1), ids=('exact', 'above'))
    def test_should_apply_configured_utf8_project_limit_to_saved_projects(
        self, react: bool | str, limit: int, extra_byte: int
    ) -> None:
        snapshot = mixed_snapshot(react=react)
        question = snapshot.questions[-1]
        assert isinstance(
            question,
            (
                CurriculumJavascriptStdinQuestionSnapshot,
                CurriculumReactQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
                CurriculumReactFastifyQuestionSnapshot,
            ),
        )
        answer = code_answer_at_size(question, limit + extra_byte)
        attempt = _attempt(
            snapshot,
            (
                SingleChoiceAnswer(question_key='q1', selected_option_key='a'),
                SingleChoiceAnswer(question_key='q2', selected_option_key='a'),
                answer,
            ),
        )
        subject, repositories = _subject(attempt, _evaluation(), max_input_bytes=limit)

        if extra_byte:
            with pytest.raises(EvaluationUnavailableError):
                subject.execute(_ATTEMPT_ID, _RUN_ID)
        else:
            result = subject.execute(_ATTEMPT_ID, _RUN_ID)
            assert result is not None
            assert len(result.questions) == 1
            assert result.questions[0].assessment_input.question_kind == question.kind
            assert result.questions[0].assessment_input.project_files[-1] == (
                question.frontend_entrypoint
                if isinstance(question, CurriculumReactFastifyQuestionSnapshot)
                else question.entrypoint,
                answer.files[0].content,
            )
        cast('Mock', repositories.events.add).assert_not_called()
