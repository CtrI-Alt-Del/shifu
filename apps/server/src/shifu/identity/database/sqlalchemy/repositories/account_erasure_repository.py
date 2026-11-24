from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from shifu.identity.core.domain.structures.account_erasure import (
    AccountErasureOverdueParticipant,
    AccountErasureResult,
)
from shifu.identity.database.sqlalchemy.models import (
    AccountBrowserCapabilityModel,
    AccountErasureModel,
    AccountErasureParticipantModel,
    AccountModel,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


class SqlalchemyAccountErasureRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_result(self, erasure_id: UUID) -> AccountErasureResult | None:
        model = self._session.get(AccountErasureModel, erasure_id)
        if model is None:
            return None
        return AccountErasureResult(
            state='closed',
            closed_at=model.closed_at,
            erasure='completed' if model.status == 'completed' else 'pending',
        )

    def find_account_id(self, erasure_id: UUID) -> str | None:
        return self._session.execute(
            select(AccountErasureModel.account_id).where(
                AccountErasureModel.erasure_id == erasure_id,
                AccountErasureModel.status == 'pending',
                AccountErasureModel.account_id.is_not(None),
            )
        ).scalar_one_or_none()

    def add(
        self,
        *,
        erasure_id: UUID,
        account_id: str,
        closed_at: datetime,
        due_at: datetime,
        participants: tuple[str, ...],
    ) -> None:
        model = AccountErasureModel(
            erasure_id=erasure_id,
            account_id=account_id,
            status='pending',
            closed_at=closed_at,
            due_at=due_at,
        )
        self._session.add(model)
        self._session.flush()
        self._session.add_all(
            [
                AccountErasureParticipantModel(
                    erasure_id=erasure_id,
                    participant=participant,
                    status='pending',
                )
                for participant in participants
            ]
        )

    def acknowledge(
        self, erasure_id: UUID, participant: str, *, acknowledged_at: datetime
    ) -> bool:
        erasure = self._session.scalar(
            select(AccountErasureModel)
            .where(AccountErasureModel.erasure_id == erasure_id)
            .with_for_update()
        )
        if erasure is None:
            return False
        participant_model = self._session.get(
            AccountErasureParticipantModel, (erasure_id, participant)
        )
        if participant_model is None:
            raise ValueError('Unknown account erasure participant')
        if participant_model.status == 'pending':
            participant_model.status = 'acknowledged'
            participant_model.acknowledged_at = acknowledged_at
            self._session.flush()

        if erasure.status == 'completed':
            return True
        has_pending = self._session.scalar(
            select(AccountErasureParticipantModel.erasure_id)
            .where(
                AccountErasureParticipantModel.erasure_id == erasure_id,
                AccountErasureParticipantModel.status == 'pending',
            )
            .limit(1)
        )
        if has_pending is None:
            if erasure.account_id is not None:
                self._session.execute(
                    delete(AccountModel).where(AccountModel.id == erasure.account_id)
                )
                self._session.execute(
                    delete(AccountBrowserCapabilityModel).where(
                        AccountBrowserCapabilityModel.account_id == erasure.account_id
                    )
                )
            erasure.account_id = None
            erasure.status = 'completed'
            erasure.completed_at = acknowledged_at
            self._session.flush()
        return True

    def find_pending(self, *, limit: int) -> list[UUID]:
        return list(
            self._session.scalars(
                select(AccountErasureModel.erasure_id)
                .where(AccountErasureModel.status == 'pending')
                .order_by(AccountErasureModel.due_at)
                .limit(limit)
            ).all()
        )

    def find_overdue_pending_participants(
        self, *, as_of: datetime, limit: int
    ) -> list[AccountErasureOverdueParticipant]:
        rows = self._session.execute(
            select(
                AccountErasureModel.erasure_id,
                AccountErasureParticipantModel.participant,
                AccountErasureModel.closed_at,
                AccountErasureModel.due_at,
            )
            .join(
                AccountErasureParticipantModel,
                AccountErasureParticipantModel.erasure_id
                == AccountErasureModel.erasure_id,
            )
            .where(
                AccountErasureModel.status == 'pending',
                AccountErasureModel.due_at <= as_of,
                AccountErasureParticipantModel.status == 'pending',
            )
            .order_by(
                AccountErasureModel.due_at,
                AccountErasureModel.erasure_id,
                AccountErasureParticipantModel.participant,
            )
            .limit(limit)
        ).all()
        return [
            AccountErasureOverdueParticipant(
                erasure_id=erasure_id,
                module='identity' if module == 'identity-bff' else module,
                closed_at=closed_at,
                due_at=due_at,
            )
            for erasure_id, module, closed_at, due_at in rows
        ]

    def remove_completed_before(self, completed_before: datetime, *, limit: int) -> int:
        models = self._session.scalars(
            select(AccountErasureModel)
            .where(
                AccountErasureModel.status == 'completed',
                AccountErasureModel.completed_at < completed_before,
            )
            .order_by(AccountErasureModel.completed_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        ).all()
        if not models:
            return 0
        erasure_ids = [model.erasure_id for model in models]
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                delete(AccountErasureModel).where(
                    AccountErasureModel.erasure_id.in_(erasure_ids)
                )
            ),
        )
        return result.rowcount or 0
