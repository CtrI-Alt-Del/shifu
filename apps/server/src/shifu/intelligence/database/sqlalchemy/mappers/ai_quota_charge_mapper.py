from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind
from shifu.intelligence.database.sqlalchemy.models import AiQuotaChargeModel


class AiQuotaChargeMapper:
    @staticmethod
    def to_entity(model: AiQuotaChargeModel) -> AiQuotaCharge:
        return AiQuotaCharge(
            request_kind=AiQuotaRequestKind(model.request_kind),
            request_id=model.request_id,
            account_id=model.account_id,
            month=model.month,
            charged_units=model.charged_units,
            refunded=model.refunded,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(charge: AiQuotaCharge) -> AiQuotaChargeModel:
        return AiQuotaChargeModel(
            request_kind=charge.request_kind.value,
            request_id=charge.request_id,
            account_id=charge.account_id,
            month=charge.month,
            charged_units=charge.charged_units,
            refunded=charge.refunded,
            created_at=charge.created_at,
            updated_at=charge.updated_at,
        )
