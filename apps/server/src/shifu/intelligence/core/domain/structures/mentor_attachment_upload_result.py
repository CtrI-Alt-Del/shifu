from shifu.intelligence.core.domain.structures.mentor_attachment_view import (
    MentorAttachmentView,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentUploadResult:
    attachment: MentorAttachmentView
    created: bool
