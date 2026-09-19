from shifu.shared.core.domain.structures import structure


@structure
class EmailDelivery:
    provider_message_id: str
