from datetime import UTC, datetime
from decimal import Decimal

from pydantic import TypeAdapter

from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    ActivityEvaluationStatus,
)
from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceAttemptDetail,
    OrderingQuestionDetail,
    OrderingResultDetail,
    OrderingStepDetail,
    VerifiedOrderingDetail,
)
from shifu.learning.rest.controllers.get_choice_activity_controller import (
    OrderingQuestionResponse,
    Response as ActivityResponse,
)
from shifu.learning.rest.controllers.get_choice_attempt_controller import (
    OrderingQuestionResultResponse,
    Response as AttemptResponse,
)


def test_activity_response_serializes_private_ordering_state() -> None:
    question = OrderingQuestionDetail(
        key='sequence',
        kind='ordering',
        prompt='Organize as etapas.',
        steps=(
            OrderingStepDetail(key='prepare', text='Preparar'),
            OrderingStepDetail(key='cook', text='Cozinhar'),
            OrderingStepDetail(key='serve', text='Servir'),
        ),
        initial_ordered_step_keys=('cook', 'prepare', 'serve'),
        verified=VerifiedOrderingDetail(
            ordered_step_keys=('prepare', 'cook', 'serve'),
            score=Decimal(100),
            is_correct=True,
            explanation='A sequência está correta.',
        ),
    )
    detail = ChoiceActivityDetail(
        activity_id='activity',
        title='Atividade',
        difficulty=ActivityDifficulty.EASY,
        questions=(question,),
        can_submit=True,
        ordering_passage_key='passage-key',
    )

    response = TypeAdapter[ActivityResponse](ActivityResponse).validate_python(
        detail,
        from_attributes=True,
    )

    question_response = response.questions[0]
    assert isinstance(question_response, OrderingQuestionResponse)
    assert question_response.kind == 'ordering'
    assert question_response.initial_ordered_step_keys == (
        'cook',
        'prepare',
        'serve',
    )
    assert question_response.verified is not None
    assert question_response.verified.ordered_step_keys == (
        'prepare',
        'cook',
        'serve',
    )
    assert response.ordering_passage_key == 'passage-key'


def test_attempt_response_serializes_disclosed_or_protected_ordering_result() -> None:
    def response_for(
        accepted_orders: tuple[tuple[str, ...], ...],
    ) -> AttemptResponse:
        detail = ChoiceAttemptDetail(
            attempt_id='attempt',
            activity_id='activity',
            status=ActivityEvaluationStatus.COMPLETED,
            submitted_at=datetime(2026, 11, 18, tzinfo=UTC),
            retry_allowed=False,
            questions=(
                OrderingResultDetail(
                    question_key='sequence',
                    kind='ordering',
                    prompt='Organize as etapas.',
                    steps=(
                        OrderingStepDetail(key='prepare', text='Preparar'),
                        OrderingStepDetail(key='cook', text='Cozinhar'),
                        OrderingStepDetail(key='serve', text='Servir'),
                    ),
                    submitted_step_keys=('cook', 'prepare', 'serve'),
                    score=Decimal(0),
                    is_correct=False,
                    explanation='Revise a sequência.',
                    accepted_orders=accepted_orders,
                ),
            ),
        )
        return TypeAdapter[AttemptResponse](AttemptResponse).validate_python(
            detail,
            from_attributes=True,
        )

    protected = response_for(())
    protected_question = protected.questions[0]
    assert isinstance(protected_question, OrderingQuestionResultResponse)
    assert protected_question.kind == 'ordering'
    assert (
        'accepted_orders'
        not in protected.model_dump(exclude_defaults=True)['questions'][0]
    )

    disclosed = response_for((('prepare', 'cook', 'serve'),))
    disclosed_question = disclosed.questions[0]
    assert isinstance(disclosed_question, OrderingQuestionResultResponse)
    assert disclosed_question.accepted_orders == (('prepare', 'cook', 'serve'),)
