from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.orm import Session as SqlalchemySession

from shifu.communication.database import CommunicationSeeder
from shifu.communication.database.sqlalchemy.repositories import (
    SqlalchemyCommunicationsRepository,
    SqlalchemyDeliveryAttemptsRepository,
)
from shifu.curriculum.database import CurriculumSeeder
from shifu.curriculum.database.sqlalchemy.repositories import (
    SqlalchemyActivitiesRepository,
    SqlalchemyCompetenciesRepository,
    SqlalchemyConceptsRepository,
    SqlalchemyCurriculumSequencesRepository,
    SqlalchemyMaterialsRepository,
    SqlalchemySkillFoundationsRepository,
    SqlalchemySkillsRepository,
)
from shifu.identity.database import IdentitySeeder
from shifu.identity.database.sqlalchemy.repositories import (
    SqlalchemyAccountActionTokensRepository,
    SqlalchemyAccountsRepository,
)
from shifu.learning.database import LearningSeeder
from shifu.learning.database.sqlalchemy.repositories import (
    SqlalchemyActivityAttemptsRepository,
    SqlalchemyActivityEvaluationsRepository,
    SqlalchemyCompetencyProgressesRepository,
    SqlalchemyGoalsRepository,
    SqlalchemySkillExperiencesRepository,
)
from shifu.shared.database.seed_data import DevelopmentSeed, build_development_seed
from shifu.shared.database.sqlalchemy.repositories import SqlalchemyEventsRepository
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.database.sqlalchemy.settings import DatabaseSettings, SeedSettings


class SeedOrchestrator:
    def __init__(
        self,
        identity_seeder: IdentitySeeder,
        curriculum_seeder: CurriculumSeeder,
        learning_seeder: LearningSeeder,
        communication_seeder: CommunicationSeeder,
        events_repository: SqlalchemyEventsRepository,
    ) -> None:
        self._identity_seeder = identity_seeder
        self._curriculum_seeder = curriculum_seeder
        self._learning_seeder = learning_seeder
        self._communication_seeder = communication_seeder
        self._events_repository = events_repository

    def clear(self) -> None:
        self._events_repository.remove_all()
        self._communication_seeder.clear()
        self._learning_seeder.clear()
        self._identity_seeder.clear()
        self._curriculum_seeder.clear()

    def run(self, seed: DevelopmentSeed | None = None) -> None:
        development_seed = seed or build_development_seed()

        self.clear()
        self._identity_seeder.run(
            list(development_seed.accounts),
            list(development_seed.account_action_tokens),
        )
        self._curriculum_seeder.run(
            list(development_seed.skills),
            list(development_seed.skill_foundations),
            list(development_seed.competencies),
            list(development_seed.concepts),
            list(development_seed.materials),
            list(development_seed.activities),
            list(development_seed.curriculum_sequences),
        )
        self._learning_seeder.run(
            list(development_seed.goals),
            list(development_seed.skill_experiences),
            list(development_seed.competency_progresses),
            list(development_seed.activity_attempts),
            list(development_seed.activity_evaluations),
        )
        self._communication_seeder.run(
            list(development_seed.communications),
            list(development_seed.delivery_attempts),
        )


def _require_current_schema(session: SqlalchemySession) -> None:
    config = Config()
    config.set_main_option(
        'script_location',
        str(Path(__file__).resolve().parents[4] / 'migrations'),
    )
    expected_heads = set(ScriptDirectory.from_config(config).get_heads())
    current_heads = set(
        MigrationContext.configure(session.connection()).get_current_heads()
    )
    if current_heads != expected_heads:
        current = ', '.join(sorted(current_heads)) or 'none'
        expected = ', '.join(sorted(expected_heads))
        raise RuntimeError(
            f'Database schema is at {current}; seed requires {expected}. '
            'Run `uv run poe db:upgrade` from apps/server first.'
        )


def seed() -> None:
    settings = SeedSettings.from_environment()
    if settings.server_app_mode != 'local':
        raise RuntimeError('Database seeding is only allowed in local mode.')

    with Session.database_session(
        engine=Session.create_database_engine(
            DatabaseSettings(url=settings.database_url)
        )
    ) as session:
        _require_current_schema(session)
        orchestrator = SeedOrchestrator(
            IdentitySeeder(
                SqlalchemyAccountsRepository(session),
                SqlalchemyAccountActionTokensRepository(session),
            ),
            CurriculumSeeder(
                SqlalchemySkillsRepository(session),
                SqlalchemySkillFoundationsRepository(session),
                SqlalchemyCompetenciesRepository(session),
                SqlalchemyConceptsRepository(session),
                SqlalchemyMaterialsRepository(session),
                SqlalchemyActivitiesRepository(session),
                SqlalchemyCurriculumSequencesRepository(session),
            ),
            LearningSeeder(
                SqlalchemyGoalsRepository(session),
                SqlalchemySkillExperiencesRepository(session),
                SqlalchemyCompetencyProgressesRepository(session),
                SqlalchemyActivityAttemptsRepository(session),
                SqlalchemyActivityEvaluationsRepository(session),
            ),
            CommunicationSeeder(
                SqlalchemyCommunicationsRepository(session),
                SqlalchemyDeliveryAttemptsRepository(session),
            ),
            SqlalchemyEventsRepository(session),
        )
        orchestrator.run()


if __name__ == '__main__':
    seed()
