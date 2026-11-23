from collections.abc import Iterator
from typing import TYPE_CHECKING, ClassVar, cast

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from tests.fixtures.postgres_fixture import PostgresDatabase

if TYPE_CHECKING:
    from httpx import Response

_IDS = IdProviderFaker()
OWNER_ACCOUNT_ID = _IDS.generate()
OTHER_ACCOUNT_ID = _IDS.generate()
OWNER_HEADERS = {'Authorization': 'Bearer owner-token'}
OTHER_HEADERS = {'Authorization': 'Bearer other-token'}


class _Authentication:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        accounts = {
            'owner-token': OWNER_ACCOUNT_ID,
            'other-token': OTHER_ACCOUNT_ID,
        }
        account_id = accounts.get(access_token)
        if account_id is None:
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=account_id,
            display_name='Pessoa Aprendente',
            time_zone=None,
            session_id=f'learning-skill-experiences-{access_token}',
            token_access_version=1,
            account_access_version=1,
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


def _path(skill_id: str) -> str:
    return f'/learning/skills/{skill_id}/experiences'


class TestListSkillExperiencesOfSkillController:
    skill_id: ClassVar[str] = _IDS.generate()

    @pytest.fixture(autouse=True)
    def _setup(self, postgres_database: PostgresDatabase) -> Iterator[None]:
        with SqlalchemyIdentityDatabase(
            postgres_database.engine
        ).transaction() as repos:
            for account_id in (OWNER_ACCOUNT_ID, OTHER_ACCOUNT_ID):
                if repos.accounts.find_by_id(account_id) is None:
                    repos.accounts.add(
                        AccountFaker.fake(id=account_id, access_version=1)
                    )
        self.database = SqlalchemyLearningDatabase(postgres_database.engine)
        app = FastAPIApp.register(postgres_database.engine)
        app.state.authentication_provider = _Authentication()
        app.state.inngest_broker = _NoopBroker()
        with TestClient(app, raise_server_exceptions=False) as client:
            self.client = client
            yield

    def _get(
        self, skill_id: str, headers: dict[str, str] | None = OWNER_HEADERS
    ) -> 'Response':
        return cast(
            'Response',
            self.client.get(  # pyright: ignore[reportUnknownMemberType]
                _path(skill_id),
                headers=headers,
            ),
        )

    def _seed(
        self,
        account_id: str,
        title: str,
        status: SkillExperienceStatus,
        *,
        skill_id: str | None = None,
    ) -> tuple[str, str]:
        goal = GoalFaker.fake(account_id=account_id, title=title)
        experience = SkillExperienceFaker.fake(
            goal_id=goal.id, skill_id=skill_id or self.skill_id, status=status
        )
        with self.database.transaction() as repositories:
            repositories.goals.add(goal)
            repositories.skill_experiences.add(experience)
        return goal.id, experience.id

    def test_should_return_only_the_own_experiences_of_the_skill_ordered_by_goal_title(
        self,
    ) -> None:
        data_goal_id, data_experience_id = self._seed(
            OWNER_ACCOUNT_ID, 'Carreira em dados', SkillExperienceStatus.COMPLETED
        )
        backend_goal_id, backend_experience_id = self._seed(
            OWNER_ACCOUNT_ID, 'Backend', SkillExperienceStatus.LEARNING
        )
        self._seed(
            OTHER_ACCOUNT_ID, 'Aaa de outra conta', SkillExperienceStatus.LEARNING
        )
        self._seed(
            OWNER_ACCOUNT_ID,
            'Outra Habilidade',
            SkillExperienceStatus.NOT_STARTED,
            skill_id=_IDS.generate(),
        )

        response = self._get(self.skill_id)

        assert response.status_code == 200, response.text
        assert response.json() == {
            'experiences': [
                {
                    'goalId': backend_goal_id,
                    'goalTitle': 'Backend',
                    'skillExperienceId': backend_experience_id,
                    'skillId': self.skill_id,
                    'status': 'learning',
                },
                {
                    'goalId': data_goal_id,
                    'goalTitle': 'Carreira em dados',
                    'skillExperienceId': data_experience_id,
                    'skillId': self.skill_id,
                    'status': 'completed',
                },
            ]
        }

    def test_should_exclude_the_experiences_of_a_second_account(self) -> None:
        self._seed(OWNER_ACCOUNT_ID, 'Meu Objetivo', SkillExperienceStatus.COMPLETED)
        other_goal_id, other_experience_id = self._seed(
            OTHER_ACCOUNT_ID, 'Objetivo da outra conta', SkillExperienceStatus.LEARNING
        )

        response = self._get(self.skill_id, OTHER_HEADERS)

        assert response.status_code == 200, response.text
        assert [
            (item['goalId'], item['skillExperienceId'])
            for item in response.json()['experiences']
        ] == [(other_goal_id, other_experience_id)]

    def test_should_order_goals_with_the_same_title_by_goal_id(self) -> None:
        first_goal_id, _ = self._seed(
            OWNER_ACCOUNT_ID, 'Carreira', SkillExperienceStatus.LEARNING
        )
        second_goal_id, _ = self._seed(
            OWNER_ACCOUNT_ID, 'Carreira', SkillExperienceStatus.NOT_STARTED
        )

        response = self._get(self.skill_id)

        assert response.status_code == 200, response.text
        assert [item['goalId'] for item in response.json()['experiences']] == sorted(
            [first_goal_id, second_goal_id]
        )

    def test_should_return_an_empty_list_for_an_unknown_skill(self) -> None:
        self._seed(OWNER_ACCOUNT_ID, 'Meu Objetivo', SkillExperienceStatus.COMPLETED)

        response = self._get(_IDS.generate())

        assert response.status_code == 200, response.text
        assert response.json() == {'experiences': []}

    def test_should_return_an_empty_list_for_an_account_without_goals(self) -> None:
        response = self._get(self.skill_id)

        assert response.status_code == 200, response.text
        assert response.json() == {'experiences': []}

    @pytest.mark.parametrize(
        'headers',
        [None, {'Authorization': 'Bearer invalid-token'}],
    )
    def test_should_return_401_without_data_when_unauthenticated(
        self, headers: dict[str, str] | None
    ) -> None:
        self._seed(OWNER_ACCOUNT_ID, 'Meu Objetivo', SkillExperienceStatus.COMPLETED)

        response = self._get(self.skill_id, headers)

        assert response.status_code == 401, response.text
        assert 'experiences' not in response.json()

    def test_should_return_a_localized_422_for_a_skill_id_that_is_not_a_ulid(
        self,
    ) -> None:
        response = self._get('not-a-ulid')

        assert response.status_code == 422, response.text
        assert response.json() == {
            'code': 'validation_error',
            'message': 'Os dados enviados são inválidos.',
        }
