from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from shifu.app import FastAPIApp
from shifu.fakers.learning.entities import GoalFaker
from shifu.fakers.learning.entities.activity_attempt_faker import ActivityAttemptFaker
from shifu.fakers.learning.entities.activity_evaluation_faker import (
    ActivityEvaluationFaker,
)
from shifu.fakers.learning.entities.competency_progress_faker import (
    CompetencyProgressFaker,
)
from shifu.fakers.learning.entities.skill_experience_faker import SkillExperienceFaker
from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response

ACCESS_TOKEN_HEADERS = {'Authorization': 'Bearer test-token'}


def _authenticated_client(engine: Engine, account_id: str) -> TestClient:
    app = FastAPIApp.register(engine)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
        AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Aprendente',
            time_zone=None,
        )
    )
    return TestClient(app)


class TestRemoveGoalController:
    def test_should_remove_goal_when_owned_by_account(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        skill_experience = SkillExperienceFaker.fake(goal_id=goal.id)
        competency_progress = CompetencyProgressFaker.fake(
            skill_experience_id=skill_experience.id
        )
        attempt = ActivityAttemptFaker.fake(skill_experience_id=skill_experience.id)
        evaluation = ActivityEvaluationFaker.fake(attempt_id=attempt.id)

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add_many([goal])
            repositories.skill_experiences.add_many([skill_experience])
            repositories.competency_progresses.add_many([competency_progress])
            repositories.activity_attempts.add_many([attempt])
            repositories.activity_evaluations.add_many([evaluation])

        with _authenticated_client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}',
                    headers=ACCESS_TOKEN_HEADERS,
                ),
            )

        assert response.status_code == 204
        assert response.text == ''

        with learning_database.transaction() as repositories:
            assert repositories.goals.find_by_id(goal.id) is None
            assert repositories.skill_experiences.find_many_by_goal_id(goal.id) == []
            assert (
                repositories.competency_progresses.find_many_by_skill_experience_id(
                    skill_experience.id
                )
                == []
            )
            assert (
                repositories.activity_attempts.find_many_by_skill_experience_id(
                    skill_experience.id
                )
                == []
            )
            assert (
                repositories.activity_evaluations.find_by_attempt_id(attempt.id) is None
            )

    def test_should_return_404_and_preserve_goal_when_requested_by_another_account(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        skill_experience = SkillExperienceFaker.fake(goal_id=goal.id)

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add(skill_experience)

        with _authenticated_client(
            postgres_database.engine, 'another-account'
        ) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}',
                    headers=ACCESS_TOKEN_HEADERS,
                ),
            )

        assert response.status_code == 404

        with learning_database.transaction() as repositories:
            preserved_goal = repositories.goals.find_by_id(goal.id)
            assert preserved_goal is not None
            assert preserved_goal.account_id == goal.account_id
            preserved_experiences = repositories.skill_experiences.find_many_by_goal_id(
                goal.id
            )
            assert [experience.id for experience in preserved_experiences] == [
                skill_experience.id
            ]

    def test_should_return_404_when_goal_does_not_exist(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        with _authenticated_client(postgres_database.engine, 'some-account') as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    '/learning/goals/nonexistent-id',
                    headers=ACCESS_TOKEN_HEADERS,
                ),
            )

        assert response.status_code == 404

    def test_should_return_401_when_unauthenticated(
        self,
        postgres_database: PostgresDatabase,
        client: TestClient,
    ) -> None:
        goal = GoalFaker.fake()
        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        response = cast(
            'Response',
            client.delete(  # pyright: ignore[reportUnknownMemberType]
                f'/learning/goals/{goal.id}'
            ),
        )

        assert response.status_code == 401

        with learning_database.transaction() as repositories:
            assert repositories.goals.find_by_id(goal.id) is not None

    def test_should_cascade_remove_every_skill_experience_and_learning_data_regardless_of_status(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        statuses = [
            SkillExperienceStatus.NOT_STARTED,
            SkillExperienceStatus.DIAGNOSING,
            SkillExperienceStatus.LEARNING,
            SkillExperienceStatus.COMPLETED,
        ]
        skill_experiences = [
            SkillExperienceFaker.fake(goal_id=goal.id, status=status)
            for status in statuses
        ]
        competency_progresses = [
            CompetencyProgressFaker.fake(skill_experience_id=experience.id)
            for experience in skill_experiences
        ]
        attempts = [
            ActivityAttemptFaker.fake(skill_experience_id=experience.id)
            for experience in skill_experiences
        ]
        evaluations = [
            ActivityEvaluationFaker.fake(attempt_id=attempt.id) for attempt in attempts
        ]

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add_many(skill_experiences)
            repositories.competency_progresses.add_many(competency_progresses)
            repositories.activity_attempts.add_many(attempts)
            repositories.activity_evaluations.add_many(evaluations)

        with _authenticated_client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}',
                    headers=ACCESS_TOKEN_HEADERS,
                ),
            )

        assert response.status_code == 204

        with learning_database.transaction() as repositories:
            assert repositories.skill_experiences.find_many_by_goal_id(goal.id) == []
            for experience in skill_experiences:
                assert (
                    repositories.competency_progresses.find_many_by_skill_experience_id(
                        experience.id
                    )
                    == []
                )
                assert (
                    repositories.activity_attempts.find_many_by_skill_experience_id(
                        experience.id
                    )
                    == []
                )
            for attempt in attempts:
                assert (
                    repositories.activity_evaluations.find_by_attempt_id(attempt.id)
                    is None
                )

    def test_should_remove_goal_with_pending_or_failed_evaluation(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        skill_experience = SkillExperienceFaker.fake(goal_id=goal.id)
        pending_attempt = ActivityAttemptFaker.fake(
            skill_experience_id=skill_experience.id
        )
        failed_attempt = ActivityAttemptFaker.fake(
            skill_experience_id=skill_experience.id
        )
        pending_evaluation = ActivityEvaluationFaker.fake(
            attempt_id=pending_attempt.id,
            status=ActivityEvaluationStatus.PENDING,
        )
        failed_evaluation = ActivityEvaluationFaker.fake(
            attempt_id=failed_attempt.id,
            status=ActivityEvaluationStatus.FAILED,
        )

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add_many([goal])
            repositories.skill_experiences.add_many([skill_experience])
            repositories.activity_attempts.add_many([pending_attempt, failed_attempt])
            repositories.activity_evaluations.add_many(
                [pending_evaluation, failed_evaluation]
            )

        with _authenticated_client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}',
                    headers=ACCESS_TOKEN_HEADERS,
                ),
            )

        assert response.status_code == 204

        with learning_database.transaction() as repositories:
            assert (
                repositories.activity_evaluations.find_by_attempt_id(pending_attempt.id)
                is None
            )
            assert (
                repositories.activity_evaluations.find_by_attempt_id(failed_attempt.id)
                is None
            )

    def test_should_leave_other_goals_of_the_same_account_untouched(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        removed_goal = GoalFaker.fake()
        preserved_goal = GoalFaker.fake(account_id=removed_goal.account_id)
        removed_experience = SkillExperienceFaker.fake(goal_id=removed_goal.id)
        preserved_experience = SkillExperienceFaker.fake(goal_id=preserved_goal.id)

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add_many([removed_goal, preserved_goal])
            repositories.skill_experiences.add_many(
                [removed_experience, preserved_experience]
            )

        with _authenticated_client(
            postgres_database.engine, removed_goal.account_id
        ) as client:
            response = cast(
                'Response',
                client.delete(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{removed_goal.id}',
                    headers=ACCESS_TOKEN_HEADERS,
                ),
            )

        assert response.status_code == 204

        with learning_database.transaction() as repositories:
            assert repositories.goals.find_by_id(removed_goal.id) is None

            still_there = repositories.goals.find_by_id(preserved_goal.id)
            assert still_there is not None
            assert still_there == preserved_goal

            preserved_experiences = repositories.skill_experiences.find_many_by_goal_id(
                preserved_goal.id
            )
            assert [experience.id for experience in preserved_experiences] == [
                preserved_experience.id
            ]
