from collections.abc import Mapping
from datetime import datetime

from shifu.shared.core.domain.structures import structure


@structure
class OutboxEvent:
    id: str
    name: str
    payload: Mapping[str, object]
    status: str
    attempts: int
    available_at: datetime
    reserved_by: str | None
    reservation_expires_at: datetime | None
    last_error_code: str | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
