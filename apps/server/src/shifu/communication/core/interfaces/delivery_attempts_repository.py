from typing import Protocol

from shifu.communication.core.domain.entities import DeliveryAttempt


class DeliveryAttemptsRepository(Protocol):
    def find_by_communication_id_and_attempt_number(
        self,
        communication_id: str,
        attempt_number: int,
    ) -> DeliveryAttempt | None: ...

    def add(self, attempt: DeliveryAttempt) -> None: ...

    def add_many(self, attempts: list[DeliveryAttempt]) -> None: ...

    def update(self, attempt: DeliveryAttempt) -> None: ...

    def redact_by_communication_id(self, communication_id: str) -> None: ...

    def remove_many_by_communication_ids(self, communication_ids: set[str]) -> int:
        """Remove delivery records for selected communications."""
        ...

    def remove_all(self) -> None: ...
