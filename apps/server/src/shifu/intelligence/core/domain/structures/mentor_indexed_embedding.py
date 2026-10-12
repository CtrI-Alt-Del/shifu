from shifu.shared.core.domain.structures import structure


@structure
class MentorIndexedEmbedding:
    corpus: str
    reference_id: str
    variation_key: str
    vector: tuple[float, ...]
