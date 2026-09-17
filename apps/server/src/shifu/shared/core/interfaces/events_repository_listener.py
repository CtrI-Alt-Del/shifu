from typing import Protocol


class EventsRepositoryListener(Protocol):
    def unlisten(self) -> None:
        """Stop listening and release the listener's database resources."""
        ...
