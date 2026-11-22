from unittest.mock import create_autospec

from inngest import Inngest

from shifu.identity.core.domain.events import AccountDeletedEvent
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases import PurgePracticePhotosUseCase
from shifu.learning.messaging.inngest.learning_inngest_messaging import (
    LearningInngestMessaging,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider


def test_register_jobs_returns_the_learning_handlers() -> None:
    functions = LearningInngestMessaging.register_jobs(
        Inngest(app_id='learning-tests'),
        learning_database=create_autospec(LearningDatabase, instance=True),
        clock_provider=create_autospec(ClockProvider, instance=True),
        curriculum_content_provider=create_autospec(
            CurriculumContentProvider,
            instance=True,
        ),
        purge_practice_photos_use_case=create_autospec(
            PurgePracticePhotosUseCase, instance=True
        ),
        account_deleted_event_name=AccountDeletedEvent.EVENT_NAME,
        telemetry_provider=create_autospec(TelemetryProvider, instance=True),
    )

    assert len(functions) == 3
