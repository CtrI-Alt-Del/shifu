from itertools import permutations

import pytest

from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceConceptCriterion,
    CorrectnessEvaluationPart,
    EvaluationRule,
    OrderingQuestion,
    OrderingStep,
)


def _valid_question(
    *,
    steps: tuple[OrderingStep, ...] | None = None,
    accepted_orders: tuple[tuple[str, ...], ...] | None = None,
) -> OrderingQuestion:
    question_steps = steps or (
        OrderingStep(key='prepare', text='Separar os ingredientes'),
        OrderingStep(key='heat', text='Aquecer a panela'),
        OrderingStep(key='cook', text='Cozinhar os ingredientes'),
    )
    return OrderingQuestion(
        key='sequence',
        prompt='Organize as etapas',
        steps=question_steps,
        accepted_orders=(
            accepted_orders
            if accepted_orders is not None
            else (('prepare', 'heat', 'cook'),)
        ),
        correct_explanation='A sequência atende ao procedimento.',
        incorrect_explanation='Revise a relação entre as etapas.',
        concept_criteria=(
            ChoiceConceptCriterion(
                concept_id='concept-1',
                criterion='Organiza as etapas do procedimento.',
                examples='Prepara os ingredientes antes de cozinhar.',
                limits='A ordem não mede a qualidade do preparo.',
                correct_score=100,
                incorrect_score=0,
            ),
        ),
    )


def _ordering_activity(activity_type: ActivityType) -> Activity:
    question = _valid_question()
    return Activity.create(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='Sequência',
        objective='Organizar as etapas',
        questions=(question,),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key=question.key,
                    weight_percentage=100,
                ),
            )
        ),
    )


class TestOrderingQuestion:
    def test_should_accept_three_to_eight_distinct_steps_and_alternative_orders(
        self,
    ) -> None:
        for size in (3, 8):
            steps = tuple(
                OrderingStep(key=f'step-{index}', text=f'Etapa {index}')
                for index in range(size)
            )
            accepted = (
                tuple(step.key for step in steps),
                tuple(reversed(tuple(step.key for step in steps))),
            )
            question = _valid_question(steps=steps, accepted_orders=accepted)

            assert question.accepted_orders == accepted

    @pytest.mark.parametrize('size', (2, 9))
    def test_should_reject_step_count_outside_supported_range(self, size: int) -> None:
        steps = tuple(
            OrderingStep(key=f'step-{index}', text=f'Etapa {index}')
            for index in range(size)
        )

        with pytest.raises(InvalidActivityError):
            _valid_question(steps=steps)

    @pytest.mark.parametrize(
        'steps',
        (
            (
                OrderingStep(key='same', text='Primeira'),
                OrderingStep(key='same', text='Segunda'),
                OrderingStep(key='third', text='Terceira'),
            ),
            (
                OrderingStep(key='first', text='Etapa'),
                OrderingStep(key='second', text='etapa'),
                OrderingStep(key='third', text='Final'),
            ),
        ),
    )
    def test_should_reject_duplicate_step_identity_or_text(
        self, steps: tuple[OrderingStep, ...]
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _valid_question(steps=steps)

    @pytest.mark.parametrize(
        'accepted_orders',
        (
            (),
            (('prepare', 'heat'),),
            (('prepare', 'heat', 'prepare'),),
            (
                ('prepare', 'heat', 'cook'),
                ('prepare', 'heat', 'cook'),
            ),
            tuple(permutations(('prepare', 'heat', 'cook'))),
        ),
    )
    def test_should_reject_missing_duplicate_or_exhaustive_accepted_orders(
        self, accepted_orders: tuple[tuple[str, ...], ...]
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _valid_question(accepted_orders=accepted_orders)

    def test_should_allow_ordering_only_in_learning_activities(self) -> None:
        assert _ordering_activity(ActivityType.LEARNING).questions == (
            _valid_question(),
        )

        with pytest.raises(InvalidActivityError):
            _ordering_activity(ActivityType.DIAGNOSTIC)
