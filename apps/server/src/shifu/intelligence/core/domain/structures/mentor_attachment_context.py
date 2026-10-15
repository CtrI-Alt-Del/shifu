from shifu.intelligence.core.domain.structures.mentor_attachment_chunk import (
    MentorAttachmentChunk,
)
from shifu.intelligence.core.domain.structures.mentor_attachment_source import (
    MentorAttachmentSource,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentContext:
    chunks: tuple[MentorAttachmentChunk, ...]
    sources: tuple[MentorAttachmentSource, ...]
