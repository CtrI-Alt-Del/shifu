from decimal import Decimal
from unittest.mock import create_autospec

from shifu.learning.core.domain.enums import ActivityDifficulty, SkillExperienceStatus
from shifu.learning.core.domain.structures import (
    ChoiceActivityDetail,
    ChoiceOptionDetail,
    ChoiceQuestionDetail,
    FillBlanksQuestionDetail,
    FillBlanksSegmentDetail,
    FillBlanksWordDetail,
    OrderingQuestionDetail,
    OrderingStepDetail,
    VerifiedOrderingDetail,
)
from shifu.learning.core.use_cases.get_choice_activity_use_case import (
    GetChoiceActivityUseCase,
)
from shifu.learning.providers.learning_mentor_context_provider import (
    LearningMentorContextProvider,
)
from shifu.learning.providers.mentor_activity_question_facts import (
    activity_question_facts,
)
from shifu.shared.core.domain.errors import NotFoundError


def _detail(*, is_diagnostic: bool = False) -> ChoiceActivityDetail:
    return ChoiceActivityDetail(
        activity_id='activity',
        title='Salteado',
        difficulty=ActivityDifficulty.EASY,
        questions=(
            ChoiceQuestionDetail(
                key='heat',
                kind='single_choice',
                prompt='Qual fogo usar?',
                options=(
                    ChoiceOptionDetail(key='a', text='Alto'),
                    ChoiceOptionDetail(key='b', text='Baixo'),
                ),
            ),
            OrderingQuestionDetail(
                key='steps',
                kind='ordering',
                prompt='Ordene o preparo.',
                steps=(
                    OrderingStepDetail(key='cut', text='Cortar'),
                    OrderingStepDetail(key='saute', text='Saltear'),
                ),
                initial_ordered_step_keys=('saute', 'cut'),
                verified=VerifiedOrderingDetail(
                    ordered_step_keys=('cut', 'saute'),
                    score=Decimal(100),
                    is_correct=True,
                    explanation='SEGREDO da correção',
                ),
            ),
            FillBlanksQuestionDetail(
                key='blank',
                prompt='Complete.',
                content_language='pt-BR',
                segments=(
                    FillBlanksSegmentDetail(text='Use fogo '),
                    FillBlanksSegmentDetail(blank_key='b1'),
                ),
                bank=(FillBlanksWordDetail(key='w1', word='alto'),),
            ),
        ),
        can_submit=True,
        is_diagnostic=is_diagnostic,
    )


class TestActivityQuestionFacts:
    def test_should_describe_what_the_learner_sees_without_results(self) -> None:
        facts = activity_question_facts(_detail())

        assert [key for key, _ in facts] == ['activity_questions'] * 3
        assert facts[0][1] == (
            'heat: questão 1 de 3 (escolha única): Qual fogo usar? | Opções: Alto; Baixo'
        )
        assert facts[1][1] == (
            'steps: questão 2 de 3 (ordenação): Ordene o preparo. '
            '| Etapas a ordenar: Cortar; Saltear'
        )
        assert facts[2][1] == (
            'blank: questão 3 de 3 (completar lacunas): Complete. '
            '| Frase: Use fogo ___ | Palavras: alto'
        )
        assert all('SEGREDO' not in value for _, value in facts)


class TestLearningMentorContextProviderActivityQuestions:
    def _provider(
        self,
    ) -> tuple[LearningMentorContextProvider, GetChoiceActivityUseCase]:
        activity = create_autospec(GetChoiceActivityUseCase, instance=True)
        activity.execute.return_value = _detail()
        provider = LearningMentorContextProvider(
            create_autospec(object),  # pyright: ignore[reportArgumentType] - unused here.
            create_autospec(object),  # pyright: ignore[reportArgumentType] - unused here.
            create_autospec(object),  # pyright: ignore[reportArgumentType] - unused here.
            activity,
        )
        return provider, activity

    def _facts(
        self,
        provider: LearningMentorContextProvider,
        *,
        status: SkillExperienceStatus = SkillExperienceStatus.LEARNING,
        allowed: tuple[str, ...] = ('activity',),
    ) -> tuple[tuple[str, str], ...]:
        return provider.current_activity_question_facts(
            'account', 'goal', 'skill', status, 'competency', 'activity', allowed
        )

    def test_should_add_the_questions_of_a_released_learning_activity(self) -> None:
        provider, activity = self._provider()

        assert len(self._facts(provider)) == 3
        activity.execute.assert_called_once_with(  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType] - autospec mock.
            'account', 'goal', 'skill', 'competency', 'activity'
        )

    def test_should_hide_diagnostic_and_unreleased_activities(self) -> None:
        provider, activity = self._provider()

        assert self._facts(provider, status=SkillExperienceStatus.DIAGNOSING) == ()
        assert self._facts(provider, allowed=()) == ()
        activity.execute.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType] - autospec mock.
        activity.execute.return_value = _detail(is_diagnostic=True)  # pyright: ignore[reportAttributeAccessIssue] - autospec mock.
        assert self._facts(provider) == ()
        activity.execute.side_effect = NotFoundError  # pyright: ignore[reportAttributeAccessIssue] - autospec mock.
        assert self._facts(provider) == ()
