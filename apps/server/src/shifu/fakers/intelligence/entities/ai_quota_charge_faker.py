from datetime import UTC, date, datetime

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.intelligence.core.domain.entities import AiQuotaCharge
from shifu.intelligence.core.domain.enums import AiQuotaRequestKind


class AiQuotaChargeFaker:
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        request_kind: AiQuotaRequestKind = AiQuotaRequestKind.MENTOR_RESPONSE,
        request_id: str | None = None,
        account_id: str | None = None,
        month: date | None = None,
        charged_units: int = 0,
        refunded: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> AiQuotaCharge:
        """An open request that has charged nothing yet, valid unless overridden."""
        created = created_at or datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        return AiQuotaCharge(
            request_kind=request_kind,
            request_id=request_id or cls._id_provider.generate(),
            account_id=account_id or cls._id_provider.generate(),
            month=month or date(2026, 11, 1),
            charged_units=charged_units,
            refunded=refunded,
            created_at=created,
            updated_at=updated_at or created,
        )
