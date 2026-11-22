from dataclasses import field
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class PracticePhotoCleanupRequestedPayload:
    photo_id: str
    object_key: str


@structure
class PracticePhotoCleanupRequestedEvent(Event[PracticePhotoCleanupRequestedPayload]):
    EVENT_NAME: ClassVar[str] = 'learning/practice-photo.cleanup.requested'
    name: str = field(default=EVENT_NAME, init=False)
