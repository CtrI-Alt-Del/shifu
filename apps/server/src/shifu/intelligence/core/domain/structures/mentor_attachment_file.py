from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentFile:
    filename: str
    media_type: str
    content: bytes
