from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.communication.core.interfaces import CommunicationDatabaseRepositories
from shifu.communication.database.sqlalchemy.repositories import (
    SqlalchemyCommunicationsRepository,
    SqlalchemyDeliveryAttemptsRepository,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class SqlalchemyCommunicationDatabase:
    """Own one Communication transaction and all repositories in that transaction."""

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
    def transaction(self) -> Generator[CommunicationDatabaseRepositories]:
        with SqlalchemySession(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            repositories = CommunicationDatabaseRepositories(
                communications=SqlalchemyCommunicationsRepository(session),
                delivery_attempts=SqlalchemyDeliveryAttemptsRepository(session),
                events=SqlalchemyEventsRepository(
                    session,
                    self._engine,
                    id_provider=self._id_provider,
                ),
            )
            try:
                yield repositories
                session.commit()
            except BaseException:
                session.rollback()
                raise
