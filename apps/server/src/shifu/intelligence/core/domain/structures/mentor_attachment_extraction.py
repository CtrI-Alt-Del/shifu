from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.intelligence.core.domain.structures.mentor_attachment_chunk import (
    MentorAttachmentChunk,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentExtraction:
    chunks: tuple[MentorAttachmentChunk, ...]
    analyzed_pages: tuple[int, ...]
    illegible_pages: tuple[int, ...]
    uninterpreted_pages: tuple[int, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        pages = (*self.analyzed_pages, *self.illegible_pages, *self.uninterpreted_pages)
        if any(page < 1 for page in pages) or len(set(pages)) != len(pages):
            raise MentorAttachmentInvalidError
        if len({chunk.chunk_id for chunk in self.chunks}) != len(self.chunks):
            raise MentorAttachmentInvalidError
