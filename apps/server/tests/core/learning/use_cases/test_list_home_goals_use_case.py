from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker
from shifu.learning.core.domain.structures import GoalSummary
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.list_home_goals_use_case import ListHomeGoalsUseCase


class TestListHomeGoalsUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.learning_database = create_autospec(LearningDatabase, instance=True)
        self.repositories = (
            self.learning_database.transaction.return_value.__enter__.return_value
        )
        self.goals_repository = self.repositories.goals
        self.skill_experiences_repository = self.repositories.skill_experiences
        self.subject = ListHomeGoalsUseCase(self.learning_database)

    def test_should_return_summaries_ordered_as_returned_by_the_repository(
        self,
    ) -> None:
        most_recent = GoalFaker.fake(
            id='01JGOAL0000000000000000RECENT',
            account_id='01JACCOUNT000000000000000001',
            title='Aprender Python',
            description='Descrição do objetivo mais recente',
            updated_at=datetime(2026, 1, 3, tzinfo=UTC),
        )
        oldest = GoalFaker.fake(
            id='01JGOAL00000000000000000OLD1',
            account_id='01JACCOUNT000000000000000001',
            title='Aprender SQL',
            description='Descrição do objetivo mais antigo',
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        self.goals_repository.find_many_by_account_id.return_value = [
            most_recent,
            oldest,
        ]
        self.skill_experiences_repository.count_many_by_goal_ids.return_value = {
            most_recent.id: 3,
            oldest.id: 1,
        }

        result = self.subject.execute('01JACCOUNT000000000000000001')

        assert result == [
            GoalSummary(
                id=most_recent.id,
                title=most_recent.title,
                description=most_recent.description,
                skill_count=3,
                updated_at=most_recent.updated_at,
            ),
            GoalSummary(
                id=oldest.id,
                title=oldest.title,
                description=oldest.description,
                skill_count=1,
                updated_at=oldest.updated_at,
            ),
        ]
        self.goals_repository.find_many_by_account_id.assert_called_once_with(
            '01JACCOUNT000000000000000001'
        )
        self.skill_experiences_repository.count_many_by_goal_ids.assert_called_once_with(
            [most_recent.id, oldest.id]
        )
        self.learning_database.transaction.assert_called_once_with()

    def test_should_default_missing_skill_counts_to_zero(self) -> None:
        goal_with_experiences = GoalFaker.fake(id='01JGOAL0000000000000000WITH1')
        goal_without_experiences = GoalFaker.fake(id='01JGOAL0000000000000NOTHING1')
        self.goals_repository.find_many_by_account_id.return_value = [
            goal_with_experiences,
            goal_without_experiences,
        ]
        self.skill_experiences_repository.count_many_by_goal_ids.return_value = {
            goal_with_experiences.id: 5,
        }

        result = self.subject.execute(goal_with_experiences.account_id)

        assert result[0].skill_count == 5
        assert result[1].skill_count == 0

    def test_should_only_query_experiences_for_the_returned_goal_ids(self) -> None:
        account_a_goal = GoalFaker.fake(
            id='01JGOAL000000000000000ACCTA1',
            account_id='01JACCOUNTA00000000000000001',
        )
        self.goals_repository.find_many_by_account_id.return_value = [account_a_goal]
        self.skill_experiences_repository.count_many_by_goal_ids.return_value = {
            account_a_goal.id: 2,
        }

        result = self.subject.execute('01JACCOUNTA00000000000000001')

        assert len(result) == 1
        assert result[0].id == account_a_goal.id
        self.goals_repository.find_many_by_account_id.assert_called_once_with(
            '01JACCOUNTA00000000000000001'
        )

    def test_should_return_empty_list_for_account_without_goals(self) -> None:
        self.goals_repository.find_many_by_account_id.return_value = []

        result = self.subject.execute('01JACCOUNTNOGOALS0000000001')

        assert result == []
        self.skill_experiences_repository.count_many_by_goal_ids.assert_called_once_with(
            []
        )
