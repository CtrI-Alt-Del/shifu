from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    MentorMessageRole,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import MentorMessageAiCharge
from shifu.intelligence.database.sqlalchemy.mappers import (
    AiQuotaChargeMapper,
    MentorMessageAiChargeMapper,
)
from shifu.intelligence.database.sqlalchemy.models import (
    AiQuotaChargeModel,
    AiQuotaMonthModel,
    MentorMessageModel,
    MentorResponseAttemptModel,
)


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

    def find_many_by_mentor_session(
        self, account_id: str, session_id: str
    ) -> tuple[MentorMessageAiCharge, ...]:
        # A Mentor message answers its learner message; the completed attempt for that
        # learner message holds the charge. Refunded charges gave their units back.
        charged_units = func.sum(AiQuotaChargeModel.charged_units)
        rows = self._session.execute(
            select(
                MentorMessageModel.id,
                MentorResponseAttemptModel.id,
                charged_units,
                AiQuotaMonthModel.limit_units,
            )
            .join(
                MentorResponseAttemptModel,
                (MentorResponseAttemptModel.session_id == MentorMessageModel.session_id)
                & (
                    MentorResponseAttemptModel.learner_message_id
                    == MentorMessageModel.in_reply_to_message_id
                ),
            )
            .join(
                AiQuotaChargeModel,
                (
                    AiQuotaChargeModel.request_kind
                    == AiQuotaRequestKind.MENTOR_RESPONSE.value
                )
                & (AiQuotaChargeModel.request_id == MentorResponseAttemptModel.id),
            )
            .join(
                AiQuotaMonthModel,
                (AiQuotaMonthModel.account_id == AiQuotaChargeModel.account_id)
                & (AiQuotaMonthModel.month == AiQuotaChargeModel.month),
            )
            .where(
                MentorMessageModel.session_id == session_id,
                MentorMessageModel.role == MentorMessageRole.MENTOR.value,
                MentorResponseAttemptModel.account_id == account_id,
                MentorResponseAttemptModel.status
                == MentorResponseStatus.COMPLETED.value,
                AiQuotaChargeModel.account_id == account_id,
                AiQuotaChargeModel.refunded.is_(False),
            )
            .group_by(
                MentorMessageModel.id,
                MentorResponseAttemptModel.id,
                AiQuotaMonthModel.limit_units,
            )
            .order_by(MentorMessageModel.id)
        ).all()
        return tuple(
            MentorMessageAiChargeMapper.to_structure(
                message_id, attempt_id, int(units), limit
            )
            for message_id, attempt_id, units, limit in rows
        )

    @staticmethod
    def _query(
        kind: AiQuotaRequestKind, request_id: str
    ) -> Select[tuple[AiQuotaChargeModel]]:
        return select(AiQuotaChargeModel).where(
            AiQuotaChargeModel.request_kind == kind.value,
            AiQuotaChargeModel.request_id == request_id,
        )
