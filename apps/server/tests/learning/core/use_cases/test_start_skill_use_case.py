from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.start_skill_use_case import StartSkillUseCase
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumCompetencySnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def catalog(*, gaps: tuple[str, ...] = ()) -> CurriculumSkillSnapshot:
    return CurriculumSkillSnapshot(
        id='skill',
        name='Skill',
        competencies=(
            CurriculumCompetencySnapshot(
                id='competency',
                skill_id='skill',
                name='Competência',
                position=1,
                items=(),
            ),
        ),
        v2_coverage_gaps=gaps,
    )


class TestStartSkillUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.curriculum = create_autospec(CurriculumContentProvider, instance=True)
        self.curriculum.get_skill_content.return_value = catalog()
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.goal = GoalFaker.fake(id='goal', account_id='account')
        self.experience = SkillExperienceFaker.fake(
            id='experience',
            goal_id='goal',
            skill_id='skill',
            status=SkillExperienceStatus.NOT_STARTED,
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.subject = StartSkillUseCase(self.database, self.curriculum, self.clock)

    def execute(self, entry_key: str = 'entry-1') -> SkillExperience:
        return self.subject.execute('account', 'goal', 'skill', entry_key)

    def test_should_start_with_entry_key_and_keep_started_at_on_replay(self) -> None:
        started = self.execute()

        assert started.status is SkillExperienceStatus.DIAGNOSING
        assert started.diagnostic_run_id == 'entry-1'
        assert started.started_at == NOW
        self.repositories.skill_experiences.update.assert_called_once_with(started)

        replay = self.execute()

        assert replay is started
        self.repositories.activity_attempts.remove_diagnostic_by_experience.assert_not_called()
        self.repositories.skill_experiences.update.assert_called_once()

    def test_should_replace_prior_run_and_discard_its_diagnostic_attempts(self) -> None:
        self.experience.status = SkillExperienceStatus.DIAGNOSING
        self.experience.started_at = NOW
        self.experience.diagnostic_run_id = 'old-entry'

        started = self.execute('new-entry')

        assert started.diagnostic_run_id == 'new-entry'
        assert started.started_at == NOW
        self.repositories.activity_attempts.remove_diagnostic_by_experience.assert_called_once_with(
            'experience'
        )
        self.repositories.skill_experiences.update.assert_called_once_with(started)

    def test_should_reject_ineligible_catalog_without_mutating_experience(self) -> None:
        self.curriculum.get_skill_content.return_value = catalog(
            gaps=('missing-level',)
        )

        with pytest.raises(CurriculumGapError):
            self.execute()

        self.repositories.skill_experiences.update.assert_not_called()
        self.repositories.activity_attempts.remove_diagnostic_by_experience.assert_not_called()

    def test_should_hide_experience_owned_by_another_account(self) -> None:
        self.repositories.goals.find_by_id.return_value.account_id = 'another-account'

        with pytest.raises(NotFoundError):
            self.execute()

        self.curriculum.get_skill_content.assert_not_called()
        self.repositories.skill_experiences.update.assert_not_called()

    def test_should_reject_entry_after_learning_has_started(self) -> None:
        self.experience.status = SkillExperienceStatus.LEARNING

        with pytest.raises(ConflictError):
            self.execute('new-entry')

        self.repositories.activity_attempts.remove_diagnostic_by_experience.assert_not_called()
        self.repositories.skill_experiences.update.assert_not_called()
