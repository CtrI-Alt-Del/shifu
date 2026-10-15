from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentCleanupRequestedPayload:
    account_id: str
    session_id: str | None
    batch_id: str | None
    deletion_generation: int


@structure
class MentorAttachmentCleanupRequestedEvent(
    Event[MentorAttachmentCleanupRequestedPayload]
):
    name: str = field(
        default='intelligence/mentor-attachment.cleanup.requested', init=False
    )
