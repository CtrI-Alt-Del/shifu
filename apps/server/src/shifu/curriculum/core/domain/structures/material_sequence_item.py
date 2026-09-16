from shifu.shared.core.domain.structures import structure


@structure
class MaterialSequenceItem:
    position: int
    material_id: str
