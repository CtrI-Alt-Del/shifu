from dataclasses import field
from datetime import datetime
from typing import ClassVar

from shifu.shared.core.domain.events import Event
from shifu.shared.core.domain.structures import structure


@structure
class AccountErasureOperationalAlertRequestedPayload:
    incident_id: str
    erasure_id: str
    module: str
    failure_code: str
    closed_at: datetime
    due_at: datetime


@structure
class AccountErasureOperationalAlertRequestedEvent(
    Event[AccountErasureOperationalAlertRequestedPayload]
):
    EVENT_NAME: ClassVar[str] = 'identity/account-erasure.operational-alert.requested'
    name: str = field(default=EVENT_NAME, init=False)
