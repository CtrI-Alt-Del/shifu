from typing import cast

from inngest import Function, Inngest

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import PurgeLearningDataForAccountUseCase
from shifu.learning.messaging.inngest.jobs import (
    EvaluateChoiceActivityJob,
    PurgeLearningDataOnAccountErasureJob,
)
from shifu.shared.core.interfaces import (
    AccountErasureAcknowledgementProvider,
    AccountErasureTargetProvider,
    ClockProvider,
    CurriculumContentProvider,
)
from shifu.shared.core.interfaces.account_activity_provider import (
    AccountActivityProvider,
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
        account_activity_provider: AccountActivityProvider,
        account_erasure_target_provider: AccountErasureTargetProvider,
        account_erasure_acknowledgement_provider: AccountErasureAcknowledgementProvider,
        curriculum_content_provider: CurriculumContentProvider | None = None,
        max_code_assessment_input_bytes: int = 262144,
        telemetry_provider: TelemetryProvider,
    ) -> list[Function[object]]:
        return [
            cast(
                'Function[object]',
                EvaluateChoiceActivityJob.handle(
                    inngest,
                    learning_database,
                    clock_provider,
                    account_activity_provider=account_activity_provider,
                    curriculum_content_provider=curriculum_content_provider,
                    max_code_assessment_input_bytes=max_code_assessment_input_bytes,
                    telemetry_provider=telemetry_provider,
                ),
            ),
            cast(
                'Function[object]',
                PurgeLearningDataOnAccountErasureJob.handle(
                    inngest,
                    PurgeLearningDataForAccountUseCase(learning_database),
                    target_provider=account_erasure_target_provider,
                    acknowledgement_provider=account_erasure_acknowledgement_provider,
                    telemetry_provider=telemetry_provider,
                ),
            ),
        ]
