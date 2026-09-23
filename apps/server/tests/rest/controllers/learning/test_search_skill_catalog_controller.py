from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.core.domain.structures import SkillFoundation
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.fakers.curriculum.entities.skill_faker import SkillFaker
from shifu.fakers.learning.entities import GoalFaker
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response


class TestSearchSkillCatalogController:
    def test_missing_bearer_token_returns_safe_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        response = cast(
            'Response',
            client.get(  # pyright: ignore[reportUnknownMemberType]
                '/learning/goals/some-goal/skills/catalog'
            ),
        )

        assert response.status_code == 401
        assert response.json()['detail']['code'] == 'unauthorized'

    def test_returns_not_found_for_a_foreign_goal(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id='another-account',
                display_name='Outra Pessoa',
                time_zone=None,
            )
        )

        with TestClient(app) as client:
            response = cast(
                'Response',
                client.get(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/catalog',
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 404
        assert response.json()['code'] == 'not_found'

    def test_returns_catalog_skills_with_foundations_and_already_in_goal_status(
        self,
        postgres_database: PostgresDatabase,
    ) -> None:
        goal = GoalFaker.fake()
        foundation_skill = SkillFaker.fake(name='JavaScript')
        catalog_skill = SkillFaker.fake(name='React')

        curriculum_database = SqlalchemyCurriculumDatabase(
            engine=postgres_database.engine
        )
        with curriculum_database.transaction() as repositories:
            repositories.skills.add_many([foundation_skill, catalog_skill])
            repositories.skill_foundations.add_many(
                [
                    SkillFoundation(
                        skill_id=catalog_skill.id,
                        foundation_skill_id=foundation_skill.id,
                    )
                ]
            )

        learning_database = SqlalchemyLearningDatabase(engine=postgres_database.engine)
        with learning_database.transaction() as repositories:
            repositories.goals.add(goal)

        app = FastAPIApp.register(postgres_database.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=goal.account_id,
                display_name='Pessoa Aprendente',
                time_zone=None,
            )
        )

        with TestClient(app) as client:
            response = cast(
                'Response',
                client.get(  # pyright: ignore[reportUnknownMemberType]
                    f'/learning/goals/{goal.id}/skills/catalog',
                    params={'query': 'React'},
                    headers={'Authorization': 'Bearer test-token'},
                ),
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body['items']) == 1
        item = body['items'][0]
        assert item['id'] == catalog_skill.id
        assert item['name'] == 'React'
        assert item['alreadyInGoal'] is False
        assert item['skillExperienceId'] is None
        assert item['foundations'] == [
            {
                'skillId': foundation_skill.id,
                'name': 'JavaScript',
                'status': 'missing',
            }
        ]
