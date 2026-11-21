from shifu.shared.core.domain.structures.structure import structure


@structure
class ActiveAccount:
    account_id: str
    time_zone: str | None
