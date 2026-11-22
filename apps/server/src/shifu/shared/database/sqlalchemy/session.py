from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session as SqlalchemySession, sessionmaker

from shifu.shared.database.sqlalchemy.account_activity_scope import (
    AccountActivityScope,
)
from shifu.shared.database.sqlalchemy.settings import DatabaseSettings

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection


class Session:
    @staticmethod
    def create_database_engine(settings: DatabaseSettings | None = None) -> Engine:
        database_settings = settings or DatabaseSettings.from_environment()
        return create_engine(database_settings.url, pool_pre_ping=True)

    @staticmethod
    @contextmanager
    def database_session(
        engine: Engine | None = None,
    ) -> Generator[SqlalchemySession]:
        database_engine = engine or Session.create_database_engine()
        connection: Connection | None = AccountActivityScope.current_connection(
            database_engine
        )
        session_factory = sessionmaker(
            bind=connection or database_engine,
            autoflush=False,
            expire_on_commit=False,
        )
        with session_factory() as session:
            try:
                with AccountActivityScope.serialize_session_use(connection):
                    yield session
                    session.commit()
            except BaseException:
                session.rollback()
                raise
