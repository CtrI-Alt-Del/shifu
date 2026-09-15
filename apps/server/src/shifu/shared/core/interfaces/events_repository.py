from typing import Protocol

from shifu.shared.core.domain.events import Event


class EventsRepository(Protocol):
    def add[Payload](self, event: Event[Payload]) -> None: ...
