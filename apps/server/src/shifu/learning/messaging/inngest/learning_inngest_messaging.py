from typing import cast

from inngest import Function, Inngest

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import PurgePracticePhotosUseCase
from shifu.learning.messaging.inngest.jobs import (
    EvaluateChoiceActivityJob,
    PurgePracticeDataOnAccountDeletedJob,
    PurgePracticePhotoJob,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
)
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider


class LearningInngestMessaging:
    """Declare the Inngest functions owned by Learning."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
        curriculum_content_provider: CurriculumContentProvider | None = None,
        max_code_assessment_input_bytes: int = 262144,
        purge_practice_photos_use_case: PurgePracticePhotosUseCase,
        account_deleted_event_name: str,
        telemetry_provider: TelemetryProvider,
    ) -> list[Function[object]]:
        return [
            cast(
                'Function[object]',
                EvaluateChoiceActivityJob.handle(
                    inngest,
                    learning_database,
                    clock_provider,
                    curriculum_content_provider=curriculum_content_provider,
                    max_code_assessment_input_bytes=max_code_assessment_input_bytes,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgePracticePhotoJob.handle(
                    inngest,
                    purge_practice_photos_use_case,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgePracticeDataOnAccountDeletedJob.handle(
                    inngest,
                    purge_practice_photos_use_case,
                    account_deleted_event_name=account_deleted_event_name,
                    telemetry_provider=telemetry_provider,
                ),
            ),
        ]
