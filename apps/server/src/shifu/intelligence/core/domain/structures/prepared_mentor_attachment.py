from shifu.shared.core.domain.structures import structure

from .mentor_attachment_vision_result import MentorAttachmentVisionResult


@structure
class PreparedMentorAttachment:
    attachment_id: str
    generation: int
    execution_owner: str
    media_type: str
    content: bytes
    vision_results: tuple[MentorAttachmentVisionResult, ...] = ()
