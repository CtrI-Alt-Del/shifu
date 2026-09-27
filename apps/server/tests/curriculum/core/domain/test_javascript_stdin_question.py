from dataclasses import FrozenInstanceError

import pytest

from shifu.curriculum.core.domain.errors import (
    InvalidActivityError,
    InvalidEvaluationRuleError,
)
from shifu.curriculum.core.domain.structures import (
    CodeConceptCriterion,
    CodeInconclusiveComment,
    CodeInconclusiveObservation,
    CodeLevelObservation,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    JavascriptDependency,
    JavascriptInitialFile,
    JavascriptPermittedCommand,
    JavascriptStdinQuestion,
)


def _concept_criterion() -> CodeConceptCriterion:
    return CodeConceptCriterion(
        concept_id='concept-1',
        description='Uses the input to produce the result',
        level_observations=tuple(
            CodeLevelObservation(
                id=f'observation-{level}',
                level=level,
                evidence=f'Evidence at {level}',
                interpretation_limit='Only source evidence',
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_observation=CodeInconclusiveObservation(
            id='observation-unknown', text='Insufficient evidence'
        ),
    )


def _question(
    *,
    initial_files: tuple[JavascriptInitialFile, ...] | None = None,
    entrypoint: str = 'src/main.js',
) -> JavascriptStdinQuestion:
    return JavascriptStdinQuestion(
        key='stdin-1',
        prompt='Read a number',
        initial_files=initial_files
        if initial_files is not None
        else (JavascriptInitialFile(path='src/main.js', content='', editable=True),),
        entrypoint=entrypoint,
        fixed_dependencies=(JavascriptDependency(name='left-pad', version='1.3.0'),),
        permitted_commands=(
            JavascriptPermittedCommand(
                id='run', executable='node', arguments=('src/main.js',)
            ),
        ),
        concept_criteria=(_concept_criterion(),),
    )


def test_should_keep_valid_stdin_project_immutable() -> None:
    question = _question()

    assert question.entrypoint == 'src/main.js'
    with pytest.raises(FrozenInstanceError):
        question.prompt = 'changed'  # type: ignore[misc]


@pytest.mark.parametrize(
    'path',
    ('/etc/passwd', '../secret.js', 'src/../secret.js', 'package.json', 'src\\main.js'),
)
def test_should_reject_unsafe_or_configuration_paths(path: str) -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            initial_files=(JavascriptInitialFile(path=path, content='', editable=True),)
        )


def test_should_reject_missing_entrypoint_and_duplicate_paths() -> None:
    initial = JavascriptInitialFile(path='src/main.js', content='', editable=True)
    with pytest.raises(InvalidActivityError):
        _question(entrypoint='src/missing.js')
    with pytest.raises(InvalidActivityError):
        _question(initial_files=(initial, initial))


def test_should_require_complete_fixed_rubric_catalog() -> None:
    criterion = CodeRubricCriterion(
        key='correctness',
        name='Correctness',
        description='Checks input handling',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(id=f'comment-{level}', level=level, text=f'Level {level}')
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id='comment-unknown', text='Inconclusive'
        ),
    )
    part = CodeRubricEvaluationPart(
        question_key='stdin-1', weight_percentage=100, criteria=(criterion,)
    )
    assert part.criteria[0].required
    with pytest.raises(InvalidEvaluationRuleError):
        CodeRubricCriterion(
            key='incomplete',
            name='Incomplete',
            description='Missing level',
            weight_percentage=100,
            required=True,
            fixed_comments=criterion.fixed_comments[:-1],
            inconclusive_comment=criterion.inconclusive_comment,
        )
