from unittest.mock import create_autospec

from inngest import Inngest

from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.messaging.inngest.learning_inngest_messaging import (
    LearningInngestMessaging,
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


def test_register_jobs_returns_the_learning_evaluation_handler() -> None:
    functions = LearningInngestMessaging.register_jobs(
        Inngest(app_id='learning-tests'),
        learning_database=create_autospec(LearningDatabase, instance=True),
        clock_provider=create_autospec(ClockProvider, instance=True),
        account_activity_provider=create_autospec(
            AccountActivityProvider,
            instance=True,
        ),
        account_erasure_target_provider=create_autospec(
            AccountErasureTargetProvider,
            instance=True,
        ),
        account_erasure_acknowledgement_provider=create_autospec(
            AccountErasureAcknowledgementProvider,
            instance=True,
        ),
        curriculum_content_provider=create_autospec(
            CurriculumContentProvider,
            instance=True,
        ),
        telemetry_provider=create_autospec(TelemetryProvider, instance=True),
    )

    assert len(functions) == 2
