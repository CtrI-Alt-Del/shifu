from typing import Protocol

from shifu.communication.core.domain.entities import DeliveryAttempt


class DeliveryAttemptsRepository(Protocol):
    def find_by_communication_id_and_attempt_number(
        self,
        communication_id: str,
        attempt_number: int,
    ) -> DeliveryAttempt | None: ...

    def add(self, attempt: DeliveryAttempt) -> None: ...

    def replace(self, attempt: DeliveryAttempt) -> None: ...
