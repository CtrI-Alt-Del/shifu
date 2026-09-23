from typing import cast

from inngest import Function, Inngest

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.messaging.inngest.jobs import EvaluateChoiceActivityJob
from shifu.shared.core.interfaces import ClockProvider


class LearningInngestMessaging:
    """Declare the Inngest functions owned by Learning."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
    ) -> list[Function[object]]:
        return [
            cast(
                'Function[object]',
                EvaluateChoiceActivityJob.handle(
                    inngest,
                    learning_database,
                    clock_provider,
                ),
            ),
        ]
