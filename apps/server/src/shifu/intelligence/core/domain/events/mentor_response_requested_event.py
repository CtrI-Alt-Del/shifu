from dataclasses import field
from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class MentorResponseRequestedPayload:
    attempt_id: str


@structure
class MentorResponseRequestedEvent(Event[MentorResponseRequestedPayload]):
    name: str = field(default='intelligence/mentor.response.requested', init=False)
