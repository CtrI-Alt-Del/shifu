from dataclasses import FrozenInstanceError, replace

import pytest
from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures import (
    CodeConceptCriterion,
    CodeInconclusiveComment,
    CodeInconclusiveObservation,
    CodeLevelObservation,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    CorrectnessEvaluationPart,
    EvaluationRule,
    JavascriptDependency,
    JavascriptInitialFile,
    JavascriptStdinQuestion,
    ReactAdditionalFilePolicy,
    ReactDependency,
    ReactInitialFile,
    ReactPermittedCommand,
    ReactQuestion,
    TranslationInconclusiveComment,
    TranslationQuestion,
    TranslationRubricComment,
    TranslationRubricCriterion,
    TranslationRubricEvaluationPart,
)


def _concept_criterion(concept_id: str = 'concept-1') -> CodeConceptCriterion:
    return CodeConceptCriterion(
        concept_id=concept_id,
        description='Preserves meaning across languages',
        level_observations=tuple(
            CodeLevelObservation(
                id=f'{concept_id}-{level}',
                level=level,
                evidence=f'Evidence at {level}',
                interpretation_limit=f'Limit at {level}',
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_observation=CodeInconclusiveObservation(
            id=f'{concept_id}-unknown', text='Insufficient evidence'
        ),
    )


def _question(
    *,
    key: str = 'translation-1',
    prompt: str = 'Translate the passage',
    source_language: str = 'en',
    target_language: str = 'pt-BR',
    source_text: str = 'The cat sat on the mat.',
    reference_translations: tuple[str, ...] = ('O gato sentou no tapete.',),
    concept_criteria: tuple[CodeConceptCriterion, ...] = (),
) -> TranslationQuestion:
    return TranslationQuestion(
        key=key,
        prompt=prompt,
        source_language=source_language,
        target_language=target_language,
        source_text=source_text,
        reference_translations=reference_translations,
        concept_criteria=concept_criteria,
    )


def _rubric_criterion(key: str, weight: int) -> TranslationRubricCriterion:
    return TranslationRubricCriterion(
        key=key,
        name=key.replace('_', ' ').title(),
        description=f'Assesses {key}',
        weight_percentage=weight,
        required=True,
        fixed_comments=tuple(
            TranslationRubricComment(
                id=f'{key}-{level}', level=level, text=f'Level {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=TranslationInconclusiveComment(
            id=f'{key}-unknown', text='Insufficient evidence'
        ),
    )


def _rubric_part(
    question_key: str, *, weight_percentage: int = 100
) -> TranslationRubricEvaluationPart:
    return TranslationRubricEvaluationPart(
        question_key=question_key,
        weight_percentage=weight_percentage,
        criteria=(
            _rubric_criterion('semantic_preservation', 70),
            _rubric_criterion('grammatical_adequacy', 30),
        ),
    )


def _code_rubric_part(
    question_key: str, *, weight_percentage: int = 100
) -> CodeRubricEvaluationPart:
    criterion = CodeRubricCriterion(
        key='quality',
        name='Quality',
        description='Uses the requested structure',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(id=f'quality-{level}', level=level, text=f'Level {level}')
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id='quality-unknown', text='Insufficient evidence'
        ),
    )
    return CodeRubricEvaluationPart(
        question_key=question_key,
        weight_percentage=weight_percentage,
        criteria=(criterion,),
    )


def _javascript_stdin_question() -> JavascriptStdinQuestion:
    return JavascriptStdinQuestion(
        key='js-1',
        prompt='Print to stdin',
        initial_files=(
            JavascriptInitialFile(path='index.js', content='', editable=True),
        ),
        entrypoint='index.js',
        fixed_dependencies=(JavascriptDependency(name='left-pad', version='1.0.0'),),
        permitted_commands=(),
        concept_criteria=(),
    )


def _react_question() -> ReactQuestion:
    return ReactQuestion(
        key='react-1',
        prompt='Build a component',
        initial_files=(
            ReactInitialFile(path='src/App.tsx', content='', editable=True),
        ),
        entrypoint='src/App.tsx',
        fixed_dependencies=(ReactDependency(name='react', version='19.0.0'),),
        permitted_commands=(
            ReactPermittedCommand(id='dev', executable='npm', arguments=('run', 'dev')),
        ),
        concept_criteria=(),
        additional_file_policy=ReactAdditionalFilePolicy(
            allowed_directories=('src/components',),
            allowed_extensions=('.tsx',),
            max_files=3,
        ),
    )


def _activity(
    question: TranslationQuestion,
    part: TranslationRubricEvaluationPart | None,
    activity_type: ActivityType = ActivityType.LEARNING,
) -> Activity:
    return Activity(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='Translation activity',
        objective='Translate the passage',
        questions=(question,),
        evaluation_rule=EvaluationRule(parts=(part,) if part is not None else ()),
    )


def test_should_build_a_valid_translation_question() -> None:
    question = _question(concept_criteria=(_concept_criterion(),))

    assert question.kind == 'translation'
    assert question.reference_translations == ('O gato sentou no tapete.',)
    with pytest.raises(FrozenInstanceError):
        question.prompt = 'changed'  # type: ignore[misc]


def test_should_reject_empty_key() -> None:
    with pytest.raises(InvalidActivityError):
        _question(key='   ')


def test_should_reject_empty_prompt() -> None:
    with pytest.raises(InvalidActivityError):
        _question(prompt='   ')


def test_should_reject_empty_source_language() -> None:
    with pytest.raises(InvalidActivityError):
        _question(source_language='   ')


def test_should_reject_empty_target_language() -> None:
    with pytest.raises(InvalidActivityError):
        _question(target_language='   ')


def test_should_reject_empty_source_text() -> None:
    with pytest.raises(InvalidActivityError):
        _question(source_text='   ')


def test_should_reject_duplicate_reference_translations() -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            reference_translations=(
                'O gato sentou no tapete.',
                'O gato sentou no tapete.',
            )
        )


def test_should_reject_empty_reference_translation_entries() -> None:
    with pytest.raises(InvalidActivityError):
        _question(reference_translations=('O gato sentou no tapete.', '   '))


def test_should_reject_missing_reference_translations() -> None:
    with pytest.raises(InvalidActivityError):
        _question(reference_translations=())


def test_should_reject_duplicate_concept_ids() -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            concept_criteria=(
                _concept_criterion('concept-1'),
                _concept_criterion('concept-1'),
            )
        )


def test_should_accept_activity_with_matching_translation_rubric() -> None:
    question = _question()
    activity = _activity(question, _rubric_part(question.key))

    assert activity.questions == (question,)


def test_should_reject_translation_question_missing_its_rubric_part() -> None:
    question = _question()

    with pytest.raises(InvalidActivityError):
        Activity(
            id='activity-1',
            competency_id='competency-1',
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Translation activity',
            objective='Translate the passage',
            questions=(question,),
            evaluation_rule=EvaluationRule(
                parts=(
                    CorrectnessEvaluationPart(
                        question_key=question.key, weight_percentage=100
                    ),
                )
            ),
        )


def test_should_reject_translation_question_paired_with_a_code_rubric_part() -> None:
    question = _question()

    with pytest.raises(InvalidActivityError):
        Activity(
            id='activity-1',
            competency_id='competency-1',
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Translation activity',
            objective='Translate the passage',
            questions=(question,),
            evaluation_rule=EvaluationRule(parts=(_code_rubric_part(question.key),)),
        )


def test_should_reject_translation_question_in_a_diagnostic_activity() -> None:
    question = _question()

    with pytest.raises(InvalidActivityError):
        _activity(
            question,
            _rubric_part(question.key),
            activity_type=ActivityType.DIAGNOSTIC,
        )


def test_should_reject_translation_question_alongside_javascript_stdin_question() -> (
    None
):
    translation = _question()
    code_question = _javascript_stdin_question()

    with pytest.raises(InvalidActivityError):
        Activity(
            id='activity-1',
            competency_id='competency-1',
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Mixed activity',
            objective='Mix AI-graded kinds',
            questions=(translation, code_question),
            evaluation_rule=EvaluationRule(
                parts=(
                    _rubric_part(translation.key, weight_percentage=50),
                    _code_rubric_part(code_question.key, weight_percentage=50),
                )
            ),
        )


def test_should_reject_translation_question_alongside_react_question() -> None:
    translation = _question()
    react_question = _react_question()

    with pytest.raises(InvalidActivityError):
        Activity(
            id='activity-1',
            competency_id='competency-1',
            activity_type=ActivityType.LEARNING,
            difficulty=ActivityDifficulty.EASY,
            title='Mixed activity',
            objective='Mix AI-graded kinds',
            questions=(translation, react_question),
            evaluation_rule=EvaluationRule(
                parts=(
                    _rubric_part(translation.key, weight_percentage=50),
                    _code_rubric_part(react_question.key, weight_percentage=50),
                )
            ),
        )


def test_should_preserve_immutable_contract_on_replace() -> None:
    question = _question()
    replaced = replace(question, key='translation-2')

    assert replaced.key == 'translation-2'
    assert replaced.prompt == question.prompt
