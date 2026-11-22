from shifu.intelligence.core.domain.errors import MentorAttachmentInvalidError
from shifu.shared.core.domain.structures import structure


@structure
class MentorAttachmentVisionResult:
    page_number: int
    legible: bool
    description: str

    def __post_init__(self) -> None:
        if (
            self.page_number < 1
            or len(self.description) > 6000
            or self.legible == (not self.description.strip())
        ):
            raise MentorAttachmentInvalidError
