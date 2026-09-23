from shifu.shared.core.domain.structures.structure import structure


@structure
class SkillCatalogEntry:
    id: str
    name: str
    description: str
