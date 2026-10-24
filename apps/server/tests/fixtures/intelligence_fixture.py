"""Intelligence HTTP test support: a configured Mentor application, stubbed AI
and storage boundaries, and seeding helpers bound to the disposable PostgreSQL
database. Nothing here reaches a model; the AgentOS fixture owns that path."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, create_autospec
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from shifu.app import FastAPIApp
from shifu.fakers.identity.entities.account_faker import AccountFaker
from shifu.fakers.intelligence.entities import MentorActionProposalFaker
from shifu.identity.database.sqlalchemy.identity_database import (
    SqlalchemyIdentityDatabase,
)
from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    LearnerMemoryChange,
    MentorMessage,
    MentorSession,
    MentorSessionSummary,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    LearnerMemoryChangeKind,
    MentorActionKind,
    MentorActionProposalStatus,
    MentorMessageRole,
    MentorResponseEventKind,
    MentorResponseStatus,
    MentorSummaryExcerptKind,
)
from shifu.intelligence.core.use_cases.mentor_detail import mentor_action_item
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryConcept,
    LearnerMemoryOrigin,
    MentorAttachmentExtraction,
    MentorConversationSummaryDraft,
    MentorResponseBlock,
    MentorResponseEvent,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
)
from shifu.intelligence.core.use_cases import FinalizeMentorResponseUseCase
from shifu.intelligence.database.sqlalchemy import SqlalchemyIntelligenceDatabase
from shifu.intelligence.pipes import IntelligencePipe
from shifu.shared.core.domain.structures import AuthenticatedUser, MentorAccessGrant
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider
from shifu.shared.messaging.inngest.inngest_broker import InngestBroker
from shifu.shared.pipes import FileStoragePipe, SharedPipe
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider

if TYPE_CHECKING:
    from collections.abc import Generator
    from fastapi import FastAPI

    from shifu.intelligence.core.domain.entities import MentorActionProposal

    from shifu.identity.core.domain.enums import AccountStatus
    from shifu.intelligence.core.domain.enums import (
        MentorSummaryFailureCode,
        MentorWorkflowStep,
    )
    from shifu.intelligence.core.interfaces import IntelligenceDatabaseRepositories
    from tests.fixtures.postgres_fixture import PostgresDatabase

MENTOR_ACCOUNT = AuthenticatedUser(
    account_id='01JACCOUNT000000000000TEST',
    display_name='Learner Test',
    time_zone=None,
)
OTHER_ACCOUNT = AuthenticatedUser(
    account_id='01JOTHER000000000000TEST',
    display_name='Other Learner',
    time_zone=None,
)
BASE_TIME = datetime(2026, 3, 1, 12, tzinfo=UTC)
ABSENT_MEMORY_ID = '01J00000000000000000000999'
LEARNER_TEXT = 'Meu laço não mostra o último item da lista.'
MENTOR_TEXT = 'Veja quais índices range produz e compare com o tamanho da lista.'
FIRST_TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)
_IDENTIFIERS = SystemIdentifierProvider()


class MentorTitleProviderStub:
    def generate(self, first_message: str) -> str:
        del first_message
        return 'Conversa de teste'


class MentorAttachmentStorageStub:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def put(self, object_key: str, content: bytes, media_type: str) -> None:
        self.objects[object_key] = (content, media_type)

    def read(self, object_key: str) -> bytes:
        return self.objects[object_key][0]

    def remove(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


class MentorAttachmentExtractorStub:
    def validate(self, content: bytes, media_type: str) -> None:
        del content, media_type

    def extract(
        self, content: bytes, media_type: str, attachment_id: str, generation: int
    ) -> MentorAttachmentExtraction:
        del content, media_type, attachment_id, generation
        return MentorAttachmentExtraction(
            chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
        )

    def render_visual_pages(
        self, content: bytes, media_type: str, page_numbers: tuple[int, ...]
    ) -> tuple[tuple[int, bytes], ...]:
        del content, media_type, page_numbers
        return ()


def configure_mentor_access(app: FastAPI) -> Mock:
    access = create_autospec(MentorAccessProvider, instance=True)

    def grant(account_id: str, operation_key: str) -> MentorAccessGrant:
        return MentorAccessGrant(
            account_id=account_id,
            access_revision='controlled-test-revision',
            operation_key=operation_key,
        )

    access.authorize.side_effect = grant
    app.dependency_overrides[IntelligencePipe.get_mentor_access_provider] = lambda: (
        access
    )
    return access


def memory_id(number: int) -> str:
    """A valid, ordered ULID-shaped memory id."""
    return f'01J00000000000000000000{number:03d}'


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


@dataclass(frozen=True)
class IntelligenceFixture:
    """Seeds Intelligence rows and builds Mentor applications on one database."""

    postgres: PostgresDatabase

    @property
    def database(self) -> SqlalchemyIntelligenceDatabase:
        return SqlalchemyIntelligenceDatabase(engine=self.postgres.engine)

    # Applications

    def mentor_app(self, account: AuthenticatedUser = MENTOR_ACCOUNT) -> FastAPI:
        """The Mentor application with controlled access and a stubbed title."""
        app = FastAPIApp.register(self.postgres.engine)
        configure_mentor_access(app)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: account
        app.dependency_overrides[
            IntelligencePipe.get_generate_mentor_title_provider
        ] = MentorTitleProviderStub
        return app

    @contextmanager
    def other_account_client(self) -> Generator[TestClient]:
        """A second application whose authenticated learner is another account."""
        app = self.mentor_app(OTHER_ACCOUNT)
        with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
            yield client

    @contextmanager
    def real_access_client(self, account_id: str) -> Generator[TestClient]:
        """An application using the real Identity access check for ``account_id``."""
        app = FastAPIApp.register(self.postgres.engine)
        app.dependency_overrides[SharedPipe.get_authenticated_user] = lambda: (
            AuthenticatedUser(
                account_id=account_id, display_name='Learner', time_zone=None
            )
        )
        with TestClient(app, headers={'Authorization': 'Bearer synthetic'}) as client:
            yield client

    # Accounts

    def create_account(self, status: AccountStatus) -> str:
        """Persist an Identity account in ``status`` and return its id."""
        account = AccountFaker.fake(status=status)
        with SqlalchemyIdentityDatabase(
            engine=self.postgres.engine
        ).transaction() as repositories:
            repositories.accounts.add(account)
        return account.id

    # Mentor responses

    def create_session(
        self,
        client: TestClient,
        submission_key: str = '123e4567-e89b-42d3-a456-426614174000',
    ) -> tuple[str, str, str]:
        response = client.post(
            '/intelligence/mentor-sessions',
            json={
                'submission_key': submission_key,
                'first_message': 'Pergunta inicial',
            },
        )
        assert response.status_code == 201
        body = response.json()
        return (
            body['session']['id'],
            body['response']['attempt_id'],
            body['pending_learner_message_id'],
        )

    def start_processing(self, attempt_id: str) -> None:
        """Claim and move a queued attempt to processing like the answer workflow."""
        now = datetime.now(UTC)
        with self.database.transaction() as repositories:
            self._claim(repositories, attempt_id, now)

    def append_status(
        self, session_id: str, attempt_id: str, progress: MentorWorkflowStep | None
    ) -> None:
        """Append a processing status event; ``None`` is the closing event."""
        with self.database.transaction() as repositories:
            repositories.mentor_response_events.append(
                self._status_event(
                    repositories, session_id, attempt_id, datetime.now(UTC), progress
                )
            )

    def complete_response(
        self,
        session_id: str,
        attempt_id: str,
        message_id: str,
        progress: tuple[MentorWorkflowStep | None, ...] = (),
    ) -> None:
        """Process the attempt, publish one approved block and finalize it."""
        intelligence = self.database
        now = datetime.now(UTC)
        with intelligence.transaction() as repositories:
            self._claim(repositories, attempt_id, now)
            for step in progress:
                repositories.mentor_response_events.append(
                    self._status_event(repositories, session_id, attempt_id, now, step)
                )
            block = MentorResponseBlock(
                block_key='synthetic-approved',
                ordinal=0,
                intent=None,
                content='Resposta sintética aprovada.',
            )
            repositories.mentor_response_events.append(
                MentorResponseEvent(
                    session_id=session_id,
                    attempt_id=attempt_id,
                    sequence=repositories.mentor_response_events.next_sequence(
                        session_id
                    ),
                    kind=MentorResponseEventKind.BLOCK,
                    status=MentorResponseStatus.PROCESSING,
                    block=block,
                    consultation=None,
                    failure_code=None,
                    created_at=now,
                )
            )
        access = create_autospec(MentorAccessProvider, instance=True)
        clock = create_autospec(ClockProvider, instance=True)
        clock.now.return_value = now
        assert FinalizeMentorResponseUseCase(
            intelligence, SystemIdentifierProvider(), clock, access
        ).execute(
            MENTOR_ACCOUNT.account_id,
            session_id,
            message_id,
            'Resposta sintética aprovada.',
            attempt_id,
            'test-owner',
        )

    # Mentor action proposals

    def seed_action_proposal(
        self,
        session_id: str,
        attempt_id: str,
        message_id: str,
        *,
        account_id: str = MENTOR_ACCOUNT.account_id,
        kind: MentorActionKind = MentorActionKind.ADD_SKILL,
        status: MentorActionProposalStatus = MentorActionProposalStatus.PENDING,
        event_status: MentorResponseStatus = MentorResponseStatus.PROCESSING,
        **changes: Any,
    ) -> MentorActionProposal:
        """Persist a proposal and the `action` event that announced it.

        Extra keyword arguments override the faker defaults (outcome, candidates...).
        """
        proposal = MentorActionProposalFaker.fake(
            account_id=account_id,
            session_id=session_id,
            learner_message_id=message_id,
            attempt_id=attempt_id,
            kind=kind,
            status=status,
            **changes,
        )
        with self.database.transaction() as repositories:
            repositories.mentor_action_proposals.add(proposal)
            repositories.mentor_response_events.append(
                MentorResponseEvent(
                    session_id=session_id,
                    attempt_id=attempt_id,
                    sequence=repositories.mentor_response_events.next_sequence(
                        session_id
                    ),
                    kind=MentorResponseEventKind.ACTION,
                    status=event_status,
                    block=None,
                    consultation=None,
                    failure_code=None,
                    created_at=datetime.now(UTC),
                    action_proposal=mentor_action_item(proposal),
                )
            )
        return proposal

    def read_action_proposals(
        self, session_id: str, account_id: str = MENTOR_ACCOUNT.account_id
    ) -> list[MentorActionProposal]:
        with self.database.transaction() as repositories:
            return repositories.mentor_action_proposals.find_many_by_session(
                account_id, session_id
            )

    # Summaries

    def seed_exchanges(
        self, session_id: str, exchanges: int
    ) -> tuple[MentorMessage, ...]:
        """Persist answered learner/Mentor pairs with controlled, ordered timestamps."""
        messages: list[MentorMessage] = []
        with self.database.transaction() as repositories:
            for index in range(exchanges):
                learner = MentorMessage(
                    id=_IDENTIFIERS.generate(),
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content=LEARNER_TEXT if index == 0 else f'Pergunta {index}.',
                    created_at=FIRST_TIMESTAMP + timedelta(minutes=index * 2),
                    in_reply_to_message_id=None,
                )
                mentor = MentorMessage(
                    id=_IDENTIFIERS.generate(),
                    session_id=session_id,
                    role=MentorMessageRole.MENTOR,
                    content=MENTOR_TEXT if index == 0 else f'Resposta {index}.',
                    created_at=FIRST_TIMESTAMP + timedelta(minutes=index * 2 + 1),
                    in_reply_to_message_id=learner.id,
                )
                repositories.mentor_messages.add(learner)
                repositories.mentor_messages.add(mentor)
                messages.extend((learner, mentor))
        return tuple(messages)

    def seed_summary(
        self,
        session_id: str,
        attempt_id: str,
        messages: tuple[MentorMessage, ...],
        *,
        version: int = 1,
        failure: MentorSummaryFailureCode | None = None,
        account_id: str = MENTOR_ACCOUNT.account_id,
    ) -> MentorSessionSummary:
        """Persist a ready (or failed) summary bounded by the last given message."""
        last = messages[-1]
        completed_at = FIRST_TIMESTAMP + timedelta(days=1)
        started = MentorSessionSummary.start(
            id=_IDENTIFIERS.generate(),
            account_id=account_id,
            session_id=session_id,
            attempt_id=attempt_id,
            version=version,
            boundary=MentorSummaryBoundary(
                message_id=last.id, created_at=last.created_at
            ),
            covered_message_count=len(messages),
            first_message_id=messages[0].id,
            now=completed_at,
        )
        if failure is not None:
            summary = started.fail(failure, completed_at)
        else:
            summary = started.complete(
                MentorConversationSummaryDraft(
                    topics=('range', 'lista'),
                    excerpts=(
                        MentorSummaryExcerptSpan(
                            message_id=messages[0].id,
                            start=0,
                            end=len(LEARNER_TEXT),
                            kind=MentorSummaryExcerptKind.DOUBT,
                        ),
                        MentorSummaryExcerptSpan(
                            message_id=messages[1].id,
                            start=0,
                            end=len(MENTOR_TEXT),
                            kind=MentorSummaryExcerptKind.GUIDANCE,
                        ),
                    ),
                    algorithm_version='textrank-v1',
                ),
                completed_at,
            )
        with self.database.transaction() as repositories:
            repositories.mentor_session_summaries.add(summary)
        return summary

    def count_summaries(self, session_id: str) -> int:
        from sqlalchemy import func, select
        from sqlalchemy.orm import Session

        from shifu.intelligence.database.sqlalchemy.models import (
            MentorSessionSummaryModel,
        )

        with Session(self.postgres.engine) as session:
            return (
                session.scalar(
                    select(func.count()).where(
                        MentorSessionSummaryModel.session_id == session_id
                    )
                )
                or 0
            )

    # Learner memories

    def seed_conversation(
        self,
        account_id: str = MENTOR_ACCOUNT.account_id,
        *,
        title: str = 'Conversa de memórias',
        content: str = 'Prefiro exemplos em Python.',
        created_at: datetime = BASE_TIME,
    ) -> tuple[str, str]:
        """Persist an owned conversation with one learner message."""
        session_id, message_id = _IDENTIFIERS.generate(), _IDENTIFIERS.generate()
        with self.database.transaction() as repositories:
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
        self,
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
            origins = (self.seed_conversation(account_id),)
        first, *others = origins
        with self.database.transaction() as repositories:
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
        self,
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
        with self.database.transaction() as repositories:
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
        self, account_id: str = MENTOR_ACCOUNT.account_id
    ) -> datetime | None:
        with self.database.transaction() as repositories:
            return repositories.learner_memories.lock_account(account_id)

    # Internals

    @staticmethod
    def _claim(
        repositories: IntelligenceDatabaseRepositories, attempt_id: str, now: datetime
    ) -> None:
        attempts = repositories.mentor_response_attempts
        attempt = attempts.find_by_id_for_update(attempt_id)
        assert attempt is not None
        assert attempts.claim(
            attempt_id,
            'test-owner',
            now,
            now + timedelta(minutes=5),
            attempt.access_revision,
        )
        assert attempts.transition(
            attempt_id,
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
            attempt.access_revision,
        )

    @staticmethod
    def _status_event(
        repositories: IntelligenceDatabaseRepositories,
        session_id: str,
        attempt_id: str,
        created_at: datetime,
        progress: MentorWorkflowStep | None,
    ) -> MentorResponseEvent:
        events = repositories.mentor_response_events
        return MentorResponseEvent(
            session_id=session_id,
            attempt_id=attempt_id,
            sequence=events.next_sequence(session_id),
            kind=MentorResponseEventKind.STATUS,
            status=MentorResponseStatus.PROCESSING,
            block=None,
            consultation=None,
            failure_code=None,
            created_at=created_at,
            progress=progress,
        )


@pytest.fixture
def intelligence_fixture(
    postgres_database: PostgresDatabase, monkeypatch: pytest.MonkeyPatch
) -> IntelligenceFixture:
    # HTTP tests assert real transactional outbox rows. Delivery is exercised by
    # disposable registered-job tests, never the shared development server.
    monkeypatch.setattr('shifu.app.InngestBroker', create_autospec(InngestBroker))
    return IntelligenceFixture(postgres_database)


@pytest.fixture
def mentor_client(intelligence_fixture: IntelligenceFixture) -> Generator[TestClient]:
    with TestClient(
        intelligence_fixture.mentor_app(),
        headers={'Authorization': 'Bearer test-token'},
    ) as client:
        yield client


@pytest.fixture
def mentor_attachment_client(
    intelligence_fixture: IntelligenceFixture,
) -> Generator[tuple[TestClient, MentorAttachmentStorageStub]]:
    app = intelligence_fixture.mentor_app()
    storage = MentorAttachmentStorageStub()
    extractor = MentorAttachmentExtractorStub()
    app.dependency_overrides[FileStoragePipe.get_file_storage_provider] = lambda: (
        storage
    )
    app.dependency_overrides[
        IntelligencePipe.get_mentor_attachment_extractor_provider
    ] = lambda: extractor
    with TestClient(app, headers={'Authorization': 'Bearer test-token'}) as client:
        yield client, storage
