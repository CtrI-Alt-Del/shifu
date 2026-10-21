from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.intelligence.core.domain.structures import LearnerMemoryConcept
from shifu.shared.constants import ENVIRONMENT
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.learner_memory_scenarios import (
    ABSENT_MEMORY_ID,
    OTHER_ACCOUNT,
    iso,
    memory_keys,
    other_account_client,
    seed_conversation,
    seed_memory,
)

if TYPE_CHECKING:
    from httpx import Response

PATH = '/intelligence/learner-memories'


class TestGetLearnerMemoryController:
    def test_should_require_authentication(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app, headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret}
        ) as client:
            response = cast('Response', client.get(f'{PATH}/{ABSENT_MEMORY_ID}'))

        assert response.status_code == 401
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_return_one_owned_memory_with_origins_and_concepts(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        first = seed_conversation(postgres_database, title='Primeira')
        second = seed_conversation(postgres_database, title='Segunda')
        memory = seed_memory(
            postgres_database,
            1,
            version=2,
            concepts=(LearnerMemoryConcept(key='python', label='Python'),),
            origins=(first, second),
        )

        response = cast('Response', mentor_client.get(f'{PATH}/{memory.id}'))

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert set(body) == memory_keys()
        assert body['id'] == memory.id
        assert body['version'] == 2
        assert body['created_at'] == iso(memory.created_at)
        assert body['concepts'] == [{'key': 'python', 'label': 'Python'}]
        assert {origin['conversation_title'] for origin in body['origins']} == {
            'Primeira',
            'Segunda',
        }
        assert all(origin['is_available'] for origin in body['origins'])

    def test_should_return_the_same_not_found_for_absent_and_foreign_memories(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        foreign = seed_memory(postgres_database, 1, account_id=OTHER_ACCOUNT.account_id)

        absent = cast('Response', mentor_client.get(f'{PATH}/{ABSENT_MEMORY_ID}'))
        hidden = cast('Response', mentor_client.get(f'{PATH}/{foreign.id}'))

        assert absent.status_code == 404
        assert hidden.status_code == 404
        assert hidden.json() == absent.json()
        assert hidden.headers['cache-control'] == 'private, no-store'

    def test_should_let_only_the_owner_read_the_memory(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        with other_account_client(postgres_database) as other:
            stranger = cast('Response', other.get(f'{PATH}/{memory.id}'))
        owner = cast('Response', mentor_client.get(f'{PATH}/{memory.id}'))

        assert stranger.status_code == 404
        assert owner.status_code == 200

    def test_should_treat_a_malformed_memory_id_as_absent(
        self, mentor_client: TestClient
    ) -> None:
        absent = cast('Response', mentor_client.get(f'{PATH}/{ABSENT_MEMORY_ID}'))
        malformed = cast('Response', mentor_client.get(f'{PATH}/not-a-ulid'))

        assert malformed.status_code == 404
        assert malformed.json() == absent.json()
        assert malformed.headers['cache-control'] == 'private, no-store'
