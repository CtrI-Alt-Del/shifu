from dataclasses import replace
from typing import Any

import pytest
from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.fakers.curriculum.structures import PairMatchingQuestionFaker
from shifu.curriculum.core.domain.structures import (
    CorrectnessEvaluationPart,
    EvaluationRule,
    PairMatchingConceptCriterion,
    PairMatchingItem,
    PairMatchingPair,
    PairMatchingQuestion,
)


def _items(prefix: str, count: int) -> tuple[PairMatchingItem, ...]:
    return tuple(
        PairMatchingItem(key=f'{prefix}-{index}', text=f'{prefix} {index}')
        for index in range(count)
    )


def _criterion(
    concept_id: str = 'concept-1',
    *,
    full_score: int | None = 100,
    partial_score: int | None = 60,
    incorrect_score: int | None = 0,
) -> PairMatchingConceptCriterion:
    return PairMatchingQuestionFaker.concept_criterion(
        concept_id,
        full_score=full_score,
        partial_score=partial_score,
        incorrect_score=incorrect_score,
    )


def _question(
    size: int = 3,
    *,
    key: str = 'pairs-1',
    translation_order: tuple[int, ...] | None = None,
    **overrides: Any,
) -> PairMatchingQuestion:
    return PairMatchingQuestionFaker.fake(
        key=key,
        size=size,
        translation_order=translation_order,
        concept_criteria=overrides.pop('concept_criteria', (_criterion(),)),
        **overrides,
    )


def _with(size: int, overrides: dict[str, Any]) -> PairMatchingQuestion:
    return _question(size, **overrides)


def _criterion_with(overrides: dict[str, Any]) -> PairMatchingConceptCriterion:
    return _criterion(**overrides)


def _activity(
    question: PairMatchingQuestion,
    activity_type: ActivityType = ActivityType.LEARNING,
) -> Activity:
    return Activity(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='Pair activity',
        objective='Match vocabulary',
        questions=(question,),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key=question.key, weight_percentage=100
                ),
            )
        ),
    )


@pytest.mark.parametrize('size', [2, 3, 8])
def test_should_build_a_valid_pair_matching_question(size: int) -> None:
    question = _question(size)

    assert question.kind == 'pair_matching'
    assert len(question.words) == size
    assert len(question.translations) == size


@pytest.mark.parametrize('size', [1, 9])
def test_should_reject_pair_counts_outside_two_to_eight(size: int) -> None:
    words = _items('word', size)
    translations = _items('translation', size)

    with pytest.raises(InvalidActivityError):
        _question(
            2,
            words=words,
            translations=translations,
            correct_pairs=tuple(
                PairMatchingPair(
                    word_key=f'word-{i}', translation_key=f'translation-{i}'
                )
                for i in range(size)
            ),
        )


def test_should_reject_unequal_item_sets() -> None:
    question = _question(3)

    with pytest.raises(InvalidActivityError):
        replace(question, translations=question.translations[:2])


@pytest.mark.parametrize('field', ['words', 'translations'])
def test_should_reject_repeated_item_keys(field: str) -> None:
    question = _question(3)
    items = getattr(question, field)
    repeated = (items[0], replace(items[1], key=items[0].key), items[2])

    with pytest.raises(InvalidActivityError):
        replace(question, **{field: repeated})


@pytest.mark.parametrize('field', ['words', 'translations'])
def test_should_reject_repeated_item_texts(field: str) -> None:
    question = _question(3)
    items = getattr(question, field)
    repeated = (items[0], replace(items[1], text=items[0].text), items[2])

    with pytest.raises(InvalidActivityError):
        replace(question, **{field: repeated})


def test_should_reject_an_answer_key_that_reuses_a_word() -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            3,
            correct_pairs=(
                PairMatchingPair(word_key='word-0', translation_key='translation-0'),
                PairMatchingPair(word_key='word-0', translation_key='translation-1'),
                PairMatchingPair(word_key='word-2', translation_key='translation-2'),
            ),
        )


def test_should_reject_an_answer_key_that_reuses_a_translation() -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            3,
            correct_pairs=(
                PairMatchingPair(word_key='word-0', translation_key='translation-0'),
                PairMatchingPair(word_key='word-1', translation_key='translation-0'),
                PairMatchingPair(word_key='word-2', translation_key='translation-2'),
            ),
        )


def test_should_reject_an_answer_key_with_unknown_keys() -> None:
    with pytest.raises(InvalidActivityError):
        _question(
            3,
            correct_pairs=(
                PairMatchingPair(word_key='word-0', translation_key='translation-0'),
                PairMatchingPair(word_key='word-1', translation_key='translation-1'),
                PairMatchingPair(word_key='word-9', translation_key='translation-2'),
            ),
        )


def test_should_reject_a_display_order_aligned_with_the_answer_key() -> None:
    with pytest.raises(InvalidActivityError):
        _question(3, translation_order=(0, 1, 2))


def test_should_accept_a_display_order_that_differs_in_only_one_position() -> None:
    question = _question(3, translation_order=(0, 2, 1))

    assert question.translations[0].key == 'translation-0'


@pytest.mark.parametrize(
    'field', ['full_explanation', 'partial_explanation', 'incorrect_explanation']
)
def test_should_reject_empty_explanations(field: str) -> None:
    with pytest.raises(InvalidActivityError):
        _with(3, {field: '  '})


@pytest.mark.parametrize(
    'field', ['key', 'prompt', 'source_language', 'target_language']
)
def test_should_reject_empty_text_fields(field: str) -> None:
    with pytest.raises(InvalidActivityError):
        _with(3, {field: ''})


def test_should_reject_repeated_concept_ids() -> None:
    with pytest.raises(InvalidActivityError):
        _question(3, concept_criteria=(_criterion('c1'), _criterion('c1')))


@pytest.mark.parametrize('score', [-1, 101])
@pytest.mark.parametrize('field', ['full_score', 'partial_score', 'incorrect_score'])
def test_should_reject_concept_scores_outside_the_percentage_range(
    field: str, score: int
) -> None:
    with pytest.raises(InvalidActivityError):
        _criterion_with({field: score})


def test_should_accept_absent_concept_scores() -> None:
    criterion = _criterion(full_score=None, partial_score=None, incorrect_score=None)

    assert criterion.full_score is None


def test_should_accept_an_activity_with_a_pair_matching_question() -> None:
    activity = _activity(_question(3))

    assert isinstance(activity.questions[0], PairMatchingQuestion)


def test_should_reject_a_pair_matching_question_in_a_diagnostic_activity() -> None:
    with pytest.raises(InvalidActivityError):
        _activity(_question(3), activity_type=ActivityType.DIAGNOSTIC)
