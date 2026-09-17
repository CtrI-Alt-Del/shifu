from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.identity.core.interfaces import IdentityDatabaseRepositories
from shifu.identity.database.sqlalchemy.repositories import (
    SqlalchemyAccountActionTokensRepository,
    SqlalchemyAccountsRepository,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class SqlalchemyIdentityDatabase:
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
    def transaction(self) -> Generator[IdentityDatabaseRepositories]:
        with SqlalchemySession(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            repositories = IdentityDatabaseRepositories(
                accounts=SqlalchemyAccountsRepository(session),
                account_action_tokens=SqlalchemyAccountActionTokensRepository(session),
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
