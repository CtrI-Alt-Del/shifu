from shifu.shared.core.domain.structures import structure


@structure
class PreparedMentorAttachment:
    attachment_id: str
    generation: int
    execution_owner: str
    media_type: str
    content: bytes
