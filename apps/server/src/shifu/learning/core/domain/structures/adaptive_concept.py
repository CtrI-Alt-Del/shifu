from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveConcept:
    id: str
    competency_id: str
    position: int
    prerequisite_ids: tuple[str, ...] = ()
