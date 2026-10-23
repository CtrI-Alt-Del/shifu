from datetime import UTC, datetime

from faker import Faker

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.intelligence.core.domain.entities import LearnerMemory
from shifu.intelligence.core.domain.enums import LearnerMemoryCategory


class LearnerMemoryFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        category: LearnerMemoryCategory = LearnerMemoryCategory.EXPLANATION_PREFERENCE,
        content: str | None = None,
        version: int = 1,
        last_declared_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> LearnerMemory:
        created = created_at or cls._faker.date_time(tzinfo=UTC)
        return LearnerMemory(
            id=id or cls._id_provider.generate(),
            account_id=account_id or cls._id_provider.generate(),
            category=category,
            content=content or cls._faker.sentence(nb_words=6)[:280],
            version=version,
            last_declared_at=last_declared_at or created,
            created_at=created,
            updated_at=updated_at or created,
        )
