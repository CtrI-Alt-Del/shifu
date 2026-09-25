from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveMaterial:
    id: str
    position: int
    concept_ids: tuple[str, ...]
    available: bool = True
    competency_id: str | None = None
