from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import structure
from shifu.shared.core.domain.validation import require_non_empty


@structure
class DeliveryOutcome:
    succeeded: bool
    provider_message_id: str | None
    failure_code: str | None
    retryable: bool

    def __post_init__(self) -> None:
        if self.succeeded and self.retryable:
            raise InvalidCommunicationError
        if self.succeeded and self.failure_code is not None:
            raise InvalidCommunicationError
        if not self.succeeded:
            if self.failure_code is None:
                object.__setattr__(
                    self,
                    'failure_code',
                    'delivery_failed',
                )
            else:
                object.__setattr__(
                    self,
                    'failure_code',
                    require_non_empty(self.failure_code, InvalidCommunicationError),
                )

    @classmethod
    def accepted(cls, provider_message_id: str | None = None) -> 'DeliveryOutcome':
        return cls(
            succeeded=True,
            provider_message_id=provider_message_id,
            failure_code=None,
            retryable=False,
        )

    @classmethod
    def temporary_failure(cls, failure_code: str) -> 'DeliveryOutcome':
        return cls(
            succeeded=False,
            provider_message_id=None,
            failure_code=failure_code,
            retryable=True,
        )

    @classmethod
    def permanent_failure(cls, failure_code: str) -> 'DeliveryOutcome':
        return cls(
            succeeded=False,
            provider_message_id=None,
            failure_code=failure_code,
            retryable=False,
        )

    @classmethod
    def rejected(cls, failure_code: str = 'rejected') -> 'DeliveryOutcome':
        return cls.permanent_failure(failure_code)
