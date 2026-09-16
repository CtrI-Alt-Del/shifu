from shifu.communication.database import CommunicationSeeder
from shifu.communication.database.sqlalchemy.repositories import (
    SqlalchemyCommunicationsRepository,
    SqlalchemyDeliveryAttemptsRepository,
)
from shifu.curriculum.database import CurriculumSeeder
from shifu.curriculum.database.sqlalchemy.repositories import (
    SqlalchemyActivitiesRepository,
    SqlalchemyCompetenciesRepository,
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
from shifu.composition.seed_data import DevelopmentSeed, build_development_seed
from shifu.shared.database.sqlalchemy.session import (
    create_database_engine,
    database_session,
)
from shifu.shared.database.sqlalchemy.settings import DatabaseSettings, SeedSettings


class SeedOrchestrator:
    def __init__(
        self,
        identity_seeder: IdentitySeeder,
        curriculum_seeder: CurriculumSeeder,
        learning_seeder: LearningSeeder,
        communication_seeder: CommunicationSeeder,
    ) -> None:
        self._identity_seeder = identity_seeder
        self._curriculum_seeder = curriculum_seeder
        self._learning_seeder = learning_seeder
        self._communication_seeder = communication_seeder

    def clear(self) -> None:
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


def seed() -> None:
    settings = SeedSettings.from_environment()
    if settings.server_app_mode != 'local':
        raise RuntimeError('Database seeding is only allowed in local mode.')

    with database_session(
        engine=create_database_engine(DatabaseSettings(url=settings.database_url))
    ) as session:
        orchestrator = SeedOrchestrator(
            IdentitySeeder(
                SqlalchemyAccountsRepository(session),
                SqlalchemyAccountActionTokensRepository(session),
            ),
            CurriculumSeeder(
                SqlalchemySkillsRepository(session),
                SqlalchemySkillFoundationsRepository(session),
                SqlalchemyCompetenciesRepository(session),
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
        )
        orchestrator.run()


if __name__ == '__main__':
    seed()
