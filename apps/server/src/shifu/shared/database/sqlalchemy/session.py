from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from shifu.shared.database.sqlalchemy.settings import DatabaseSettings


def create_database_engine(settings: DatabaseSettings | None = None) -> Engine:
    database_settings = settings or DatabaseSettings.from_environment()
    return create_engine(database_settings.url, pool_pre_ping=True)


@contextmanager
def database_session(
    engine: Engine | None = None,
) -> Generator[Session]:
    database_engine = engine or create_database_engine()
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
