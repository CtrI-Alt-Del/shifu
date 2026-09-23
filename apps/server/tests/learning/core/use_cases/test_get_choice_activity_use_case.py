from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import CompetencyProgress
from shifu.learning.core.domain.structures import ChoiceActivityDetail
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetChoiceActivityUseCase
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
COMPETENCY_ID = 'competency-1'
EXPERIENCE_ID = 'experience-1'
ACTIVITY_ID = 'activity-1'


def snapshot(
    *, explanation: str = 'Feedback privado'
) -> CurriculumChoiceActivitySnapshot:
    questions = tuple(
        CurriculumChoiceQuestionSnapshot(
            key=f'q{index}',
            kind='single_choice' if index == 1 else 'multiple_selection',
            prompt=f'Pergunta {index}?',
            options=(
                CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
                CurriculumChoiceOptionSnapshot(key='b', text='B', is_correct=False),
                *(
                    (
                        CurriculumChoiceOptionSnapshot(
                            key='c', text='C', is_correct=True
                        ),
                    )
                    if index > 1
                    else ()
                ),
            ),
            correct_explanation=explanation,
            incorrect_explanation='Feedback de revisão',
        )
        for index in range(1, 4)
    )
    return CurriculumChoiceActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Atividade',
        questions=questions,
        parts=tuple(
            CurriculumChoicePartSnapshot(
                question_key=f'q{index}',
                weight_percentage=Decimal(weight),
            )
            for index, weight in enumerate(('34', '33', '33'), 1)
        ),
    )


class TestGetChoiceActivityUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID, goal_id=GOAL_ID, skill_id=SKILL_ID
        )
        self.progress = CompetencyProgress(
            id='progress-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
            created_at=SkillExperienceFaker.fake().created_at,
            updated_at=SkillExperienceFaker.fake().updated_at,
            initial_progress=Decimal('0'),
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = self.progress
        self.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
        self.repositories.activity_attempts.find_many_by_skill_experience_id_and_activity_id.return_value = []
        self.provider.get_choice_activity.return_value = snapshot()
        self.subject = GetChoiceActivityUseCase(self.database, self.provider)

    def test_should_return_only_safe_ordered_question_projection(self) -> None:
        detail = self.subject.execute(
            ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
        )

        assert isinstance(detail, ChoiceActivityDetail)
        assert tuple(question.key for question in detail.questions) == (
            'q1',
            'q2',
            'q3',
        )
        assert tuple(option.key for option in detail.questions[0].options) == ('a', 'b')
        assert detail.can_submit is True
        assert not hasattr(detail.questions[0].options[0], 'is_correct')
        assert not hasattr(detail.questions[0], 'correct_explanation')

    def test_should_not_read_curriculum_for_private_absence(self) -> None:
        self.repositories.goals.find_by_id.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )

        self.provider.get_choice_activity.assert_not_called()

    def test_should_reject_unreleased_competency_and_incomplete_snapshot(self) -> None:
        self.progress.content_released = False
        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )
        self.provider.get_choice_activity.assert_not_called()

        self.progress.content_released = True
        self.provider.get_choice_activity.return_value = None
        with pytest.raises(NotFoundError):
            self.subject.execute(
                ACCOUNT_ID, GOAL_ID, SKILL_ID, COMPETENCY_ID, ACTIVITY_ID
            )
