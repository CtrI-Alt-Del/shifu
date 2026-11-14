import hashlib

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shifu.learning.core.domain.structures import GoalConfirmation
from shifu.learning.database.sqlalchemy.mappers import GoalConfirmationMapper
from shifu.learning.database.sqlalchemy.models import GoalConfirmationModel


class SqlalchemyGoalConfirmationsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def lock(self, account_id: str, confirmation_key: str) -> None:
        # A transaction-scoped advisory lock serializes duplicate deliveries of the
        # same confirmation before the first one commits its row.
        digest = hashlib.sha256(
            f'goal-confirmation:{account_id}:{confirmation_key}'.encode()
        ).digest()[:8]
        advisory_key = int.from_bytes(digest, byteorder='big', signed=True)
        self._session.execute(select(func.pg_advisory_xact_lock(advisory_key)))

    def find(self, account_id: str, confirmation_key: str) -> GoalConfirmation | None:
        model = self._session.scalar(
            select(GoalConfirmationModel).where(
                GoalConfirmationModel.account_id == account_id,
                GoalConfirmationModel.confirmation_key == confirmation_key,
            )
        )
        return GoalConfirmationMapper.to_domain(model) if model is not None else None

    def add(self, confirmation: GoalConfirmation) -> None:
        self._session.add(GoalConfirmationMapper.to_model(confirmation))
        self._session.flush()
