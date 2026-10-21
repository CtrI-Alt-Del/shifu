from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.app import FastAPIApp
from shifu.intelligence.core.domain.enums import LearnerMemoryChangeKind
from shifu.intelligence.core.domain.structures import LearnerMemoryConcept
from shifu.intelligence.database.sqlalchemy.models import (
    LearnerMemoryChangeModel,
    LearnerMemoryConceptModel,
    LearnerMemoryModel,
    LearnerMemoryOriginModel,
)
from shifu.shared.constants import ENVIRONMENT
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import MENTOR_ACCOUNT
from tests.intelligence.server.controllers.learner_memory_scenarios import (
    ABSENT_MEMORY_ID,
    BASE_TIME,
    OTHER_ACCOUNT,
    database_of,
    memory_id,
    other_account_client,
    read_fence,
    seed_change,
    seed_conversation,
    seed_memory,
)

if TYPE_CHECKING:
    from httpx import Response

PATH = '/intelligence/learner-memories'


def _count(postgres_database: PostgresDatabase, model: type) -> int:
    with Session(postgres_database.engine) as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


class TestRemoveLearnerMemoryController:
    def test_should_require_authentication(
        self, postgres_database: PostgresDatabase
    ) -> None:
        app = FastAPIApp.register(postgres_database.engine)
        with TestClient(
            app, headers={'x-shifu-bff-secret': ENVIRONMENT.bff_shared_secret}
        ) as client:
            response = cast('Response', client.delete(f'{PATH}/{ABSENT_MEMORY_ID}'))

        assert response.status_code == 401
        assert response.headers['cache-control'] == 'private, no-store'

    def test_should_treat_a_malformed_memory_id_as_absent_without_effect(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        seed_memory(postgres_database, 1)

        response = cast('Response', mentor_client.delete(f'{PATH}/not-a-ulid'))

        assert response.status_code == 204
        assert response.headers['cache-control'] == 'private, no-store'
        assert _count(postgres_database, LearnerMemoryModel) == 1

    def test_should_delete_the_memory_with_its_origins_and_concepts_and_advance_the_fence(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        memory = seed_memory(
            postgres_database,
            1,
            concepts=(LearnerMemoryConcept(key='python', label='Python'),),
            origins=((session_id, message_id),),
        )
        seed_memory(postgres_database, 2)
        assert read_fence(postgres_database) is None

        before = datetime.now(UTC)
        response = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))

        assert response.status_code == 204
        assert response.headers['cache-control'] == 'private, no-store'
        assert response.content == b''
        with database_of(postgres_database).transaction() as repositories:
            assert (
                repositories.learner_memories.find_details(
                    MENTOR_ACCOUNT.account_id, memory.id
                )
                is None
            )
            remaining = repositories.learner_memories.find_many_by_account(
                MENTOR_ACCOUNT.account_id
            )
        assert [item.id for item in remaining] == [memory_id(2)]
        assert _count(postgres_database, LearnerMemoryConceptModel) == 0
        assert _count(postgres_database, LearnerMemoryOriginModel) == 1
        fence = read_fence(postgres_database)
        assert fence is not None
        assert before <= fence <= datetime.now(UTC)

    def test_should_erase_the_change_texts_and_show_deleted_items_without_text(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        memory = seed_memory(
            postgres_database,
            1,
            content='Agora prefiro JavaScript.',
            origins=((session_id, message_id),),
        )
        change_id = seed_change(
            postgres_database,
            memory,
            session_id,
            message_id,
            kind=LearnerMemoryChangeKind.UPDATED,
            previous_content='Prefiro Python.',
        )

        response = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))
        detail = mentor_client.get(f'/intelligence/mentor-sessions/{session_id}')

        assert response.status_code == 204
        [item] = detail.json()['memory_items']
        assert item['id'] == change_id
        assert item['kind'] == 'updated'
        assert item['source_message_id'] == message_id
        assert item['memory_id'] is None
        assert item['content'] is None
        assert item['previous_content'] is None
        with Session(postgres_database.engine) as session:
            row = session.get(LearnerMemoryChangeModel, change_id)
            assert row is not None
            assert (row.content, row.previous_content, row.memory_id) == (
                None,
                None,
                None,
            )

    def test_should_succeed_without_effect_when_repeated_or_absent(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        first = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))
        fence = read_fence(postgres_database)
        repeated = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))
        absent = cast('Response', mentor_client.delete(f'{PATH}/{ABSENT_MEMORY_ID}'))

        assert (first.status_code, repeated.status_code, absent.status_code) == (
            204,
            204,
            204,
        )
        assert repeated.headers['cache-control'] == 'private, no-store'
        assert fence is not None
        assert read_fence(postgres_database) == fence

    def test_should_never_move_the_fence_backwards(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        memory = seed_memory(postgres_database, 1)
        future = datetime.now(UTC) + timedelta(days=30)
        with database_of(postgres_database).transaction() as repositories:
            repositories.learner_memories.advance_fence(
                MENTOR_ACCOUNT.account_id, future
            )

        response = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))

        assert response.status_code == 204
        assert read_fence(postgres_database) == future

    def test_should_keep_a_foreign_memory_and_its_change_texts_intact(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(
            postgres_database, OTHER_ACCOUNT.account_id
        )
        memory = seed_memory(
            postgres_database,
            1,
            account_id=OTHER_ACCOUNT.account_id,
            content='Segredo do outro aprendiz.',
            origins=((session_id, message_id),),
        )
        change_id = seed_change(postgres_database, memory, session_id, message_id)

        response = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))

        assert response.status_code == 204
        with database_of(postgres_database).transaction() as repositories:
            kept = repositories.learner_memories.find_details(
                OTHER_ACCOUNT.account_id, memory.id
            )
        assert kept is not None
        assert kept.memory.content == 'Segredo do outro aprendiz.'
        with Session(postgres_database.engine) as session:
            row = session.get(LearnerMemoryChangeModel, change_id)
            assert row is not None
            assert row.content == 'Segredo do outro aprendiz.'
            assert row.memory_id == memory.id
        assert read_fence(postgres_database, OTHER_ACCOUNT.account_id) is None
        assert read_fence(postgres_database) is None

    def test_should_let_the_owner_delete_after_a_foreign_attempt(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        memory = seed_memory(postgres_database, 1)

        with other_account_client(postgres_database) as other:
            stranger = cast('Response', other.delete(f'{PATH}/{memory.id}'))
        owner = cast('Response', mentor_client.delete(f'{PATH}/{memory.id}'))

        assert stranger.status_code == 204
        assert owner.status_code == 204
        assert _count(postgres_database, LearnerMemoryModel) == 0

    def test_should_keep_other_memories_visible_to_the_list_after_a_delete(
        self, mentor_client: TestClient, postgres_database: PostgresDatabase
    ) -> None:
        deleted = seed_memory(postgres_database, 1)
        kept = seed_memory(postgres_database, 2)

        mentor_client.delete(f'{PATH}/{deleted.id}')
        listed = mentor_client.get(PATH)

        assert [item['id'] for item in listed.json()['items']] == [kept.id]


class TestLearnerMemoryPersistenceConstraints:
    @pytest.mark.parametrize(
        'overrides',
        [
            {'category': 'mood'},
            {'content': ''},
            {'content': 'x' * 281},
            {'version': 0},
        ],
    )
    def test_should_reject_invalid_memory_rows(
        self, postgres_database: PostgresDatabase, overrides: dict[str, object]
    ) -> None:
        values: dict[str, object] = {
            'id': memory_id(1),
            'account_id': MENTOR_ACCOUNT.account_id,
            'category': 'declared_knowledge',
            'content': 'Sei Python.',
            'content_search': 'sei python.',
            'version': 1,
            'last_declared_at': BASE_TIME,
            'created_at': BASE_TIME,
            'updated_at': BASE_TIME,
        } | overrides
        with Session(postgres_database.engine) as session:
            session.add(LearnerMemoryModel(**values))
            with pytest.raises(IntegrityError):
                session.flush()

    def test_should_accept_content_of_exactly_one_and_280_code_points(
        self, postgres_database: PostgresDatabase
    ) -> None:
        for number, content in enumerate(('x', 'y' * 280), start=1):
            seed_memory(postgres_database, number, content=content)

        assert _count(postgres_database, LearnerMemoryModel) == 2

    def test_should_reject_a_concept_position_outside_the_three_slots(
        self, postgres_database: PostgresDatabase
    ) -> None:
        memory = seed_memory(postgres_database, 1)
        with Session(postgres_database.engine) as session:
            session.add(
                LearnerMemoryConceptModel(
                    memory_id=memory.id,
                    concept_key='python',
                    label='Python',
                    position=3,
                )
            )
            with pytest.raises(IntegrityError):
                session.flush()

    def test_should_reject_text_kept_without_a_memory_and_a_created_change_with_previous_text(
        self, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        memory = seed_memory(postgres_database, 1, origins=((session_id, message_id),))

        def change(**overrides: object) -> LearnerMemoryChangeModel:
            values: dict[str, object] = {
                'id': SystemIdentifierProvider().generate(),
                'account_id': MENTOR_ACCOUNT.account_id,
                'memory_id': memory.id,
                'session_id': session_id,
                'message_id': message_id,
                'kind': 'created',
                'category': 'explanation_preference',
                'content': 'Texto',
                'previous_content': None,
                'created_at': BASE_TIME,
            } | overrides
            return LearnerMemoryChangeModel(**values)

        for invalid in (
            change(memory_id=None),
            change(kind='updated', memory_id=None, content=None, previous_content='x'),
            change(previous_content='Antes', kind='created'),
            change(kind='removed'),
            change(category='mood'),
        ):
            with Session(postgres_database.engine) as session:
                session.add(invalid)
                with pytest.raises(IntegrityError):
                    session.flush()

    def test_should_accept_a_textless_change_without_a_memory(
        self, postgres_database: PostgresDatabase
    ) -> None:
        session_id, message_id = seed_conversation(postgres_database)
        memory = seed_memory(postgres_database, 1, origins=((session_id, message_id),))
        change_id = seed_change(postgres_database, memory, session_id, message_id)
        with database_of(postgres_database).transaction() as repositories:
            repositories.learner_memory_changes.erase_by_memory_id(
                MENTOR_ACCOUNT.account_id, memory.id
            )

        with Session(postgres_database.engine) as session:
            row = session.get(LearnerMemoryChangeModel, change_id)
            assert row is not None
            assert (row.memory_id, row.content, row.previous_content) == (
                None,
                None,
                None,
            )
