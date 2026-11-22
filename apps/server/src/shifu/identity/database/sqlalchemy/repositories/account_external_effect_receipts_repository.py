from datetime import datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from shifu.identity.core.domain.structures.account_external_effect_receipt import (
    AccountExternalEffectReceiptAdmission,
    AccountExternalEffectReceiptReconciliation,
)
from shifu.identity.database.sqlalchemy.mappers.account_external_effect_receipt_mapper import (
    AccountExternalEffectReceiptMapper,
)
from shifu.identity.database.sqlalchemy.models.account_external_effect_receipt_model import (
    AccountExternalEffectReceiptModel,
)
from shifu.identity.database.sqlalchemy.models.account_external_effect_reconciliation_model import (
    AccountExternalEffectReconciliationModel,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


class SqlalchemyAccountExternalEffectReceiptsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def admit(
        self, account_id: str, effect_id: UUID, operation: str
    ) -> AccountExternalEffectReceiptAdmission:
        result = self._session.execute(
            insert(AccountExternalEffectReceiptModel)
            .values(
                account_id=account_id,
                effect_id=effect_id,
                operation=operation,
                state='in_flight',
            )
            .on_conflict_do_nothing(
                index_elements=[
                    AccountExternalEffectReceiptModel.account_id,
                    AccountExternalEffectReceiptModel.effect_id,
                ]
            )
            .returning(AccountExternalEffectReceiptModel.effect_id)
        )
        is_new = result.scalar_one_or_none() is not None
        model = self._session.scalar(
            select(AccountExternalEffectReceiptModel)
            .where(
                AccountExternalEffectReceiptModel.account_id == account_id,
                AccountExternalEffectReceiptModel.effect_id == effect_id,
            )
            .with_for_update()
        )
        if model is None:
            raise RuntimeError('External effect receipt was not persisted')
        return AccountExternalEffectReceiptMapper.to_admission(model, is_new=is_new)

    def settle(self, account_id: str, effect_id: UUID) -> None:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                update(AccountExternalEffectReceiptModel)
                .where(
                    AccountExternalEffectReceiptModel.account_id == account_id,
                    AccountExternalEffectReceiptModel.effect_id == effect_id,
                    AccountExternalEffectReceiptModel.state.in_(
                        ('in_flight', 'unknown')
                    ),
                )
                .values(state='settled')
            ),
        )
        if result.rowcount == 1:
            return

        receipt = self._session.scalar(
            select(AccountExternalEffectReceiptModel)
            .where(
                AccountExternalEffectReceiptModel.account_id == account_id,
                AccountExternalEffectReceiptModel.effect_id == effect_id,
            )
            .with_for_update()
        )
        if receipt is None or receipt.state != 'settled':
            raise RuntimeError('External effect receipt could not be settled')

    def mark_unknown(self, account_id: str, effect_id: UUID) -> None:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                update(AccountExternalEffectReceiptModel)
                .where(
                    AccountExternalEffectReceiptModel.account_id == account_id,
                    AccountExternalEffectReceiptModel.effect_id == effect_id,
                    AccountExternalEffectReceiptModel.state == 'in_flight',
                )
                .values(state='unknown')
            ),
        )
        if result.rowcount != 1:
            raise RuntimeError('External effect receipt could not be marked unknown')

    def list_unresolved(
        self, limit: int
    ) -> tuple[AccountExternalEffectReceiptAdmission, ...]:
        models = self._session.scalars(
            select(AccountExternalEffectReceiptModel)
            .where(
                AccountExternalEffectReceiptModel.state.in_(('in_flight', 'unknown'))
            )
            .order_by(
                AccountExternalEffectReceiptModel.admitted_at,
                AccountExternalEffectReceiptModel.account_id,
                AccountExternalEffectReceiptModel.effect_id,
            )
            .limit(limit)
        )
        return tuple(
            AccountExternalEffectReceiptMapper.to_admission(model, is_new=False)
            for model in models
        )

    def reconcile(
        self,
        reconciliation: AccountExternalEffectReceiptReconciliation,
        *,
        reconciled_at: datetime,
        stale_before: datetime,
    ) -> bool:
        model = self._session.scalar(
            select(AccountExternalEffectReceiptModel)
            .where(
                AccountExternalEffectReceiptModel.account_id
                == reconciliation.account_id,
                AccountExternalEffectReceiptModel.effect_id == reconciliation.effect_id,
            )
            .with_for_update()
        )
        if (
            model is None
            or model.operation != reconciliation.operation
            or model.state not in ('in_flight', 'unknown')
            or (
                model.state in ('in_flight', 'unknown')
                and (
                    not reconciliation.confirm_no_live_operation
                    or model.admitted_at > stale_before
                )
            )
        ):
            return False

        self._session.add(
            AccountExternalEffectReconciliationModel(
                id=uuid4(),
                effect_id=reconciliation.effect_id,
                operation=reconciliation.operation,
                previous_state=model.state,
                resolution=reconciliation.resolution,
                operator_id=reconciliation.operator_id,
                evidence_reference=reconciliation.evidence_reference,
                evidence_sha256=reconciliation.evidence_sha256,
                reconciled_at=reconciled_at,
            )
        )
        if reconciliation.resolution == 'applied':
            model.state = 'settled'
        else:
            self._session.delete(model)
        return True

    def remove_reconciliations_before(self, cutoff: datetime, limit: int) -> int:
        models = self._session.scalars(
            select(AccountExternalEffectReconciliationModel)
            .where(AccountExternalEffectReconciliationModel.reconciled_at < cutoff)
            .order_by(AccountExternalEffectReconciliationModel.reconciled_at)
            .limit(limit)
        )
        removed = 0
        for model in models:
            self._session.delete(model)
            removed += 1
        return removed

    def has_unresolved_for_account_id(self, account_id: str) -> bool:
        effect_id = self._session.scalar(
            select(AccountExternalEffectReceiptModel.effect_id)
            .where(
                AccountExternalEffectReceiptModel.account_id == account_id,
                AccountExternalEffectReceiptModel.state.in_(('in_flight', 'unknown')),
            )
            .limit(1)
        )
        return effect_id is not None

    def remove_settled_for_account_id(self, account_id: str) -> int:
        result = cast(
            'CursorResult[Any]',
            self._session.execute(
                delete(AccountExternalEffectReceiptModel).where(
                    AccountExternalEffectReceiptModel.account_id == account_id,
                    AccountExternalEffectReceiptModel.state == 'settled',
                )
            ),
        )
        return result.rowcount or 0
