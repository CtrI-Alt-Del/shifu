from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.abandon_diagnostic_use_case import (
    AbandonDiagnosticUseCase,
)
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from shifu.shared.core.interfaces import ClockProvider

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


class TestAbandonDiagnosticUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.goal = GoalFaker.fake(id='goal', account_id='account')
        self.experience = SkillExperienceFaker.fake(
            id='experience',
            goal_id='goal',
            skill_id='skill',
            status=SkillExperienceStatus.DIAGNOSING,
        )
        self.experience.diagnostic_run_id = 'active-run'
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = self.experience
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.subject = AbandonDiagnosticUseCase(self.database, self.clock)

    def execute(self, account_id: str = 'account', run_id: str = 'active-run') -> None:
        self.subject.execute(account_id, 'goal', 'skill', run_id)

    def test_should_abandon_only_the_current_run(self) -> None:
        self.execute()

        assert self.experience.status is SkillExperienceStatus.NOT_STARTED
        assert self.experience.diagnostic_run_id is None
        assert self.experience.updated_at == NOW
        self.repositories.activity_attempts.remove_diagnostic_by_experience.assert_called_once_with(
            'experience'
        )
        self.repositories.skill_experiences.update.assert_called_once_with(
            self.experience
        )

    def test_should_not_touch_experience_when_run_key_is_stale(self) -> None:
        with pytest.raises(ConflictError):
            self.execute(run_id='stale-run')

        self.repositories.activity_attempts.remove_diagnostic_by_experience.assert_not_called()
        self.repositories.skill_experiences.update.assert_not_called()

    def test_should_hide_an_experience_from_another_account(self) -> None:
        with pytest.raises(NotFoundError):
            self.execute(account_id='other-account')

        self.repositories.skill_experiences.find_by_id_for_update.assert_not_called()
