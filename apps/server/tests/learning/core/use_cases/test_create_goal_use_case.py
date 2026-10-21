from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.create_goal_use_case import CreateGoalUseCase
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def catalog(*, gaps: tuple[str, ...] = ()) -> CurriculumSkillSnapshot:
    concept = CurriculumConceptSnapshot(
        id='concept',
        competency_id='competency',
        name='Conceito',
        position=1,
        prerequisite_ids=(),
        observation_criteria='Critério',
    )
    activity = CurriculumActivitySnapshot(
        id='diagnostic-easy',
        title='Diagnóstico',
        activity_type='diagnostic',
        difficulty='easy',
        position=1,
        concept_ids=('concept',),
        question_count_by_concept=(('concept', 1),),
        maximum_evidence_by_concept=(('concept', 1),),
        executable_concept_evidence=True,
    )
    return CurriculumSkillSnapshot(
        id='skill',
        name='Skill',
        v2_coverage_gaps=gaps,
        competencies=(
            CurriculumCompetencySnapshot(
                id='competency',
                skill_id='skill',
                name='Competência',
                position=1,
                items=(),
                concepts=(concept,),
                diagnostic_activities=(activity,),
            ),
        ),
    )


class TestCreateGoalUseCase:
    def test_should_pin_v2_policy_only_for_an_eligible_catalog(self) -> None:
        database = create_autospec(LearningDatabase, instance=True)
        repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        database.transaction.return_value.__enter__.return_value = repositories
        curriculum = create_autospec(CurriculumContentProvider, instance=True)
        curriculum.get_skill_content.return_value = catalog()
        clock = create_autospec(ClockProvider, instance=True)
        clock.now.return_value = NOW
        identifiers = create_autospec(IdentifierProvider, instance=True)
        identifiers.generate.side_effect = (
            'goal-new',
            'experience-new',
            'progress-new',
        )
        subject = CreateGoalUseCase(database, curriculum, clock, identifiers)

        goal = subject.execute('account', 'Meta', 'Descrição', ('skill',))

        assert goal.id == 'goal-new'
        experience = repositories.skill_experiences.add_many.call_args.args[0][0]

        assert experience.status is SkillExperienceStatus.NOT_STARTED
        assert (
            repositories.competency_progresses.add_many.call_args.args[0][
                0
            ].initial_progress
            is None
        )

        curriculum.get_skill_content.return_value = catalog(gaps=('coverage-gap',))
        with pytest.raises(CurriculumGapError):
            subject.execute('account', 'Meta', 'Descrição', ('skill',))

        assert repositories.goals.add_many.call_count == 1
