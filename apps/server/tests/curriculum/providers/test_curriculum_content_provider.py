from shifu.curriculum.core.domain.structures import (
    ChoiceConceptCriterion,
    CorrectnessEvaluationPart,
    EvaluationRule,
    OrderingQuestion,
    OrderingStep,
)
from shifu.curriculum.providers.curriculum_content_provider.curriculum_content_provider import (
    has_executable_evidence,
)
from shifu.fakers.curriculum.entities import ActivityFaker


def ordering_question(key: str, *, incomplete_scores: bool = False) -> OrderingQuestion:
    return OrderingQuestion(
        key=key,
        prompt='Organize as etapas.',
        steps=(
            OrderingStep(key='prepare', text='Preparar'),
            OrderingStep(key='cook', text='Cozinhar'),
            OrderingStep(key='serve', text='Servir'),
        ),
        accepted_orders=(('prepare', 'cook', 'serve'),),
        correct_explanation='Sequência aceita.',
        incorrect_explanation='Revise a sequência.',
        concept_criteria=(
            ChoiceConceptCriterion(
                concept_id='concept-order',
                criterion='Ordena o processo.',
                examples='Prepara antes de cozinhar.',
                limits='A apresentação pode variar.',
                correct_score=100,
                incorrect_score=None if incomplete_scores else 0,
            ),
        ),
    )


def test_should_mark_ordering_activity_evidence_executable() -> None:
    question_keys = ('q1', 'q2', 'q3')
    activity = ActivityFaker.fake(
        competency_id='competency-1',
        questions=tuple(ordering_question(key) for key in question_keys),
        evaluation_rule=EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(
                    question_key=key,
                    weight_percentage=weight,
                )
                for key, weight in zip(question_keys, (34, 33, 33), strict=True)
            ),
        ),
    )

    assert has_executable_evidence(activity, {'concept-order': 100})


def test_should_reject_ordering_activity_without_both_concept_scores() -> None:
    question_keys = ('q1', 'q2', 'q3')
    activity = ActivityFaker.fake(
        competency_id='competency-1',
        questions=(
            ordering_question('q1', incomplete_scores=True),
            ordering_question('q2'),
            ordering_question('q3'),
        ),
        evaluation_rule=EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(
                    question_key=key,
                    weight_percentage=weight,
                )
                for key, weight in zip(question_keys, (34, 33, 33), strict=True)
            ),
        ),
    )

    assert not has_executable_evidence(activity, {'concept-order': 100})
