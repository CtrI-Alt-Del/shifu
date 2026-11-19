import pytest
from shifu.curriculum.core.domain.errors import InvalidEvaluationRuleError
from shifu.curriculum.core.domain.structures import (
    TranslationInconclusiveComment,
    TranslationRubricComment,
    TranslationRubricCriterion,
)


def _comments(
    key: str = 'semantic_preservation',
) -> tuple[TranslationRubricComment, ...]:
    return tuple(
        TranslationRubricComment(
            id=f'{key}-{level}', level=level, text=f'Level {level}'
        )
        for level in (0, 25, 50, 75, 100)
    )


def _criterion(
    *,
    key: str = 'semantic_preservation',
    weight_percentage: int = 70,
    comments: tuple[TranslationRubricComment, ...] | None = None,
    inconclusive_id: str = 'semantic_preservation-unknown',
) -> TranslationRubricCriterion:
    return TranslationRubricCriterion(
        key=key,
        name='Semantic preservation',
        description='Assesses whether meaning is preserved',
        weight_percentage=weight_percentage,
        required=True,
        fixed_comments=comments if comments is not None else _comments(key),
        inconclusive_comment=TranslationInconclusiveComment(
            id=inconclusive_id, text='Insufficient evidence'
        ),
    )


def test_should_build_a_valid_translation_rubric_criterion() -> None:
    criterion = _criterion()

    assert criterion.key == 'semantic_preservation'
    assert tuple(sorted(item.level for item in criterion.fixed_comments)) == (
        0,
        25,
        50,
        75,
        100,
    )


def test_should_reject_empty_key() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        _criterion(key='   ')


def test_should_reject_empty_name() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricCriterion(
            key='semantic_preservation',
            name='   ',
            description='Assesses semantic preservation',
            weight_percentage=70,
            required=True,
            fixed_comments=_comments(),
            inconclusive_comment=TranslationInconclusiveComment(
                id='semantic_preservation-unknown', text='Insufficient evidence'
            ),
        )


def test_should_reject_empty_description() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricCriterion(
            key='semantic_preservation',
            name='Semantic preservation',
            description='   ',
            weight_percentage=70,
            required=True,
            fixed_comments=_comments(),
            inconclusive_comment=TranslationInconclusiveComment(
                id='semantic_preservation-unknown', text='Insufficient evidence'
            ),
        )


def test_should_reject_weight_percentage_out_of_range() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        _criterion(weight_percentage=101)
    with pytest.raises(InvalidEvaluationRuleError):
        _criterion(weight_percentage=-1)


def test_should_reject_comment_with_invalid_level() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationRubricComment(id='bad', level=10, text='Invalid level')


def test_should_reject_fixed_comments_missing_a_level() -> None:
    incomplete = tuple(
        TranslationRubricComment(id=f'c-{level}', level=level, text=f'Level {level}')
        for level in (0, 25, 50, 75)
    )
    with pytest.raises(InvalidEvaluationRuleError):
        _criterion(comments=incomplete)


def test_should_reject_fixed_comments_with_duplicate_ids() -> None:
    duplicated = tuple(
        TranslationRubricComment(id='same-id', level=level, text=f'Level {level}')
        for level in (0, 25, 50, 75, 100)
    )
    with pytest.raises(InvalidEvaluationRuleError):
        _criterion(comments=duplicated)


def test_should_reject_inconclusive_comment_reusing_a_fixed_comment_id() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        _criterion(inconclusive_id='semantic_preservation-0')


def test_should_reject_empty_inconclusive_comment_text() -> None:
    with pytest.raises(InvalidEvaluationRuleError):
        TranslationInconclusiveComment(id='x', text='   ')
