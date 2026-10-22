from unittest.mock import create_autospec

from inngest import Inngest

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.messaging.inngest.learning_inngest_messaging import (
    LearningInngestMessaging,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


def test_register_jobs_returns_the_learning_evaluation_handler() -> None:
    functions = LearningInngestMessaging.register_jobs(
        Inngest(app_id='learning-tests'),
        learning_database=create_autospec(LearningDatabase, instance=True),
        clock_provider=create_autospec(ClockProvider, instance=True),
        curriculum_content_provider=create_autospec(
            CurriculumContentProvider,
            instance=True,
        ),
    )

    assert len(functions) == 1
