from shifu.intelligence.core.domain.enums import MentorIntent
from shifu.intelligence.core.domain.structures.mentor_attachment_source import (
    MentorAttachmentSource,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorResponseBlock:
    block_key: str
    ordinal: int
    intent: MentorIntent | None
    content: str
    sources: tuple[MentorAttachmentSource, ...] = ()
