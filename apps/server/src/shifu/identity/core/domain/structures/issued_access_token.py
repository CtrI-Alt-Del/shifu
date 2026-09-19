from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class IssuedAccessToken:
    token: str
    expires_at: datetime
