from typing import Literal

from shifu.shared.core.domain.structures import structure


@structure
class PendingConfirmationStatusResult:
    state: Literal['ready', 'cooldown', 'delivery_issue']
    retry_after_seconds: int | None = None
