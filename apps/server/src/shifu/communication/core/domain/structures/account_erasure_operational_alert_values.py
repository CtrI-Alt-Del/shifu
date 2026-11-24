from datetime import datetime
from uuid import UUID

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import NonEmptyText, structure

_ALLOWED_MODULES = frozenset(
    {'identity', 'learning', 'gamification', 'intelligence', 'communication'}
)
_FAILURE_CODE = 'erasure_deadline_exceeded'


@structure
class AccountErasureOperationalAlertValues:
    """Non-personal values for the fixed account-erasure operations notice."""

    erasure_id: UUID
    module: str
    failure_code: str
    closed_at: datetime
    due_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            'module',
            NonEmptyText.create(
                self.module, error_type=InvalidCommunicationError
            ).value,
        )
        if self.module not in _ALLOWED_MODULES:
            raise InvalidCommunicationError
        if self.failure_code != _FAILURE_CODE:
            raise InvalidCommunicationError
        for value in (self.closed_at, self.due_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise InvalidCommunicationError
        if self.due_at < self.closed_at:
            raise InvalidCommunicationError
