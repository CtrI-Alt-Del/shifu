from collections.abc import Iterator
from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.database.seed_data import (
    SEED_ACCOUNT_ID,
    SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
    SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
    SEED_ADAPTIVE_LAB_GOAL_ID,
    SEED_ADAPTIVE_LAB_SKILL_ID,
    build_development_seed,
)
from tests.fixtures.image_choice_activity_fixture import ImageChoiceActivityFixture
from tests.fixtures.fill_blanks_activity_fixture import (
    CORRECT_PAIRS,
    FillBlanksActivityFixture,
)
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.fixtures.redis_fixture import RedisFixture

if TYPE_CHECKING:
    from httpx import Response


_RUN_ID = '0a3c1f6e-7d2b-4a35-9c58-3f1e2d4b5a60'
_SUBMISSION_KEY = '2f7d6c1a-5b3e-4d90-8a41-6c0e9b7d3f12'


class _TestAuthenticationProvider:
    def authenticate(self, access_token: str) -> AuthenticatedUser:
        if access_token != 'test-access-token':
            raise AuthorizationError
        return AuthenticatedUser(
            account_id=SEED_ACCOUNT_ID,
            display_name='Pessoa Estudante',
            time_zone='America/Sao_Paulo',
            session_id='diagnostic-batch-test-session',
            token_access_version=1,
            account_access_version=1,
        )


class _NoopBroker:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def application(
    postgres_database: PostgresDatabase,
    redis_fixture: RedisFixture,
) -> Iterator[FastAPI]:
    seed = build_development_seed()
    with SqlalchemyIdentityDatabase(
        postgres_database.engine
    ).transaction() as repositories:
        for account in seed.accounts:
            if repositories.accounts.find_by_id(account.id) is None:
                repositories.accounts.add(account)
    with SqlalchemyCurriculumDatabase(
        postgres_database.engine
    ).transaction() as repositories:
        repositories.skills.add_many(list(seed.skills))
        repositories.skill_foundations.add_many(list(seed.skill_foundations))
        repositories.competencies.add_many(list(seed.competencies))
        repositories.concepts.add_many(list(seed.concepts))
        repositories.materials.add_many(list(seed.materials))
        repositories.activities.add_many(list(seed.activities))
        repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
    with SqlalchemyLearningDatabase(
        postgres_database.engine
    ).transaction() as repositories:
        repositories.goals.add_many(list(seed.goals))
        repositories.skill_experiences.add_many(list(seed.skill_experiences))
        repositories.competency_progresses.add_many(list(seed.competency_progresses))
        repositories.activity_attempts.add_many(list(seed.activity_attempts))
        repositories.activity_evaluations.add_many(list(seed.activity_evaluations))
        experience = repositories.skill_experiences.find_by_id(
            SEED_ADAPTIVE_LAB_EXPERIENCE_ID
        )
        assert experience is not None
        experience.status = SkillExperienceStatus.LEARNING
        repositories.skill_experiences.update(experience)

    application = FastAPIApp.register(postgres_database.engine)
    application.state.authentication_provider = _TestAuthenticationProvider()
    application.state.inngest_broker = _NoopBroker()
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application, raise_server_exceptions=False) as test_client:
        yield test_client


def _batch(answer: dict[str, object]) -> dict[str, object]:
    return {
        'submission_key': _SUBMISSION_KEY,
        'items': [
            {
                'competency_id': SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
                'activity_id': FillBlanksActivityFixture.ACTIVITY_ID,
                'activity_revision': 'revision-1',
                'answers': [answer],
            }
        ],
    }


def _submit(client: TestClient, body: dict[str, object]) -> 'Response':
    return cast(
        'Response',
        client.post(  # pyright: ignore[reportUnknownMemberType]
            f'/learning/goals/{SEED_ADAPTIVE_LAB_GOAL_ID}'
            f'/skills/{SEED_ADAPTIVE_LAB_SKILL_ID}/diagnostic/submissions',
            json=body,
            headers={
                'Authorization': 'Bearer test-access-token',
                'X-Diagnostic-Run-Id': _RUN_ID,
            },
        ),
    )


class TestSubmitDiagnosticBatchController:
    def test_should_reject_a_fill_blanks_answer_without_persistence(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        before = FillBlanksActivityFixture.write_counts(postgres_database)

        response = _submit(
            client, _batch(FillBlanksActivityFixture.fill_answer(*CORRECT_PAIRS))
        )

        assert response.status_code == 422, response.json()
        assert FillBlanksActivityFixture.write_counts(postgres_database) == before

    def test_should_reject_an_image_choice_answer_without_persistence(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        before = ImageChoiceActivityFixture.write_counts(postgres_database)

        response = _submit(
            client,
            _batch(
                ImageChoiceActivityFixture.image_answer(
                    ImageChoiceActivityFixture.CORRECT_OPTION_KEY
                )
            ),
        )

        assert response.status_code == 422, response.json()
        assert ImageChoiceActivityFixture.write_counts(postgres_database) == before

    def test_should_let_other_kinds_past_the_request_boundary_to_the_run_check(
        self, client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        before = FillBlanksActivityFixture.write_counts(postgres_database)

        response = _submit(
            client,
            _batch(
                {
                    'kind': 'single_choice',
                    'question_key': 'q1',
                    'selected_option_keys': ['a'],
                }
            ),
        )

        # The kind passes the request boundary; no diagnostic run is open for the goal.
        assert response.status_code == 409, response.json()
        assert response.json()['code'] == 'conflict'
        assert FillBlanksActivityFixture.write_counts(postgres_database) == before
