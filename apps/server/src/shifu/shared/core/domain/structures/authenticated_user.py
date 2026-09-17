from shifu.shared.core.domain.structures.structure import structure


@structure
class AuthenticatedUser:
    account_id: str
    display_name: str
    time_zone: str | None
