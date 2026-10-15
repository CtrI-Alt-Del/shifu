from uuid import UUID

from shifu.intelligence.core.domain.errors import MentorInputInvalidError
from shifu.intelligence.core.domain.structures.mentor_context_hint import (
    MentorContextHint,
)
from shifu.shared.core.domain.structures import structure


@structure
class MentorSubmission:
    submission_key: str
    content: str
    context_hint: MentorContextHint | None = None
    attachment_batch_id: str | None = None
    attachment_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise MentorInputInvalidError
        try:
            parsed = UUID(self.submission_key)
        except ValueError as error:
            raise MentorInputInvalidError from error
        if parsed.version != 4 or str(parsed) != self.submission_key.lower():
            raise MentorInputInvalidError
        if (
            len(self.attachment_ids) > 5
            or len(set(self.attachment_ids)) != len(self.attachment_ids)
            or bool(self.attachment_ids) != (self.attachment_batch_id is not None)
            or (
                self.attachment_batch_id is not None
                and not self.attachment_batch_id.strip()
            )
            or any(not attachment_id.strip() for attachment_id in self.attachment_ids)
        ):
            raise MentorInputInvalidError
