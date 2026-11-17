from datetime import UTC, date, datetime

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.intelligence.core.domain.entities import AiQuotaMonth


class AiQuotaMonthFaker:
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        account_id: str | None = None,
        month: date | None = None,
        used_units: int = 0,
        limit_units: int = 1000,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> AiQuotaMonth:
        """A month with no usage and the test limit, valid unless overridden."""
        created = created_at or datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
        return AiQuotaMonth(
            account_id=account_id or cls._id_provider.generate(),
            month=month or date(2026, 11, 1),
            used_units=used_units,
            limit_units=limit_units,
            created_at=created,
            updated_at=updated_at or created,
        )
