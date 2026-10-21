from dataclasses import field

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentPreparationRequestedPayload:
    attachment_id: str
    generation: int


@structure
class MentorAttachmentPreparationRequestedEvent(
    Event[MentorAttachmentPreparationRequestedPayload]
):
    name: str = field(
        default='intelligence/mentor-attachment.preparation.requested', init=False
    )
