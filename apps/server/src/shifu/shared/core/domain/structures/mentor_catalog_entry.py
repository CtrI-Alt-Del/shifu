from shifu.shared.core.domain.structures.structure import structure


@structure
class MentorCatalogEntry:
    reference_id: str
    kind: str
    skill_id: str
    competency_id: str | None
    title: str
    description: str | None
    concept_ids: tuple[str, ...]
    source_version: str
