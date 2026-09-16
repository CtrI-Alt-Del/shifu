from shifu.shared.core.domain.structures import structure


@structure
class DeliveryOutcome:
    succeeded: bool
    provider_message_id: str | None
    failure_code: str | None
    retryable: bool
