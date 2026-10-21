from datetime import timedelta
from typing import TYPE_CHECKING, cast

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.identity.core.domain.enums import AccountStatus
from shifu.intelligence.core.domain.enums import LearnerMemoryCategory
from shifu.intelligence.core.domain.structures import LearnerMemoryConcept
from shifu.shared.constants import ENVIRONMENT
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.learner_memory_scenarios import (
    BASE_TIME,
    OTHER_ACCOUNT,
    create_account,
    iso,
    memory_id,
    memory_keys,
    real_access_client,
    seed_conversation,
    seed_memory,
)

if TYPE_CHECKING:
    from httpx import Response

PATH = '/intelligence/learner-memories'


class TestListLearnerMemoriesController:
    def test_should_require_authentication(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app, headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret}
        ) as client:
            response = cast('Response', client.get(PATH))

        assert response.status_code == 401
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_reject_an_inactive_account_without_listing(
        self, postgres_database: PostgresDatabase
    ) -> None:
        account_id = create_account(
            postgres_database, AccountStatus.PENDING_CONFIRMATION
        )
        seed_memory(postgres_database, 1, account_id=account_id)

        with real_access_client(postgres_database, account_id) as client:
            response = cast('Response', client.get(PATH))

        assert response.status_code == 403
        assert response.headers['cache-control'] == 'private, no-store'
        assert 'items' not in response.json()

    def test_should_list_an_active_accounts_memories_through_the_real_access_check(
        self, postgres_database: PostgresDatabase
    ) -> None:
        account_id = create_account(postgres_database, AccountStatus.ACTIVE)
        seed_memory(postgres_database, 1, account_id=account_id)

        with real_access_client(postgres_database, account_id) as client:
            response = cast('Response', client.get(PATH))

        assert response.status_code == 200
        assert [item['id'] for item in response.json()['items']] == [memory_id(1)]

    def test_should_return_an_empty_list_without_memories(
        self, mentor_client: TestClient
    ) -> None:
        response = cast('Response', mentor_client.get(PATH))

        assert response.status_code == 200
        assert response.json() == {'items': []}
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_return_the_complete_shape_with_origins_and_ordered_concepts(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(
            postgres_database, title='Exemplos em Python'
        )
        memory = seed_memory(
            postgres_database,
            1,
            version=3,
            concepts=(
                LearnerMemoryConcept(key='exemplo curto', label='Exemplos curtos'),
                LearnerMemoryConcept(key='python', label='Python'),
            ),
            origins=((session_id, message_id),),
        )

        response = cast('Response', mentor_client.get(PATH))

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.json() == {
            'items': [
                {
                    'id': memory.id,
                    'category': 'explanation_preference',
                    'content': 'Prefiro exemplos em Python.',
                    'version': 3,
                    'created_at': iso(memory.created_at),
                    'updated_at': iso(memory.updated_at),
                    'origins': [
                        {
                            'session_id': session_id,
                            'message_id': message_id,
                            'conversation_title': 'Exemplos em Python',
                            'is_available': True,
                            'declared_at': iso(memory.updated_at),
                        }
                    ],
                    'concepts': [
                        {'key': 'exemplo curto', 'label': 'Exemplos curtos'},
                        {'key': 'python', 'label': 'Python'},
                    ],
                }
            ]
        }
        assert set(response.json()['items'][0]) == memory_keys()

    def test_should_order_by_update_time_descending_then_id(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 3, updated_at=BASE_TIME)
        seed_memory(postgres_database, 2, updated_at=BASE_TIME + timedelta(hours=1))
        seed_memory(postgres_database, 1, updated_at=BASE_TIME + timedelta(hours=1))
        seed_memory(postgres_database, 4, updated_at=BASE_TIME + timedelta(hours=2))

        response = cast('Response', mentor_client.get(PATH))

        assert [item['id'] for item in response.json()['items']] == [
            memory_id(4),
            memory_id(1),
            memory_id(2),
            memory_id(3),
        ]

    def test_should_never_list_another_accounts_memories(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1)
        seed_memory(postgres_database, 2, account_id=OTHER_ACCOUNT.account_id)

        response = cast('Response', mentor_client.get(PATH))

        assert [item['id'] for item in response.json()['items']] == [memory_id(1)]

    def test_should_filter_by_category(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1)
        seed_memory(
            postgres_database,
            2,
            category=LearnerMemoryCategory.DECLARED_KNOWLEDGE,
            content='Sei Python.',
        )
        seed_memory(
            postgres_database,
            3,
            category=LearnerMemoryCategory.RECURRING_DIFFICULTY,
            content='Tenho dificuldade com laços.',
        )

        response = cast(
            'Response',
            mentor_client.get(PATH, params={'category': 'declared_knowledge'}),
        )

        assert response.status_code == 200
        assert [item['id'] for item in response.json()['items']] == [memory_id(2)]

    def test_should_match_the_query_ignoring_case_and_accents_in_both_directions(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1, content='Prefiro EXPLICAÇÕES curtas.')
        seed_memory(postgres_database, 2, content='Quero criar um jogo.')

        for query in ('explicacoes', 'EXPLICAÇÕES', 'explicações', 'ExplicaCoes'):
            response = cast('Response', mentor_client.get(PATH, params={'q': query}))
            assert response.status_code == 200
            assert [item['id'] for item in response.json()['items']] == [memory_id(1)]

    def test_should_match_a_substring_and_trim_the_query(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1, content='Prefiro exemplos em Python.')

        response = cast(
            'Response', mentor_client.get(PATH, params={'q': '  emplos em  '})
        )

        assert [item['id'] for item in response.json()['items']] == [memory_id(1)]

    def test_should_treat_wildcards_in_the_query_literally(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1, content='Tenho 100% de foco.')
        seed_memory(postgres_database, 2, content='Uso nome_variavel sempre.')
        seed_memory(postgres_database, 3, content='Uso caminho\\arquivo no Windows.')
        seed_memory(postgres_database, 4, content='Sem símbolos.')

        for query, expected in (('%', 1), ('_', 2), ('\\', 3)):
            response = cast('Response', mentor_client.get(PATH, params={'q': query}))
            assert [item['id'] for item in response.json()['items']] == [
                memory_id(expected)
            ]

    def test_should_combine_query_and_category_and_treat_a_blank_query_as_absent(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1, content='Prefiro exemplos em Python.')
        seed_memory(
            postgres_database,
            2,
            category=LearnerMemoryCategory.DECLARED_KNOWLEDGE,
            content='Sei Python.',
        )

        both = cast(
            'Response',
            mentor_client.get(
                PATH, params={'q': 'python', 'category': 'declared_knowledge'}
            ),
        )
        blank = cast('Response', mentor_client.get(PATH, params={'q': '   '}))

        assert [item['id'] for item in both.json()['items']] == [memory_id(2)]
        assert len(blank.json()['items']) == 2

    def test_should_reject_an_invalid_category_and_an_oversized_query(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1)

        category = cast(
            'Response', mentor_client.get(PATH, params={'category': 'mood'})
        )
        oversized = cast('Response', mentor_client.get(PATH, params={'q': 'a' * 101}))
        limit = cast('Response', mentor_client.get(PATH, params={'q': 'a' * 100}))

        assert category.status_code == 422
        assert oversized.status_code == 422
        assert oversized.headers['cache-control'] == 'private, no-store'
        assert limit.status_code == 200

    def test_should_report_an_origin_whose_conversation_was_deleted_as_unavailable(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database, title='Apagada')
        seed_memory(postgres_database, 1, origins=((session_id, message_id),))

        deleted = mentor_client.delete(f'/intelligence/mentor-sessions/{session_id}')
        response = cast('Response', mentor_client.get(PATH))

        assert deleted.status_code == 204
        [origin] = response.json()['items'][0]['origins']
        assert origin['session_id'] == session_id
        assert origin['message_id'] is None
        assert origin['conversation_title'] is None
        assert origin['is_available'] is False
