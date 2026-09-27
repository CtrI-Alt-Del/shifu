from typing import cast
from collections.abc import Callable

from inngest import Function, Inngest

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.messaging.inngest.jobs import EvaluateChoiceActivityJob
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    CodeRubricAssessorProvider,
)


class LearningInngestMessaging:
    """Declare the Inngest functions owned by Learning."""

    @staticmethod
    def register_jobs(
        inngest: Inngest,
        *,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
        curriculum_content_provider: CurriculumContentProvider | None = None,
        code_rubric_assessor_provider_factory: Callable[[], CodeRubricAssessorProvider]
        | None = None,
        max_code_assessment_input_bytes: int = 262144,
    ) -> list[Function[object]]:
        return [
            cast(
                'Function[object]',
                EvaluateChoiceActivityJob.handle(
                    inngest,
                    learning_database,
                    clock_provider,
                    curriculum_content_provider,
                    code_rubric_assessor_provider_factory,
                    max_code_assessment_input_bytes,
                ),
            ),
        ]
