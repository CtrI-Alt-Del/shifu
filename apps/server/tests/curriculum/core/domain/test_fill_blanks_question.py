from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal

import pytest

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    FillBlanksBankWord,
    FillBlanksBlank,
    FillBlanksConceptCriterion,
    FillBlanksSegment,
    SingleChoiceQuestion,
)
from shifu.fakers.curriculum.structures import FillBlanksQuestionFaker
from shifu.fakers.shared.curriculum_fill_blanks_question_snapshot_faker import (
    CurriculumFillBlanksQuestionSnapshotFaker,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumFillBlanksBlankSnapshot,
    CurriculumFillBlanksConceptCriterionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumFillBlanksSegmentSnapshot,
    CurriculumLearningActivitySnapshot,
)


def _blank_segments(*blank_keys: str) -> tuple[FillBlanksSegment, ...]:
    return tuple(FillBlanksSegment(blank_key=key) for key in blank_keys)


def _criterion(
    *blank_keys: str, concept_id: str = 'concept-1'
) -> FillBlanksConceptCriterion:
    return FillBlanksConceptCriterion(
        concept_id=concept_id,
        criterion='Criterion',
        examples='Example',
        limits='Limit',
        blank_keys=blank_keys,
    )


def _choice() -> SingleChoiceQuestion:
    return SingleChoiceQuestion(
        key='choice-1',
        prompt='Pick',
        options=(
            ChoiceOption(key='a', text='A', is_correct=True),
            ChoiceOption(key='b', text='B', is_correct=False),
        ),
        correct_explanation='Right',
        incorrect_explanation='Wrong',
    )


def _activity(
    activity_type: ActivityType = ActivityType.LEARNING,
    parts: tuple[CorrectnessEvaluationPart, ...] | None = None,
) -> Activity:
    fill = FillBlanksQuestionFaker.fake()
    second = replace(_choice(), key='choice-2')
    return Activity.create(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='English',
        objective='Practice the present simple',
        questions=(fill, _choice(), second),
        evaluation_rule=EvaluationRule(
            parts=parts
            or (
                CorrectnessEvaluationPart(question_key='fill-1', weight_percentage=40),
                CorrectnessEvaluationPart(
                    question_key='choice-1', weight_percentage=30
                ),
                CorrectnessEvaluationPart(
                    question_key='choice-2', weight_percentage=30
                ),
            )
        ),
    )


class TestFillBlanksQuestion:
    def test_should_accept_content_with_alternatives_distractor_and_repeated_word(
        self,
    ) -> None:
        question = FillBlanksQuestionFaker.fake()

        assert question.kind == 'fill_blanks'
        assert [word.word for word in question.bank].count('day') == 2
        assert 'go' not in {
            word for blank in question.blanks for word in blank.accepted_words
        }
        assert question.blanks[0].accepted_words == ('goes', 'walks')

    def test_should_trim_words_and_keys(self) -> None:
        blank = FillBlanksBlank(key=' b1 ', accepted_words=(' goes ',))
        word = FillBlanksBankWord(key=' w1 ', word=' goes ')

        assert (blank.key, blank.accepted_words) == ('b1', ('goes',))
        assert (word.key, word.word) == ('w1', 'goes')

    def test_should_find_a_solution_that_needs_an_augmenting_assignment(self) -> None:
        question = FillBlanksQuestionFaker.fake(
            segments=_blank_segments('b1', 'b2'),
            blanks=(
                FillBlanksBlank(key='b1', accepted_words=('go', 'walk')),
                FillBlanksBlank(key='b2', accepted_words=('go',)),
            ),
            bank=(
                FillBlanksBankWord(key='w1', word='go'),
                FillBlanksBankWord(key='w2', word='walk'),
            ),
            concept_criteria=(_criterion('b1', 'b2'),),
        )

        assert len(question.blanks) == 2

    @pytest.mark.parametrize(
        'overrides',
        (
            {
                'segments': _blank_segments('b1'),
                'blanks': (),
            },
            {
                'blanks': (
                    FillBlanksBlank(key='b1', accepted_words=('goes',)),
                    FillBlanksBlank(key='b1', accepted_words=('does',)),
                    FillBlanksBlank(key='b3', accepted_words=('day',)),
                ),
            },
            {
                'bank': (
                    FillBlanksBankWord(key='w1', word='goes'),
                    FillBlanksBankWord(key='w1', word='does'),
                    FillBlanksBankWord(key='w4', word='day'),
                ),
            },
            {'segments': _blank_segments('b1', 'b2', 'b3', 'unknown')},
            {'segments': _blank_segments('b1', 'b2')},
            {'segments': _blank_segments('b3', 'b2', 'b1')},
            {'segments': _blank_segments('b1', 'b2', 'b3', 'b3')},
            {
                'blanks': (
                    FillBlanksBlank(key='b1', accepted_words=('goes',)),
                    FillBlanksBlank(key='b2', accepted_words=('goes',)),
                    FillBlanksBlank(key='b3', accepted_words=('day',)),
                ),
            },
            {
                'bank': (
                    FillBlanksBankWord(key='w1', word='goes'),
                    FillBlanksBankWord(key='w3', word='does'),
                    FillBlanksBankWord(key='w6', word='go'),
                ),
            },
            {'concept_criteria': ()},
            {'concept_criteria': (_criterion('b1', 'missing'),)},
            {
                'concept_criteria': (
                    _criterion('b1', concept_id='same'),
                    _criterion('b2', 'b3', concept_id='same'),
                )
            },
            {'partial_explanation': None},
        ),
        ids=(
            'no-blanks',
            'duplicate-blank-key',
            'duplicate-bank-key',
            'segment-references-unknown-blank',
            'blank-absent-from-segments',
            'blanks-out-of-segment-order',
            'blank-referenced-twice',
            'solution-needs-an-occurrence-twice',
            'solution-lacks-a-word',
            'no-concept-criteria',
            'criterion-with-unknown-blank',
            'duplicate-concept',
            'partial-explanation-missing-for-two-blanks',
        ),
    )
    def test_should_reject_invalid_content(self, overrides: dict[str, object]) -> None:
        with pytest.raises(InvalidActivityError):
            FillBlanksQuestionFaker.fake(**overrides)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        'field', ('correct_explanation', 'incorrect_explanation', 'prompt', 'key')
    )
    def test_should_reject_blank_required_text(self, field: str) -> None:
        with pytest.raises(InvalidActivityError):
            replace(FillBlanksQuestionFaker.fake(), **{field: '  '})

    def test_should_reject_a_partial_explanation_on_a_single_blank_question(
        self,
    ) -> None:
        with pytest.raises(InvalidActivityError):
            FillBlanksQuestionFaker.fake(
                segments=_blank_segments('b1'),
                blanks=(FillBlanksBlank(key='b1', accepted_words=('goes',)),),
                bank=(FillBlanksBankWord(key='w1', word='goes'),),
                concept_criteria=(_criterion('b1'),),
            )

        question = FillBlanksQuestionFaker.fake(
            segments=_blank_segments('b1'),
            blanks=(FillBlanksBlank(key='b1', accepted_words=('goes',)),),
            bank=(FillBlanksBankWord(key='w1', word='goes'),),
            concept_criteria=(_criterion('b1'),),
            partial_explanation=None,
        )
        assert question.partial_explanation is None

    @pytest.mark.parametrize(
        'build',
        (
            lambda: FillBlanksSegment(),
            lambda: FillBlanksSegment(text='a', blank_key='b1'),
            lambda: FillBlanksBlank(key='b1', accepted_words=()),
            lambda: FillBlanksBlank(key='b1', accepted_words=('go', 'go')),
            lambda: FillBlanksBlank(key='b1', accepted_words=(' ',)),
            lambda: FillBlanksBankWord(key='w1', word=' '),
            lambda: _criterion(),
            lambda: _criterion('b1', 'b1'),
        ),
        ids=(
            'segment-empty',
            'segment-both',
            'blank-without-words',
            'blank-duplicate-words',
            'blank-blank-word',
            'bank-blank-word',
            'criterion-without-blanks',
            'criterion-duplicate-blanks',
        ),
    )
    def test_should_reject_invalid_parts(self, build: object) -> None:
        with pytest.raises(InvalidActivityError):
            build()  # type: ignore[operator]

    def test_should_only_accept_the_fill_blanks_discriminator(self) -> None:
        with pytest.raises(InvalidActivityError):
            replace(FillBlanksQuestionFaker.fake(), kind='other')  # type: ignore[arg-type]

    def test_should_accept_a_learning_activity_and_reject_a_diagnostic_one(
        self,
    ) -> None:
        assert _activity().questions[0].key == 'fill-1'

        with pytest.raises(InvalidActivityError):
            _activity(ActivityType.DIAGNOSTIC)

    def test_should_require_one_correctness_part_for_every_question(self) -> None:
        with pytest.raises(InvalidActivityError):
            _activity(
                parts=(
                    CorrectnessEvaluationPart(
                        question_key='fill-1', weight_percentage=50
                    ),
                    CorrectnessEvaluationPart(
                        question_key='choice-1', weight_percentage=50
                    ),
                )
            )


def _snapshot() -> CurriculumLearningActivitySnapshot:
    fill = CurriculumFillBlanksQuestionSnapshotFaker.fake()
    choice = tuple(
        CurriculumChoiceQuestionSnapshot(
            key=f'choice-{number}',
            kind='single_choice',
            prompt='Pick',
            options=(
                CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
            ),
            correct_explanation='Right',
            incorrect_explanation='Wrong',
        )
        for number in (1, 2)
    )
    return CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='English',
        questions=(fill, *choice),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='fill-1', weight_percentage=Decimal(40)
            ),
            CurriculumChoicePartSnapshot(
                question_key='choice-1', weight_percentage=Decimal(30)
            ),
            CurriculumChoicePartSnapshot(
                question_key='choice-2', weight_percentage=Decimal(30)
            ),
        ),
        required_concept_ids=(),
        activity_type='learning',
        schema_version=1,
        revision='revision-1',
    )


def _snapshot_mutations() -> dict[
    str, Callable[[CurriculumFillBlanksQuestionSnapshot], object]
]:
    return {
        'duplicate-blank': lambda fill: replace(
            fill, blanks=(fill.blanks[0], fill.blanks[0], fill.blanks[2])
        ),
        'duplicate-word-key': lambda fill: replace(
            fill, bank=(fill.bank[0], fill.bank[0])
        ),
        'blank-absent-from-segments': lambda fill: replace(
            fill, segments=fill.segments[:-2]
        ),
        'partial-explanation-missing': lambda fill: replace(
            fill, partial_explanation=None
        ),
        'no-concept-criteria': lambda fill: replace(fill, concept_criteria=()),
        'criterion-with-unknown-blank': lambda fill: replace(
            fill,
            concept_criteria=(
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id='c',
                    criterion='x',
                    examples='y',
                    limits='z',
                    blank_keys=('missing',),
                ),
            ),
        ),
        'unknown-kind': lambda fill: replace(fill, kind='other'),
    }


class TestCurriculumFillBlanksSnapshots:
    def test_should_publish_a_learning_activity_that_mixes_fill_blanks_and_choice(
        self,
    ) -> None:
        assert _snapshot().questions[0].key == 'fill-1'

    @pytest.mark.parametrize('name', tuple(_snapshot_mutations()))
    def test_should_reject_inconsistent_question_snapshots(self, name: str) -> None:
        fill = CurriculumFillBlanksQuestionSnapshotFaker.fake()

        with pytest.raises(ValidationError):
            _snapshot_mutations()[name](fill)

    @pytest.mark.parametrize(
        'build',
        (
            lambda: CurriculumFillBlanksSegmentSnapshot(),
            lambda: CurriculumFillBlanksBlankSnapshot(key='b1', accepted_words=()),
        ),
        ids=('segment-empty', 'blank-without-words'),
    )
    def test_should_reject_invalid_snapshot_parts(self, build: object) -> None:
        with pytest.raises(ValidationError):
            build()  # type: ignore[operator]

    def test_should_reject_fill_blanks_in_a_diagnostic_snapshot(self) -> None:
        with pytest.raises(ValidationError):
            replace(
                _snapshot(),
                activity_type='diagnostic',
                diagnostic_revision='diagnostic-1',
            )

    def test_should_reject_a_fill_blanks_question_paired_with_a_code_rubric_part(
        self,
    ) -> None:
        snapshot = _snapshot()
        wrong = replace(
            snapshot.parts[0],
            question_key='choice-1',
        )
        with pytest.raises(ValidationError):
            replace(snapshot, parts=(snapshot.parts[0], wrong, wrong))
