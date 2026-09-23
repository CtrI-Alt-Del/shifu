from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient
from sqlalchemy import Engine

from shifu.app import FastAPIApp
from shifu.curriculum.core.domain.structures import SkillFoundation
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.fakers.curriculum.entities.skill_faker import SkillFaker
from shifu.fakers.learning.entities import GoalFaker
from shifu.fakers.learning.entities.skill_experience_faker import SkillExperienceFaker
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response


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


class TestAddSkillToGoalController:
    def test_missing_bearer_token_returns_safe_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.post(  # pyright: ignore[reportUnknownMemberType]
                '/learning/goals/some-goal/skills',
                json={'skill_id': 'some-skill', 'foundation_skill_ids': []},
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_creates_a_skill_experience_and_its_selected_foundations(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        foundation_skill = SkillFaker.fake(name='JavaScript')
        skill = SkillFaker.fake(name='React')

        curriculum_database = SqlalchemyCurriculumDatabase(
            engine=postgres_database.engine
        )
        with curriculum_database.transaction() as repositories:
            repositories.skills.add_many([foundation_skill, skill])
            repositories.skill_foundations.add_many(
                [
                    SkillFoundation(
                        skill_id=skill.id,
                        foundation_skill_id=foundation_skill.id,
                    )
                ]
            )

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        with _authenticated_client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills',
                    json={
                        'skill_id': skill.id,
                        'foundation_skill_ids': [foundation_skill.id],
                    },
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 201
        body = response.json()
        created_skill_ids = {item['skillId'] for item in body['created']}
        assert created_skill_ids == {skill.id, foundation_skill.id}
        assert all(item['status'] == 'not-started' for item in body['created'])

    def test_returns_not_found_for_a_foreign_goal(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        skill = SkillFaker.fake()

        curriculum_database = SqlalchemyCurriculumDatabase(
            engine=postgres_database.engine
        )
        with curriculum_database.transaction() as repositories:
            repositories.skills.add_many([skill])

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        with _authenticated_client(
            postgres_database.engine, 'another-account'
        ) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills',
                    json={'skill_id': skill.id, 'foundation_skill_ids': []},
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 404
        assert response.json()['code'] == 'not_found'

    def test_returns_conflict_when_the_skill_was_already_added(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        skill = SkillFaker.fake()

        curriculum_database = SqlalchemyCurriculumDatabase(
            engine=postgres_database.engine
        )
        with curriculum_database.transaction() as repositories:
            repositories.skills.add_many([skill])

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add_many(
                [
                    SkillExperienceFaker.fake(
                        goal_id=goal.id,
                        skill_id=skill.id,
                        created_at=datetime.now(UTC),
                    )
                ]
            )

        with _authenticated_client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills',
                    json={'skill_id': skill.id, 'foundation_skill_ids': []},
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 409
        assert response.json()['code'] == 'conflict'

    def test_returns_bad_request_for_a_non_direct_foundation(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        skill = SkillFaker.fake()
        unrelated_skill = SkillFaker.fake()

        curriculum_database = SqlalchemyCurriculumDatabase(
            engine=postgres_database.engine
        )
        with curriculum_database.transaction() as repositories:
            repositories.skills.add_many([skill, unrelated_skill])

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        with _authenticated_client(postgres_database.engine, goal.account_id) as client:
            response = cast(
                'Response',
                client.post(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills',
                    json={
                        'skill_id': skill.id,
                        'foundation_skill_ids': [unrelated_skill.id],
                    },
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 400
        assert response.json()['code'] == 'validation_error'
