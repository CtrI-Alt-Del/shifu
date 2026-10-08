from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.gamification.core.interfaces import GamificationDatabaseRepositories
from shifu.gamification.database.sqlalchemy.repositories import (
    SqlalchemyEarnedAchievementsRepository,
    SqlalchemyGamificationProfilesRepository,
    SqlalchemyRewardedMilestonesRepository,
    SqlalchemyXpGrantsRepository,
)
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class SqlalchemyGamificationDatabase:
    def __init__(
        self,
        engine: Engine | None = None,
        id_provider: IdentifierProvider | None = None,
    ) -> None:
        self._engine: Engine = engine or Session.create_database_engine()
        self._id_provider: IdentifierProvider = (
            id_provider or SystemIdentifierProvider()
        )

    @contextmanager
    def transaction(self) -> Generator[GamificationDatabaseRepositories]:
        with SqlalchemySession(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            repositories = GamificationDatabaseRepositories(
                profiles=SqlalchemyGamificationProfilesRepository(session),
                xp_grants=SqlalchemyXpGrantsRepository(session),
                earned_achievements=SqlalchemyEarnedAchievementsRepository(session),
                rewarded_milestones=SqlalchemyRewardedMilestonesRepository(session),
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
