from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentSource:
    attachment_id: str
    chunk_id: str
    page_number: int | None
    locator: str

    def __post_init__(self) -> None:
        if (
            not self.attachment_id.strip()
            or not self.chunk_id.strip()
            or (self.page_number is not None and self.page_number < 1)
            or not self.locator.strip()
        ):
            raise MentorAttachmentInvalidError
