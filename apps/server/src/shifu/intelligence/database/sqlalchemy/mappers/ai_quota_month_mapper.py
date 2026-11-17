from shifu.intelligence.core.domain.entities import AiQuotaMonth
from shifu.intelligence.database.sqlalchemy.models import AiQuotaMonthModel


class AiQuotaMonthMapper:
    @staticmethod
    def to_entity(model: AiQuotaMonthModel) -> AiQuotaMonth:
        return AiQuotaMonth(
            account_id=model.account_id,
            month=model.month,
            used_units=model.used_units,
            limit_units=model.limit_units,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(month: AiQuotaMonth) -> AiQuotaMonthModel:
        return AiQuotaMonthModel(
            account_id=month.account_id,
            month=month.month,
            used_units=month.used_units,
            limit_units=month.limit_units,
            created_at=month.created_at,
            updated_at=month.updated_at,
        )
