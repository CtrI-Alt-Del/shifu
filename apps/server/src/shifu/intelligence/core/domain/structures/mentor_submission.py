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

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise MentorInputInvalidError
        try:
            parsed = UUID(self.submission_key)
        except ValueError as error:
            raise MentorInputInvalidError from error
        if parsed.version != 4 or str(parsed) != self.submission_key.lower():
            raise MentorInputInvalidError
