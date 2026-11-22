from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.errors import GoalNotFoundError
from shifu.learning.core.domain.events import PracticePhotoCleanupRequestedEvent
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import RemoveGoalUseCase
from tests.learning.core.use_cases.practice_draft_use_case_setup import fake_photo

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'


class TestRemoveGoalUseCase:
    def setup_method(self) -> None:
        self.learning_database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.learning_database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.goals_repository = self.repositories.goals
        self.subject = RemoveGoalUseCase(self.learning_database)

    def test_should_remove_goal_when_owned_by_account(self) -> None:
        goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.goals_repository.find_by_id.return_value = goal

        self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        self.goals_repository.remove.assert_called_once_with(goal)

    def test_should_request_cleanup_for_every_practice_photo_before_removing_the_goal(
        self,
    ) -> None:
        goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        experience = SkillExperienceFaker.fake(goal_id=GOAL_ID)
        self.goals_repository.find_by_id.return_value = goal
        self.repositories.skill_experiences.find_many_by_goal_id.return_value = [
            experience
        ]
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            experience
        )
        self.repositories.practice_photos.list_for_skill_experience.return_value = (
            fake_photo(),
            fake_photo(photo_id='photo-2'),
        )
        order: list[str] = []

        def record_event(event: object) -> None:
            assert isinstance(event, PracticePhotoCleanupRequestedEvent)
            order.append(f'event:{event.payload.photo_id}')

        def record_remove(_goal: object) -> None:
            order.append('remove')

        self.repositories.events.add.side_effect = record_event
        self.goals_repository.remove.side_effect = record_remove

        self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        assert order == ['event:photo-1', 'event:photo-2', 'remove']
        event = self.repositories.events.add.call_args.args[0]
        assert isinstance(event, PracticePhotoCleanupRequestedEvent)

    def test_should_raise_goal_not_found_error_when_goal_missing(self) -> None:
        self.goals_repository.find_by_id.return_value = None

        with pytest.raises(GoalNotFoundError):
            self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        self.goals_repository.remove.assert_not_called()

    def test_should_raise_goal_not_found_error_when_goal_belongs_to_another_account(
        self,
    ) -> None:
        goal = GoalFaker.fake(id=GOAL_ID, account_id='other-account')
        self.goals_repository.find_by_id.return_value = goal

        with pytest.raises(GoalNotFoundError):
            self.subject.execute(account_id=ACCOUNT_ID, goal_id=GOAL_ID)

        self.goals_repository.remove.assert_not_called()
