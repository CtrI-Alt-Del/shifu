from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from shifu.curriculum.core.interfaces import CurriculumDatabase
from shifu.curriculum.database.sqlalchemy.repositories import (
	SqlalchemyActivitiesRepository,
	SqlalchemyCompetenciesRepository,
	SqlalchemyCurriculumSequencesRepository,
	SqlalchemyMaterialsRepository,
	SqlalchemySkillFoundationsRepository,
	SqlalchemySkillsRepository,
)


class CurriculumDatabaseRepositories:
	def __init__(self, session: Session) -> None:
		self.skills = SqlalchemySkillsRepository(session)
		self.skill_foundations = SqlalchemySkillFoundationsRepository(session)
		self.competencies = SqlalchemyCompetenciesRepository(session)
		self.materials = SqlalchemyMaterialsRepository(session)
		self.activities = SqlalchemyActivitiesRepository(session)
		self.curriculum_sequences = SqlalchemyCurriculumSequencesRepository(session)


class SqlalchemyCurriculumDatabase:
	def __init__(self, engine: Engine) -> None:
		self._session_factory = sessionmaker(bind=engine)

	@contextmanager
	def transaction(self) -> CurriculumDatabase:
		session = self._session_factory()
		try:
			yield CurriculumDatabaseRepositories(session)
			session.commit()
		except Exception:
			session.rollback()
			raise
		finally:
			session.close()
