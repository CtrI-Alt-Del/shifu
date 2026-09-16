from shifu.communication.core.domain.entities import Communication, DeliveryAttempt
from shifu.communication.core.interfaces import (
    CommunicationsRepository,
    DeliveryAttemptsRepository,
)


class CommunicationSeeder:
    def __init__(
        self,
        communications_repository: CommunicationsRepository,
        delivery_attempts_repository: DeliveryAttemptsRepository,
    ) -> None:
        self._communications_repository = communications_repository
        self._delivery_attempts_repository = delivery_attempts_repository

    def clear(self) -> None:
        self._delivery_attempts_repository.remove_all()
        self._communications_repository.remove_all()

    def run(
        self,
        communications: list[Communication],
        delivery_attempts: list[DeliveryAttempt] | None = None,
    ) -> None:
        self._communications_repository.add_many(communications)
        self._delivery_attempts_repository.add_many(delivery_attempts or [])
