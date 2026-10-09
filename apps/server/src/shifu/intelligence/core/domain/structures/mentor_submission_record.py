from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class MentorSubmissionRecord:
    session_id: str
    content_fingerprint: str | None
    deleted_at: datetime | None
