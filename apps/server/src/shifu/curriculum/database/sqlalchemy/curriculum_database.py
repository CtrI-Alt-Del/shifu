from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.curriculum.core.interfaces import CurriculumDatabaseRepositories
from shifu.curriculum.database.sqlalchemy.repositories import (
    SqlalchemyActivitiesRepository,
    SqlalchemyCompetenciesRepository,
    SqlalchemyConceptsRepository,
    SqlalchemyCurriculumSequencesRepository,
    SqlalchemyMaterialsRepository,
    SqlalchemySkillFoundationsRepository,
    SqlalchemySkillsRepository,
)
from shifu.shared.database.sqlalchemy.session import Session


class SqlalchemyCurriculumDatabase:
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine: Engine = engine or Session.create_database_engine()

    @contextmanager
    def transaction(self) -> Generator[CurriculumDatabaseRepositories]:
        with SqlalchemySession(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            repositories = CurriculumDatabaseRepositories(
                skills=SqlalchemySkillsRepository(session),
                skill_foundations=SqlalchemySkillFoundationsRepository(session),
                competencies=SqlalchemyCompetenciesRepository(session),
                concepts=SqlalchemyConceptsRepository(session),
                materials=SqlalchemyMaterialsRepository(session),
                activities=SqlalchemyActivitiesRepository(session),
                curriculum_sequences=SqlalchemyCurriculumSequencesRepository(session),
            )
            try:
                yield repositories
                session.commit()
            except BaseException:
                session.rollback()
                raise
