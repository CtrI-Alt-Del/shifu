from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session as SqlalchemySession, sessionmaker

from shifu.shared.database.sqlalchemy.settings import DatabaseSettings


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
        session_factory = sessionmaker(
            bind=database_engine,
            autoflush=False,
            expire_on_commit=False,
        )
        with session_factory() as session:
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise
