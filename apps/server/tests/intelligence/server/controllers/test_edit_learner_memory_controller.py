from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shifu.app import FastAPIApp
from shifu.identity.core.domain.enums import AccountStatus
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryAnalysis,
    LearnerMemoryConcept,
)
from shifu.intelligence.database.sqlalchemy.models import LearnerMemoryChangeModel
from shifu.shared.constants import ENVIRONMENT
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.learner_memory_scenarios import (
    ABSENT_MEMORY_ID,
    BASE_TIME,
    OTHER_ACCOUNT,
    create_account,
    database_of,
    iso,
    memory_keys,
    other_account_client,
    real_access_client,
    seed_change,
    seed_conversation,
    seed_memory,
)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from httpx import Response

PATH = '/intelligence/learner-memories'
NEW_CONCEPTS = (
    LearnerMemoryConcept(key='javascript', label='JavaScript'),
    LearnerMemoryConcept(key='exemplo', label='Exemplos'),
)


class _ConceptsAnalyzerStub:
    """Deterministic concepts; edit must never classify statements."""

    def __init__(self) -> None:
        self.contents: list[str] = []

    def analyze(self, text: str) -> LearnerMemoryAnalysis:
        raise AssertionError('Editing a memory must not run the classifier')

    def concepts(self, content: str) -> tuple[LearnerMemoryConcept, ...]:
        self.contents.append(content)
        return NEW_CONCEPTS


@pytest.fixture
def analyzer(
    mentor_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> _ConceptsAnalyzerStub:
    stub = _ConceptsAnalyzerStub()
    monkeypatch.setattr(
        cast('FastAPI', mentor_client.app).state, 'learner_memory_analyzer', stub
    )
    return stub


def _patch(
    client: TestClient, memory_id: str, content: str, expected_version: int
) -> 'Response':
    return cast(
        'Response',
        client.patch(
            f'{PATH}/{memory_id}',
            json={'content': content, 'expected_version': expected_version},
        ),
    )


class TestEditLearnerMemoryController:
    def test_should_require_authentication(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app, headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret}
        ) as client:
            response = _patch(client, ABSENT_MEMORY_ID, 'Prefiro curtos.', 1)

        assert response.status_code == 401
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_reject_an_inactive_account_without_changing_the_memory(
        self, postgres_database: PostgresDatabase
    ) -> None:
        account_id = create_account(postgres_database, AccountStatus.DELETED)
        memory = seed_memory(postgres_database, 1, account_id=account_id)

        with real_access_client(postgres_database, account_id) as client:
            response = _patch(client, memory.id, 'Prefiro exemplos curtos.', 1)

        assert response.status_code == 403
        assert response.headers['cache-control'] == 'private, no-store'
        with database_of(postgres_database).transaction() as repositories:
            kept = repositories.learner_memories.find_details(account_id, memory.id)
        assert kept is not None
        assert (kept.memory.content, kept.memory.version) == (memory.content, 1)

    def test_should_edit_content_recompute_concepts_and_persist_the_new_version(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
    ) -> None:
        memory = seed_memory(
            postgres_database,
            1,
            concepts=(LearnerMemoryConcept(key='python', label='Python'),),
        )
        before = datetime.now(UTC)

        response = _patch(
            mentor_client, memory.id, '  Prefiro exemplos em JavaScript.  ', 1
        )

        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        body = response.json()
        assert set(body) == memory_keys()
        assert body['content'] == 'Prefiro exemplos em JavaScript.'
        assert body['version'] == 2
        assert body['created_at'] == iso(memory.created_at)
        assert body['concepts'] == [
            {'key': 'javascript', 'label': 'JavaScript'},
            {'key': 'exemplo', 'label': 'Exemplos'},
        ]
        assert analyzer.contents == ['Prefiro exemplos em JavaScript.']
        fetched = mentor_client.get(f'{PATH}/{memory.id}').json()
        assert fetched == body
        with database_of(postgres_database).transaction() as repositories:
            stored = repositories.learner_memories.find_by_id_for_update(
                MENTOR_ACCOUNT.account_id, memory.id
            )
        assert stored is not None
        assert stored.version == 2
        assert stored.created_at == memory.created_at
        assert before <= stored.last_declared_at == stored.updated_at
        assert stored.updated_at > memory.updated_at

    def test_should_find_the_edited_text_through_the_search_and_not_the_old_one(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
    ) -> None:
        memory = seed_memory(postgres_database, 1, content='Prefiro vídeos longos.')

        _patch(mentor_client, memory.id, 'Prefiro ÁUDIOS curtos.', 1)

        found = mentor_client.get(PATH, params={'q': 'audios'}).json()['items']
        stale = mentor_client.get(PATH, params={'q': 'videos'}).json()['items']
        assert [item['id'] for item in found] == [memory.id]
        assert stale == []

    def test_should_create_no_change_record_or_marker(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        memory = seed_memory(postgres_database, 1, origins=((session_id, message_id),))
        seed_change(postgres_database, memory, session_id, message_id)

        response = _patch(mentor_client, memory.id, 'Prefiro exemplos curtos.', 1)

        assert response.status_code == 200
        detail = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}').json()
        assert [item['content'] for item in detail['memory_items']] == [memory.content]
        with Session(postgres_database.engine) as session:
            assert (
                session.scalar(
                    select(func.count()).select_from(LearnerMemoryChangeModel)
                )
                == 1
            )

    def test_should_return_conflict_for_a_stale_version_and_change_nothing(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        first = _patch(mentor_client, memory.id, 'Prefiro exemplos curtos.', 1)
        stale = _patch(mentor_client, memory.id, 'Prefiro vídeos.', 1)

        assert first.status_code == 200
        assert stale.status_code == 409
        assert stale.headers['cache-control'] == 'private, no-store'
        assert stale.json()['code'] == 'conflict'
        current = mentor_client.get(f'{PATH}/{memory.id}').json()
        assert current['content'] == 'Prefiro exemplos curtos.'
        assert current['version'] == 2
        # Concepts are computed before the lock, so the stale attempt computed them too.
        assert analyzer.contents == ['Prefiro exemplos curtos.', 'Prefiro vídeos.']

    @pytest.mark.parametrize('content', ['', '    ', 'x' * 281, ' ' + 'x' * 281])
    def test_should_return_a_memory_specific_validation_error_for_invalid_content(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
        content: str,
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        response = _patch(mentor_client, memory.id, content, 1)

        assert response.status_code == 422
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.json() == {
            'detail': {
                'code': 'validation_error',
                'message': 'O texto da memória deve ter entre 1 e 280 caracteres.',
            }
        }
        unchanged = mentor_client.get(f'{PATH}/{memory.id}').json()
        assert (unchanged['content'], unchanged['version']) == (memory.content, 1)

    def test_should_accept_content_of_exactly_280_code_points(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        response = _patch(mentor_client, memory.id, 'x' * 280, 1)

        assert response.status_code == 200
        assert response.json()['content'] == 'x' * 280

    @pytest.mark.parametrize(
        'body',
        [
            {'content': 'Texto'},
            {'expected_version': 1},
            {'content': 'Texto', 'expected_version': 0},
            {'content': 'Texto', 'expected_version': '1'},
            {'content': 'Texto', 'expected_version': 1.5},
            {'content': 7, 'expected_version': 1},
            {
                'content': 'Texto',
                'expected_version': 1,
                'category': 'declared_knowledge',
            },
        ],
    )
    def test_should_reject_a_malformed_body(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
        body: dict[str, object],
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        response = cast(
            'Response', mentor_client.patch(f'{PATH}/{memory.id}', json=body)
        )

        assert response.status_code == 422
        assert response.json()['code'] == 'validation_error'
        assert analyzer.contents == []
        assert mentor_client.get(f'{PATH}/{memory.id}').json()['version'] == 1

    def test_should_treat_a_malformed_memory_id_as_absent(
        self, mentor_client: TestClient, analyzer: _ConceptsAnalyzerStub
    ) -> None:
        absent = _patch(mentor_client, ABSENT_MEMORY_ID, 'Texto', 1)
        malformed = _patch(mentor_client, 'not-a-ulid', 'Texto', 1)

        assert malformed.status_code == 404
        assert malformed.json() == absent.json()
        assert malformed.headers['cache-control'] == 'private, no-store'

    def test_should_return_the_same_not_found_for_absent_and_foreign_memories(
        self,
        mentor_client: TestClient,
        postgres_database: PostgresDatabase,
        analyzer: _ConceptsAnalyzerStub,
    ) -> None:
        foreign = seed_memory(
            postgres_database,
            1,
            account_id=OTHER_ACCOUNT.account_id,
            content='Segredo do outro aprendiz.',
            updated_at=BASE_TIME,
        )

        absent = _patch(mentor_client, ABSENT_MEMORY_ID, 'Texto', 1)
        hidden = _patch(mentor_client, foreign.id, 'Texto', 1)

        assert (absent.status_code, hidden.status_code) == (404, 404)
        assert hidden.json() == absent.json()
        assert hidden.headers['cache-control'] == 'private, no-store'
        with other_account_client(postgres_database) as other:
            kept = other.get(f'{PATH}/{foreign.id}').json()
        assert (kept['content'], kept['version']) == ('Segredo do outro aprendiz.', 1)

    def test_should_recompute_concepts_with_the_composed_analyzer(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        memory = seed_memory(
            postgres_database,
            1,
            concepts=(LearnerMemoryConcept(key='semente', label='Semente'),),
        )

        response = _patch(
            mentor_client, memory.id, 'Prefiro exemplos curtos de funções.', 1
        )

        assert response.status_code == 200
        concepts = response.json()['concepts']
        assert len(concepts) <= 3
        assert 'semente' not in [concept['key'] for concept in concepts]
        assert mentor_client.get(f'{PATH}/{memory.id}').json()['concepts'] == concepts
