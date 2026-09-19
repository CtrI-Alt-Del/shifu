from shifu.shared.core.domain.structures import structure


@structure
class Event[Payload]:
    name: str
    payload: Payload
