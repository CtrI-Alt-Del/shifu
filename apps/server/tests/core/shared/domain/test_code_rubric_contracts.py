from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CodeCriterionDecision,
    CodeRubricAssessmentInput,
    CodeRubricDecisions,
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
)


def _choice(key: str) -> CurriculumChoiceQuestionSnapshot:
    return CurriculumChoiceQuestionSnapshot(
        key=key,
        kind='single_choice',
        prompt='Choose one',
        options=(
            CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
            CurriculumChoiceOptionSnapshot(key='b', text='B', is_correct=False),
        ),
        correct_explanation='Correct',
        incorrect_explanation='Try again',
    )


def test_should_preserve_order_and_version_in_immutable_snapshot() -> None:
    code = CurriculumJavascriptStdinQuestionSnapshot(
        key='third',
        prompt='Read input',
        initial_files=(
            CurriculumJavascriptInitialFileSnapshot(
                path='src/main.js', content='', editable=True
            ),
        ),
        entrypoint='src/main.js',
        fixed_dependencies=(),
        permitted_commands=(),
        concept_criteria=(),
    )
    criterion = CurriculumCodeRubricCriterionSnapshot(
        key='correctness',
        name='Correctness',
        description='Checks output',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CurriculumCodeRubricCommentSnapshot(
                id=f'comment-{level}', level=level, text=f'Level {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
            id='unknown', text='Unknown'
        ),
    )
    questions = (_choice('first'), _choice('second'), code)
    snapshot = CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Mixed practice',
        questions=questions,
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='first', weight_percentage=Decimal(40)
            ),
            CurriculumChoicePartSnapshot(
                question_key='second', weight_percentage=Decimal(30)
            ),
            CurriculumCodeRubricPartSnapshot(
                question_key='third',
                weight_percentage=Decimal(30),
                criteria=(criterion,),
            ),
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='digest',
    )

    assert tuple(question.key for question in snapshot.questions) == (
        'first',
        'second',
        'third',
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.revision = 'changed'  # type: ignore[misc]


def test_should_reject_invalid_mixed_snapshot_weights_and_missing_entrypoint() -> None:
    with pytest.raises(ValidationError):
        CurriculumJavascriptStdinQuestionSnapshot(
            key='stdin',
            prompt='Read input',
            initial_files=(
                CurriculumJavascriptInitialFileSnapshot(
                    path='src/main.js', content='', editable=True
                ),
            ),
            entrypoint='src/missing.js',
            fixed_dependencies=(),
            permitted_commands=(),
            concept_criteria=(),
        )
    with pytest.raises(ValidationError):
        CurriculumLearningActivitySnapshot(
            id='activity-1',
            competency_id='competency-1',
            difficulty='easy',
            title='Bad',
            questions=(_choice('first'), _choice('second'), _choice('third')),
            parts=(
                CurriculumChoicePartSnapshot(
                    question_key='first', weight_percentage=Decimal(100)
                ),
            ),
            required_concept_ids=(),
            activity_type='learning',
            schema_version=1,
            revision='digest',
        )


def test_should_keep_assessment_input_and_decisions_provider_neutral() -> None:
    with pytest.raises(ValidationError):
        CodeRubricAssessmentInput(
            question_kind='javascript_stdin',
            prompt='Read input',
            project_files=(('src/main.js', 'console.log(1)'),),
            submitted_paths=('src/main.js',),
            rubric_criteria=(),
            concept_criteria=(),
        )
    decisions = CodeRubricDecisions(
        criterion_levels=(CodeCriterionDecision(key='correctness', level=100),),
        concept_levels=(),
    )
    assert decisions.criterion_levels[0].level == 100
