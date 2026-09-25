from dataclasses import field

from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class ActivitySubmissionRequestedPayload:
    attempt_id: str
    run_id: str
    skill_experience_id: str
    activity_id: str
    kind: ActivityAttemptKind
    requested_at: str


@structure
class ActivitySubmissionRequestedEvent(Event[ActivitySubmissionRequestedPayload]):
    name: str = field(
        default='learning/activity-submission.requested',
        init=False,
    )
