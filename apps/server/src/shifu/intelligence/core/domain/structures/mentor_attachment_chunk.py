from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentChunk:
    chunk_id: str
    attachment_id: str
    generation: int
    page_number: int | None
    locator: str
    content: str

    def __post_init__(self) -> None:
        if (
            not self.chunk_id.strip()
            or not self.attachment_id.strip()
            or self.generation < 1
            or (self.page_number is not None and self.page_number < 1)
            or not self.locator.strip()
            or not self.content.strip()
        ):
            raise MentorAttachmentInvalidError
