"""Declare the Inngest functions owned by Gamification."""

from typing import cast

from inngest import Function, Inngest

from shifu.gamification.core.interfaces import GamificationDatabase
from shifu.gamification.core.use_cases import (
    CreateGamificationProfileUseCase,
    DeleteGamificationProfileUseCase,
    GrantXpUseCase,
    RecognizeCompetencyMasteredUseCase,
    RecognizeDiagnosticCompletedUseCase,
    RecognizeSkillCompletedUseCase,
)
from shifu.gamification.messaging.inngest.jobs import (
    CreateProfileOnAccountActivatedJob,
    PurgeProfileOnAccountDeletedJob,
    RecognizeCompetencyMasteredJob,
    RecognizeDiagnosticCompletedJob,
    RecognizeSkillCompletedJob,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.core.interfaces import IdentifierProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider


class GamificationInngestMessaging:
    """Compose Gamification jobs without creating another HTTP endpoint."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        gamification_database: GamificationDatabase,
        curriculum_content_provider: CurriculumContentProvider,
        clock_provider: ClockProvider,
        id_provider: IdentifierProvider | None = None,
    ) -> list[Function[object]]:
        id_provider = id_provider or SystemIdentifierProvider()

        grant_xp_use_case = GrantXpUseCase(gamification_database, id_provider)
        create_profile_use_case = CreateGamificationProfileUseCase(
            gamification_database, id_provider
        )
        delete_profile_use_case = DeleteGamificationProfileUseCase(
            gamification_database
        )
        recognize_diagnostic_use_case = RecognizeDiagnosticCompletedUseCase(
            gamification_database,
            curriculum_content_provider,
            id_provider,
            grant_xp_use_case,
        )
        recognize_competency_use_case = RecognizeCompetencyMasteredUseCase(
            gamification_database,
            id_provider,
            grant_xp_use_case,
        )
        recognize_skill_use_case = RecognizeSkillCompletedUseCase(
            gamification_database,
            id_provider,
            grant_xp_use_case,
        )

        return [
            cast(
                'Function[object]',
                CreateProfileOnAccountActivatedJob.handle(
                    inngest,
                    create_profile_use_case,
                    clock_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgeProfileOnAccountDeletedJob.handle(
                    inngest,
                    delete_profile_use_case,
                ),
            ),
            cast(
                'Function[object]',
                RecognizeDiagnosticCompletedJob.handle(
                    inngest,
                    recognize_diagnostic_use_case,
                    clock_provider,
                ),
            ),
            cast(
                'Function[object]',
                RecognizeCompetencyMasteredJob.handle(
                    inngest,
                    recognize_competency_use_case,
                    clock_provider,
                ),
            ),
            cast(
                'Function[object]',
                RecognizeSkillCompletedJob.handle(
                    inngest,
                    recognize_skill_use_case,
                    clock_provider,
                ),
            ),
        ]
