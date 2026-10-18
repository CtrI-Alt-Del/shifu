from shifu.intelligence.core.domain.enums import MentorAttachmentStatus
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentView:
    attachment_id: str
    filename: str
    media_type: str
    size_bytes: int
    status: MentorAttachmentStatus
    failure_code: str | None
    analyzed_pages: tuple[int, ...]
    illegible_pages: tuple[int, ...]
    uninterpreted_pages: tuple[int, ...]
