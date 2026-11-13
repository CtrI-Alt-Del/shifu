from datetime import date, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from shifu.intelligence.core.domain.entities import AiQuotaMonth
from shifu.intelligence.database.sqlalchemy.mappers import AiQuotaMonthMapper
from shifu.intelligence.database.sqlalchemy.models import AiQuotaMonthModel


class SqlalchemyAiQuotaMonthsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ensure_and_lock(
        self, account_id: str, month: date, limit_units: int, now: datetime
    ) -> AiQuotaMonth:
        # An existing row keeps the limit copied when it was created.
        self._session.execute(
            insert(AiQuotaMonthModel)
            .values(
                account_id=account_id,
                month=month,
                used_units=0,
                limit_units=limit_units,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=['account_id', 'month'])
        )
        model = self._session.scalars(self._locked_query(account_id, month)).one()
        return AiQuotaMonthMapper.to_entity(model)

    def lock_existing(self, account_id: str, month: date) -> AiQuotaMonth | None:
        model = self._session.scalar(self._locked_query(account_id, month))
        return AiQuotaMonthMapper.to_entity(model) if model is not None else None

    def find_by_account_and_month(
        self, account_id: str, month: date
    ) -> AiQuotaMonth | None:
        model = self._session.scalar(
            select(AiQuotaMonthModel)
            .where(
                AiQuotaMonthModel.account_id == account_id,
                AiQuotaMonthModel.month == month,
            )
            .execution_options(populate_existing=True)
        )
        return AiQuotaMonthMapper.to_entity(model) if model is not None else None

    def update(self, month: AiQuotaMonth) -> None:
        self._session.execute(
            update(AiQuotaMonthModel)
            .where(
                AiQuotaMonthModel.account_id == month.account_id,
                AiQuotaMonthModel.month == month.month,
            )
            .values(used_units=month.used_units, updated_at=month.updated_at)
        )

    def lock_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            select(AiQuotaMonthModel.account_id)
            .where(AiQuotaMonthModel.account_id == account_id)
            .order_by(AiQuotaMonthModel.month)
            .with_for_update()
        ).all()

    def remove_by_account_id(self, account_id: str) -> int:
        removed = self._session.scalars(
            delete(AiQuotaMonthModel)
            .where(AiQuotaMonthModel.account_id == account_id)
            .returning(AiQuotaMonthModel.month)
        ).all()
        return len(removed)

    @staticmethod
    def _locked_query(account_id: str, month: date) -> Select[tuple[AiQuotaMonthModel]]:
        return (
            select(AiQuotaMonthModel)
            .where(
                AiQuotaMonthModel.account_id == account_id,
                AiQuotaMonthModel.month == month,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
