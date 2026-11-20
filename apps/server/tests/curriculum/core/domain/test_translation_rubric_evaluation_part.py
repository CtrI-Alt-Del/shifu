import pytest
from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.curriculum.core.domain.structures import (
    TranslationInconclusiveComment,
    TranslationRubricComment,
    TranslationRubricCriterion,
    TranslationRubricEvaluationPart,
)


def _criterion(
    key: str, weight_percentage: int, *, required: bool = True
) -> TranslationRubricCriterion:
    return TranslationRubricCriterion(
        key=key,
        name=key.replace('_', ' ').title(),
        description=f'Assesses {key}',
        weight_percentage=weight_percentage,
        required=required,
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


def _valid_criteria() -> tuple[TranslationRubricCriterion, ...]:
    return (
        _criterion('semantic_preservation', 70),
        _criterion('grammatical_adequacy', 30),
    )


def test_should_build_a_valid_translation_rubric_evaluation_part() -> None:
    part = TranslationRubricEvaluationPart(
        question_key='translation-1',
        weight_percentage=100,
        criteria=_valid_criteria(),
    )

    assert part.question_key == 'translation-1'
    assert {criterion.key for criterion in part.criteria} == {
        'semantic_preservation',
        'grammatical_adequacy',
    }


def test_should_reject_empty_question_key() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricEvaluationPart(
            question_key='   ',
            weight_percentage=100,
            criteria=_valid_criteria(),
        )


def test_should_reject_other_than_exactly_two_criteria() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricEvaluationPart(
            question_key='translation-1',
            weight_percentage=100,
            criteria=(_criterion('semantic_preservation', 70),),
        )
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricEvaluationPart(
            question_key='translation-1',
            weight_percentage=100,
            criteria=(
                *_valid_criteria(),
                _criterion('extra_criterion', 0),
            ),
        )


def test_should_reject_unexpected_criterion_keys() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricEvaluationPart(
            question_key='translation-1',
            weight_percentage=100,
            criteria=(
                _criterion('semantic_preservation', 70),
                _criterion('fluency', 30),
            ),
        )


def test_should_reject_non_fixed_weight_split() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricEvaluationPart(
            question_key='translation-1',
            weight_percentage=100,
            criteria=(
                _criterion('semantic_preservation', 60),
                _criterion('grammatical_adequacy', 40),
            ),
        )


def test_should_reject_criterion_not_marked_required() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricEvaluationPart(
            question_key='translation-1',
            weight_percentage=100,
            criteria=(
                _criterion('semantic_preservation', 70, required=False),
                _criterion('grammatical_adequacy', 30),
            ),
        )
