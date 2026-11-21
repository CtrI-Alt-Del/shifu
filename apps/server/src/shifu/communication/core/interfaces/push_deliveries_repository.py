from typing import Protocol

from shifu.communication.core.domain.entities import PushDelivery


class PushDeliveriesRepository(Protocol):
    def find_many_by_reminder_id(
        self, reminder_id: str
    ) -> tuple[PushDelivery, ...]: ...

    def try_add(self, delivery: PushDelivery) -> bool:
        """Insert the delivery; return False on a (reminder_id, subscription_id) conflict."""
        ...

    def update(self, delivery: PushDelivery) -> None: ...

    def remove(self, delivery: PushDelivery) -> None:
        """Release a reservation so the browser can be attempted again."""
        ...
