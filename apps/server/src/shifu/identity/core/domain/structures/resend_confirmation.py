from datetime import datetime

from shifu.identity.core.domain.enums import ResendConfirmationResultStatus
from shifu.shared.core.domain.structures import structure


@structure
class ResendConfirmationResult:
    result: ResendConfirmationResultStatus
    retry_after_seconds: int | None = None
    identity_confirmation_id: str | None = None
    communication_id: str | None = None
    confirmation_token: str | None = None
    confirmation_expires_at: datetime | None = None
