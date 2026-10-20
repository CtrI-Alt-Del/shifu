from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.learning.core.domain.enums import (
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import (
    CurriculumGapError,
    GoalConfirmationConflictError,
    InvalidGoalError,
)
from shifu.learning.core.domain.structures import GoalConfirmation
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.create_planned_goal_use_case import (
    CreatePlannedGoalUseCase,
)
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
    PlannedGoalConfirmation,
    PlannedGoalSkill,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)
ACCOUNT_ID = '01JACCOUNT000000000000TEST'
PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
CONFIRMATION_KEY = '3f0c2b9e-8d1a-4c57-9b2e-6a1d4f8c0e21'


def catalog(skill_id: str, *, gaps: tuple[str, ...] = ()) -> CurriculumSkillSnapshot:
    concept = CurriculumConceptSnapshot(
        id=f'{skill_id}-concept',
        competency_id=f'{skill_id}-competency',
        name='Conceito',
        position=1,
        prerequisite_ids=(),
        observation_criteria='Critério',
    )
    activity = CurriculumActivitySnapshot(
        id=f'{skill_id}-diagnostic',
        title='Diagnóstico',
        activity_type='diagnostic',
        difficulty='easy',
        position=1,
        concept_ids=(concept.id,),
        question_count_by_concept=((concept.id, 1),),
        maximum_evidence_by_concept=((concept.id, 1),),
        executable_concept_evidence=True,
    )
    return CurriculumSkillSnapshot(
        id=skill_id,
        name=f'Skill {skill_id}',
        v2_coverage_gaps=gaps,
        competencies=(
            CurriculumCompetencySnapshot(
                id=f'{skill_id}-competency',
                skill_id=skill_id,
                name='Competência',
                position=1,
                items=(),
                concepts=(concept,),
                diagnostic_activities=(activity,),
            ),
        ),
    )


def confirmation(
    *,
    title: str = '  Automatizar tarefas com Python ',
    description: str = 'Scripts que resolvem planilhas por mim. ',
    skills: tuple[PlannedGoalSkill, ...] | None = None,
) -> PlannedGoalConfirmation:
    return PlannedGoalConfirmation(
        account_id=ACCOUNT_ID,
        confirmation_key=CONFIRMATION_KEY,
        planning_id=PLANNING_ID,
        title=title,
        description=description,
        skills=skills
        if skills is not None
        else (
            PlannedGoalSkill(skill_id='logic', inclusion_reason=' Base da automação. '),
            PlannedGoalSkill(
                skill_id='python', inclusion_reason='Linguagem dos scripts.'
            ),
        ),
    )


def _python_with_gap(skill_id: str) -> CurriculumSkillSnapshot:
    return catalog(skill_id, gaps=('coverage-gap',) if skill_id == 'python' else ())


class _Setup:
    def __init__(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.repositories.goal_confirmations.find.return_value = None
        self.curriculum = create_autospec(CurriculumContentProvider, instance=True)
        self.curriculum.get_skill_content.side_effect = catalog
        clock = create_autospec(ClockProvider, instance=True)
        clock.now.return_value = NOW
        identifiers = create_autospec(IdentifierProvider, instance=True)
        identifiers.generate.side_effect = (f'id-{index}' for index in range(1, 100))
        self.subject = CreatePlannedGoalUseCase(
            self.database, self.curriculum, clock, identifiers
        )


class TestCreatePlannedGoalUseCase:
    def test_should_create_the_goal_with_every_skill_and_its_justification_once(
        self,
    ) -> None:
        setup = _Setup()

        creation = setup.subject.execute(confirmation())

        assert creation.goal_id == 'id-1'
        assert creation.confirmation_key == CONFIRMATION_KEY
        assert creation.replayed is False
        setup.repositories.goal_confirmations.lock.assert_called_once_with(
            ACCOUNT_ID, CONFIRMATION_KEY
        )
        goal = setup.repositories.goals.add_many.call_args.args[0][0]
        assert goal.title == 'Automatizar tarefas com Python'
        assert goal.description == 'Scripts que resolvem planilhas por mim.'
        assert goal.account_id == ACCOUNT_ID
        experiences = [
            call.args[0][0]
            for call in setup.repositories.skill_experiences.add_many.call_args_list
        ]
        assert [(e.skill_id, e.inclusion_reason, e.status) for e in experiences] == [
            ('logic', 'Base da automação.', SkillExperienceStatus.NOT_STARTED),
            ('python', 'Linguagem dos scripts.', SkillExperienceStatus.NOT_STARTED),
        ]
        assert all(e.goal_id == 'id-1' for e in experiences)
        progresses = [
            call.args[0]
            for call in setup.repositories.competency_progresses.add_many.call_args_list
        ]
        assert [len(batch) for batch in progresses] == [1, 1]
        assert progresses[0][0].status is CompetencyProgressStatus.LEARNING
        assert progresses[0][0].content_released is False
        stored = setup.repositories.goal_confirmations.add.call_args.args[0]
        assert isinstance(stored, GoalConfirmation)
        assert (stored.goal_id, stored.planning_id, stored.created_at) == (
            'id-1',
            PLANNING_ID,
            NOW,
        )
        # Everything happens inside the single Learning transaction.
        assert setup.database.transaction.call_count == 1

    def test_should_return_the_same_goal_for_a_repeated_confirmation(self) -> None:
        setup = _Setup()
        first = setup.subject.execute(confirmation())
        stored = setup.repositories.goal_confirmations.add.call_args.args[0]
        setup.repositories.goal_confirmations.find.return_value = stored

        replay = setup.subject.execute(confirmation())

        assert replay.goal_id == first.goal_id
        assert replay.replayed is True
        assert setup.repositories.goals.add_many.call_count == 1
        assert setup.repositories.skill_experiences.add_many.call_count == 2
        assert setup.repositories.goal_confirmations.add.call_count == 1

    def test_should_refuse_a_repeated_key_with_another_content(self) -> None:
        setup = _Setup()
        setup.subject.execute(confirmation())
        stored = setup.repositories.goal_confirmations.add.call_args.args[0]
        setup.repositories.goal_confirmations.find.return_value = stored

        with pytest.raises(GoalConfirmationConflictError):
            setup.subject.execute(confirmation(title='Outro título'))

        assert setup.repositories.goals.add_many.call_count == 1

    @pytest.mark.parametrize(
        'invalid',
        [
            confirmation(title='   '),
            confirmation(description=''),
            confirmation(title='x' * 241),
            confirmation(skills=()),
            confirmation(
                skills=(
                    PlannedGoalSkill(skill_id='logic', inclusion_reason='Base.'),
                    PlannedGoalSkill(skill_id='logic', inclusion_reason='Outra.'),
                )
            ),
            confirmation(
                skills=(PlannedGoalSkill(skill_id='logic', inclusion_reason='  '),)
            ),
        ],
        ids=[
            'blank-title',
            'blank-description',
            'long-title',
            'no-skills',
            'duplicated-skill',
            'blank-justification',
        ],
    )
    def test_should_reject_an_incomplete_confirmation_before_writing(
        self, invalid: PlannedGoalConfirmation
    ) -> None:
        setup = _Setup()

        with pytest.raises(InvalidGoalError):
            setup.subject.execute(invalid)

        setup.database.transaction.assert_not_called()

    def test_should_refuse_a_skill_the_curriculum_cannot_start_without_partial_rows(
        self,
    ) -> None:
        setup = _Setup()
        setup.curriculum.get_skill_content.side_effect = _python_with_gap

        with pytest.raises(CurriculumGapError):
            setup.subject.execute(confirmation())

        setup.repositories.goals.add_many.assert_not_called()
        setup.repositories.skill_experiences.add_many.assert_not_called()
        setup.repositories.goal_confirmations.add.assert_not_called()

    def test_should_refuse_an_unknown_skill(self) -> None:
        setup = _Setup()
        setup.curriculum.get_skill_content.side_effect = None
        setup.curriculum.get_skill_content.return_value = None

        with pytest.raises(CurriculumGapError):
            setup.subject.execute(confirmation())

        setup.repositories.goals.add_many.assert_not_called()
