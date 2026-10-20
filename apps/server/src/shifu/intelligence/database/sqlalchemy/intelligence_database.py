from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.intelligence.core.interfaces import IntelligenceDatabaseRepositories
from shifu.intelligence.database.sqlalchemy.repositories import (
    SqlalchemyMentorAttachmentBatchesRepository,
    SqlalchemyMentorAttachmentChunksRepository,
    SqlalchemyMentorAttachmentsRepository,
    SqlalchemyMentorMessagesRepository,
    SqlalchemyMentorResponseAttemptsRepository,
    SqlalchemyMentorResponseEventsRepository,
    SqlalchemyMentorSessionsRepository,
    SqlalchemyPlanningSessionsRepository,
)
from shifu.intelligence.database.sqlalchemy.repositories.planning_embeddings_repository import (
    SqlalchemyPlanningEmbeddingsRepository,
)
from shifu.intelligence.database.sqlalchemy.repositories.mentor_embeddings_repository import (
    SqlalchemyMentorEmbeddingsRepository,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class SqlalchemyIntelligenceDatabase:
    def __init__(
        self,
        engine: Engine | None = None,
        id_provider: IdentifierProvider | None = None,
    ) -> None:
        self._engine = engine or Session.create_database_engine()
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )

    @contextmanager
    def transaction(self) -> Generator[IntelligenceDatabaseRepositories]:
        with SqlalchemySession(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            repositories = IntelligenceDatabaseRepositories(
                planning_sessions=SqlalchemyPlanningSessionsRepository(session),
                planning_embeddings=SqlalchemyPlanningEmbeddingsRepository(session),
                events=SqlalchemyEventsRepository(
                    session,
                    self._engine,
                    id_provider=self._id_provider,
                ),
                mentor_sessions=SqlalchemyMentorSessionsRepository(session),
                mentor_embeddings=SqlalchemyMentorEmbeddingsRepository(session),
                mentor_messages=SqlalchemyMentorMessagesRepository(session),
                mentor_response_attempts=SqlalchemyMentorResponseAttemptsRepository(
                    session
                ),
                mentor_response_events=SqlalchemyMentorResponseEventsRepository(
                    session
                ),
                mentor_attachment_batches=SqlalchemyMentorAttachmentBatchesRepository(
                    session
                ),
                mentor_attachments=SqlalchemyMentorAttachmentsRepository(session),
                mentor_attachment_chunks=SqlalchemyMentorAttachmentChunksRepository(
                    session
                ),
            )
            try:
                yield repositories
                session.commit()
            except BaseException:
                session.rollback()
                raise
