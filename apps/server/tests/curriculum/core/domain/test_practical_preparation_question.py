from dataclasses import replace
import pytest

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    JavascriptInitialFile,
    JavascriptStdinQuestion,
    PracticalPreparationQuestion,
    PracticeCriterion,
    PracticeCriterionLevel,
    PracticeInsufficiencyRule,
    PracticePhotoRecord,
    SingleChoiceQuestion,
)
from shifu.curriculum.database.sqlalchemy.mappers.activity_mapper import (
    ActivityMapper,
)
from shifu.fakers.curriculum.structures import PracticalPreparationQuestionFaker


def _record(index: int) -> PracticePhotoRecord:
    return PracticePhotoRecord(
        key=f'record-{index}', label=f'Registro {index}', must_show='O prato.'
    )


def _criteria(*weights: int) -> tuple[PracticeCriterion, ...]:
    return tuple(
        PracticalPreparationQuestionFaker.criterion(
            f'criterion-{index}', f'Critério {index}', 'Descrição.', weight
        )
        for index, weight in enumerate(weights)
    )


def _question(
    *,
    records: tuple[PracticePhotoRecord, ...] | None = None,
    criteria: tuple[PracticeCriterion, ...] | None = None,
    insufficiency_rules: tuple[PracticeInsufficiencyRule, ...] = (),
) -> PracticalPreparationQuestion:
    return PracticalPreparationQuestionFaker.fake(
        records=records if records is not None else (_record(0),),
        criteria=criteria if criteria is not None else _criteria(100),
        insufficiency_rules=insufficiency_rules,
    )


def _activity(
    question: PracticalPreparationQuestion,
    *,
    activity_type: ActivityType = ActivityType.LEARNING,
    extra_questions: tuple[SingleChoiceQuestion, ...] = (),
) -> Activity:
    parts = (
        CorrectnessEvaluationPart(
            question_key=question.key, weight_percentage=100 - 10 * len(extra_questions)
        ),
        *(
            CorrectnessEvaluationPart(question_key=item.key, weight_percentage=10)
            for item in extra_questions
        ),
    )
    return Activity.create(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='Legumes salteados',
        objective='Preparar legumes salteados',
        questions=(question, *extra_questions),
        evaluation_rule=EvaluationRule(parts=parts),
    )


class TestPracticalPreparationQuestion:
    @pytest.mark.parametrize('size', (1, 5))
    def test_should_accept_one_to_five_records(self, size: int) -> None:
        records = tuple(_record(index) for index in range(size))

        assert len(_question(records=records).records) == size

    @pytest.mark.parametrize('size', (0, 6))
    def test_should_reject_record_count_outside_range(self, size: int) -> None:
        records = tuple(_record(index) for index in range(size))

        with pytest.raises(InvalidActivityError):
            _question(records=records)

    def test_should_reject_repeated_record_keys(self) -> None:
        with pytest.raises(InvalidActivityError):
            _question(records=(_record(0), _record(0)))

    @pytest.mark.parametrize('weights', ((100,), (40, 40, 20), (60, 40)))
    def test_should_accept_weights_that_sum_to_one_hundred(
        self, weights: tuple[int, ...]
    ) -> None:
        assert len(_question(criteria=_criteria(*weights)).criteria) == len(weights)

    @pytest.mark.parametrize('weights', ((99,), (101,), (50, 49), (60, 41), (0, 100)))
    def test_should_reject_weights_that_do_not_sum_to_one_hundred(
        self, weights: tuple[int, ...]
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _question(criteria=_criteria(*weights))

    def test_should_reject_repeated_criterion_keys(self) -> None:
        first = _criteria(50)[0]
        second = replace(
            first,
            levels=tuple(
                PracticeCriterionLevel(
                    score=level.score,
                    description=level.description,
                    comment_key=f'other-{level.score}',
                )
                for level in first.levels
            ),
        )

        with pytest.raises(InvalidActivityError):
            _question(criteria=(first, second))

    @pytest.mark.parametrize('missing_score', (0, 25, 50, 75, 100))
    def test_should_reject_criterion_without_a_required_level(
        self, missing_score: int
    ) -> None:
        criterion = _criteria(100)[0]
        levels = tuple(
            level for level in criterion.levels if level.score != missing_score
        )

        with pytest.raises(InvalidActivityError):
            replace(criterion, levels=levels)

    def test_should_reject_level_with_score_outside_the_scale(self) -> None:
        with pytest.raises(InvalidActivityError):
            PracticeCriterionLevel(score=10, description='Texto', comment_key='key')

    @pytest.mark.parametrize('field', ('description', 'comment_key'))
    def test_should_reject_level_without_description_or_comment(
        self, field: str
    ) -> None:
        values = {'score': 50, 'description': 'Texto', 'comment_key': 'key'}
        values[field] = ' '

        with pytest.raises(InvalidActivityError):
            PracticeCriterionLevel(**values)  # type: ignore[arg-type]

    def test_should_reject_repeated_level_comment_keys(self) -> None:
        criterion = _criteria(100)[0]
        levels = tuple(
            PracticeCriterionLevel(
                score=level.score, description=level.description, comment_key='same'
            )
            for level in criterion.levels
        )

        with pytest.raises(InvalidActivityError):
            replace(criterion, levels=levels)

    def test_should_accept_insufficiency_rule_for_existing_record_and_criterion(
        self,
    ) -> None:
        rule = PracticeInsufficiencyRule(
            record_key='record-0',
            criterion_keys=('criterion-0',),
            comment='Refaça a foto.',
        )

        assert _question(insufficiency_rules=(rule,)).insufficiency_rules == (rule,)

    @pytest.mark.parametrize(
        ('record_key', 'criterion_keys'),
        (('missing', ('criterion-0',)), ('record-0', ('missing',))),
    )
    def test_should_reject_insufficiency_rule_pointing_to_missing_keys(
        self, record_key: str, criterion_keys: tuple[str, ...]
    ) -> None:
        rule = PracticeInsufficiencyRule(
            record_key=record_key, criterion_keys=criterion_keys, comment='Refaça.'
        )

        with pytest.raises(InvalidActivityError):
            _question(insufficiency_rules=(rule,))

    def test_should_reject_insufficiency_rule_without_criteria_or_comment(
        self,
    ) -> None:
        with pytest.raises(InvalidActivityError):
            PracticeInsufficiencyRule(
                record_key='record-0', criterion_keys=(), comment='Refaça.'
            )
        with pytest.raises(InvalidActivityError):
            PracticeInsufficiencyRule(
                record_key='record-0', criterion_keys=('criterion-0',), comment=' '
            )

    def test_should_reject_question_without_concept_mapping(self) -> None:
        with pytest.raises(InvalidActivityError):
            PracticalPreparationQuestionFaker.fake(concept_criteria=())

    def test_should_reject_unknown_difficulty(self) -> None:
        with pytest.raises(InvalidActivityError):
            PracticalPreparationQuestionFaker.fake(difficulty='extreme')


class TestPracticalPreparationActivity:
    def test_should_publish_exactly_one_question_in_learning_activities(self) -> None:
        question = PracticalPreparationQuestionFaker.fake()

        assert _activity(question).questions == (question,)

    def test_should_accept_questions_scored_by_fixed_rules(self) -> None:
        question = PracticalPreparationQuestionFaker.fake()
        extra = SingleChoiceQuestion(
            key='extra',
            prompt='Pergunta',
            options=(
                ChoiceOption(key='a', text='A', is_correct=True),
                ChoiceOption(key='b', text='B', is_correct=False),
            ),
            correct_explanation='Certo.',
            incorrect_explanation='Errado.',
        )

        assert _activity(question, extra_questions=(extra,)).questions == (
            question,
            extra,
        )

    def test_should_reject_a_question_scored_by_another_ai_rubric(self) -> None:
        question = PracticalPreparationQuestionFaker.fake()
        code = JavascriptStdinQuestion(
            key='code',
            prompt='Imprima o resultado.',
            initial_files=(
                JavascriptInitialFile(path='index.js', content='', editable=True),
            ),
            entrypoint='index.js',
            fixed_dependencies=(),
            permitted_commands=(),
            concept_criteria=(),
        )

        with pytest.raises(InvalidActivityError):
            Activity.create(
                id='activity-1',
                competency_id='competency-1',
                activity_type=ActivityType.LEARNING,
                difficulty=ActivityDifficulty.EASY,
                title='Misturada',
                objective='Misturada',
                questions=(question, code),
                evaluation_rule=EvaluationRule(
                    parts=(
                        CorrectnessEvaluationPart(
                            question_key=question.key, weight_percentage=50
                        ),
                        CorrectnessEvaluationPart(
                            question_key='code', weight_percentage=50
                        ),
                    )
                ),
            )

    def test_should_reject_two_practical_questions(self) -> None:
        first = PracticalPreparationQuestionFaker.fake(key='first')
        second = PracticalPreparationQuestionFaker.fake(key='second')

        with pytest.raises(InvalidActivityError):
            Activity.create(
                id='activity-1',
                competency_id='competency-1',
                activity_type=ActivityType.LEARNING,
                difficulty=ActivityDifficulty.EASY,
                title='Dois',
                objective='Dois',
                questions=(first, second),
                evaluation_rule=EvaluationRule(
                    parts=(
                        CorrectnessEvaluationPart(
                            question_key='first', weight_percentage=50
                        ),
                        CorrectnessEvaluationPart(
                            question_key='second', weight_percentage=50
                        ),
                    )
                ),
            )

    def test_should_reject_diagnostic_activity(self) -> None:
        with pytest.raises(InvalidActivityError):
            _activity(
                PracticalPreparationQuestionFaker.fake(),
                activity_type=ActivityType.DIAGNOSTIC,
            )

    def test_should_survive_a_mapper_round_trip(self) -> None:
        activity = _activity(PracticalPreparationQuestionFaker.fake())

        restored = ActivityMapper.to_domain(ActivityMapper.to_model(activity))

        assert restored == activity
