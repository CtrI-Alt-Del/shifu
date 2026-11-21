from shifu.communication.core.domain.enums import PushDeliveryOutcomeKind
from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import NonEmptyText, structure


@structure
class PushDeliveryOutcome:
    kind: PushDeliveryOutcomeKind
    code: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, 'kind', PushDeliveryOutcomeKind(self.kind))
        except ValueError:
            raise InvalidCommunicationError from None
        if self.code is not None:
            object.__setattr__(
                self,
                'code',
                NonEmptyText.create(
                    self.code, error_type=InvalidCommunicationError
                ).value,
            )

    @classmethod
    def accepted(cls) -> 'PushDeliveryOutcome':
        return cls(kind=PushDeliveryOutcomeKind.ACCEPTED)

    @classmethod
    def gone(cls) -> 'PushDeliveryOutcome':
        return cls(kind=PushDeliveryOutcomeKind.GONE, code='subscription_gone')

    @classmethod
    def temporary_failure(cls, code: str) -> 'PushDeliveryOutcome':
        return cls(kind=PushDeliveryOutcomeKind.TEMPORARY_FAILURE, code=code)

    @classmethod
    def permanent_failure(cls, code: str) -> 'PushDeliveryOutcome':
        return cls(kind=PushDeliveryOutcomeKind.PERMANENT_FAILURE, code=code)
