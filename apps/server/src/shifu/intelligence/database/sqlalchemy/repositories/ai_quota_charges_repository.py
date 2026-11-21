from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.database.sqlalchemy.mappers import AiQuotaChargeMapper
from shifu.intelligence.database.sqlalchemy.models import AiQuotaChargeModel


class SqlalchemyAiQuotaChargesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, charge: AiQuotaCharge) -> None:
        self._session.add(AiQuotaChargeMapper.to_model(charge))
        self._session.flush()

    def find(self, kind: AiQuotaRequestKind, request_id: str) -> AiQuotaCharge | None:
        model = self._session.scalar(
            self._query(kind, request_id).execution_options(populate_existing=True)
        )
        return AiQuotaChargeMapper.to_entity(model) if model is not None else None

    def find_for_update(
        self, kind: AiQuotaRequestKind, request_id: str
    ) -> AiQuotaCharge | None:
        model = self._session.scalar(
            self._query(kind, request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return AiQuotaChargeMapper.to_entity(model) if model is not None else None

    def update(self, charge: AiQuotaCharge) -> None:
        self._session.execute(
            update(AiQuotaChargeModel)
            .where(
                AiQuotaChargeModel.request_kind == charge.request_kind.value,
                AiQuotaChargeModel.request_id == charge.request_id,
            )
            .values(
                charged_units=charge.charged_units,
                refunded=charge.refunded,
                updated_at=charge.updated_at,
            )
        )

    def remove_by_account_id(self, account_id: str) -> int:
        removed = self._session.scalars(
            delete(AiQuotaChargeModel)
            .where(AiQuotaChargeModel.account_id == account_id)
            .returning(AiQuotaChargeModel.request_id)
        ).all()
        return len(removed)

    @staticmethod
    def _query(
        kind: AiQuotaRequestKind, request_id: str
    ) -> Select[tuple[AiQuotaChargeModel]]:
        return select(AiQuotaChargeModel).where(
            AiQuotaChargeModel.request_kind == kind.value,
            AiQuotaChargeModel.request_id == request_id,
        )
