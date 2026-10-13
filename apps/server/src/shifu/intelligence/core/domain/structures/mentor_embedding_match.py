from shifu.shared.core.domain.structures import structure


@structure
class MentorEmbeddingMatch:
    reference_id: str
    variation_key: str
    similarity: float
