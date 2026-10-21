"""Shared setup for the learner-memory controller tests."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.identity.core.domain.enums import AccountStatus
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    LearnerMemoryChange,
    MentorMessage,
    MentorSession,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    LearnerMemoryChangeKind,
    MentorMessageRole,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryConcept,
    LearnerMemoryOrigin,
)
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser
from shifu.shared.pipes import SharedPipe
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.postgres_fixture import PostgresDatabase
from tests.intelligence.server.controllers.conftest import (
    MENTOR_ACCOUNT,
    MentorTitleWorkflowStub,
    configure_mentor_access,
)

OTHER_ACCOUNT = AuthenticatedUser(
    account_id='01JOTHER000000000000TEST',
    display_name='Other Learner',
    time_zone=None,
)
BASE_TIME = datetime(2026, 3, 1, 12, tzinfo=UTC)
ABSENT_MEMORY_ID = '01J00000000000000000000999'
_IDENTIFIERS = SystemIdentifierProvider()


def memory_id(number: int) -> str:
    """A valid, ordered ULID-shaped memory id."""
    return f'01J00000000000000000000{number:03d}'


def database_of(postgres_database: PostgresDatabase) -> SqlalchemyIntelligenceDatabase:
    return SqlalchemyIntelligenceDatabase(engine=postgres_database.engine)


def seed_conversation(
    postgres_database: PostgresDatabase,
    account_id: str = MENTOR_ACCOUNT.account_id,
    *,
    title: str = 'Conversa de memórias',
    content: str = 'Prefiro exemplos em Python.',
    created_at: datetime = BASE_TIME,
) -> tuple[str, str]:
    """Persist an owned conversation with one learner message."""
    session_id, message_id = _IDENTIFIERS.generate(), _IDENTIFIERS.generate()
    with database_of(postgres_database).transaction() as repositories:
        repositories.mentor_sessions.add(
            MentorSession(
                id=session_id,
                account_id=account_id,
                title=title,
                created_at=created_at,
                updated_at=created_at,
                last_activity_at=created_at,
            ),
            str(uuid4()),
            f'fingerprint:{session_id}',
        )
        repositories.mentor_messages.add(
            MentorMessage(
                id=message_id,
                session_id=session_id,
                role=MentorMessageRole.LEARNER,
                content=content,
                created_at=created_at,
                in_reply_to_message_id=None,
            )
        )
    return session_id, message_id


def seed_memory(
    postgres_database: PostgresDatabase,
    number: int,
    *,
    account_id: str = MENTOR_ACCOUNT.account_id,
    category: LearnerMemoryCategory = LearnerMemoryCategory.EXPLANATION_PREFERENCE,
    content: str = 'Prefiro exemplos em Python.',
    version: int = 1,
    updated_at: datetime = BASE_TIME,
    concepts: tuple[LearnerMemoryConcept, ...] = (),
    origins: tuple[tuple[str, str], ...] = (),
) -> LearnerMemory:
    """Persist a memory with origins given as ``(session_id, message_id)`` pairs."""
    memory = LearnerMemory(
        id=memory_id(number),
        account_id=account_id,
        category=category,
        content=content,
        version=version,
        last_declared_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )
    if not origins:
        origins = (seed_conversation(postgres_database, account_id),)
    first, *others = origins
    with database_of(postgres_database).transaction() as repositories:
        repositories.learner_memories.add(
            memory,
            concepts,
            LearnerMemoryOrigin(
                session_id=first[0], message_id=first[1], declared_at=updated_at
            ),
        )
        for session_id, message_id in others:
            repositories.learner_memories.add_origin(
                memory.id,
                LearnerMemoryOrigin(
                    session_id=session_id,
                    message_id=message_id,
                    declared_at=updated_at + timedelta(minutes=1),
                ),
            )
    return memory


def seed_change(
    postgres_database: PostgresDatabase,
    memory: LearnerMemory,
    session_id: str,
    message_id: str,
    *,
    kind: LearnerMemoryChangeKind = LearnerMemoryChangeKind.CREATED,
    previous_content: str | None = None,
    created_at: datetime = BASE_TIME,
) -> str:
    """Persist a change record of ``memory`` anchored to a learner message."""
    change_id = _IDENTIFIERS.generate()
    with database_of(postgres_database).transaction() as repositories:
        repositories.learner_memory_changes.add(
            LearnerMemoryChange(
                id=change_id,
                account_id=memory.account_id,
                memory_id=memory.id,
                session_id=session_id,
                message_id=message_id,
                kind=kind,
                category=memory.category,
                content=memory.content,
                previous_content=previous_content,
                created_at=created_at,
            )
        )
    return change_id


def read_fence(
    postgres_database: PostgresDatabase, account_id: str = MENTOR_ACCOUNT.account_id
) -> datetime | None:
    with database_of(postgres_database).transaction() as repositories:
        return repositories.learner_memories.lock_account(account_id)


@contextmanager
def other_account_client(
    postgres_database: PostgresDatabase,
) -> Generator[TestClient]:
    """A second application whose authenticated learner is another account."""
    app = FastAPIApp.register(postgres_database.engine)
    configure_mentor_access(app)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: OTHER_ACCOUNT
    app.dependency_overrides[IntelligencePipe.get_generate_mentor_title_workflow] = (
        MentorTitleWorkflowStub
    )
    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client


@contextmanager
def real_access_client(
    postgres_database: PostgresDatabase, account_id: str
) -> Generator[TestClient]:
    """An application using the real Identity access check for ``account_id``."""
    app = FastAPIApp.register(postgres_database.engine)
    app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
        AuthenticatedUser(account_id=account_id, display_name='Learner', time_zone=None)
    )
    with TestClient(app, headers={'Authorization': 'Bearer synthetic'}) as client:
        yield client


def create_account(postgres_database: PostgresDatabase, status: AccountStatus) -> str:
    """Persist an Identity account in ``status`` and return its id."""
    account = AccountFaker.fake(status=status)
    with SqlalchemyIdentityDatabase(engine=postgres_database.engine).transaction() as (
        repositories
    ):
        repositories.accounts.add(account)
    return account.id


def memory_keys() -> set[str]:
    return {
        'id',
        'category',
        'content',
        'version',
        'created_at',
        'updated_at',
        'origins',
        'concepts',
    }


def iso(value: datetime) -> str:
    return value.isoformat().replace('+00:00', 'Z')
