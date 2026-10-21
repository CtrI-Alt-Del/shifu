from shifu.shared.core.domain.structures.structure import structure


@structure
class MentorUsage:
    operation_key: str
    attempt_id: str
    used_tokens: int
    cancelled: bool
