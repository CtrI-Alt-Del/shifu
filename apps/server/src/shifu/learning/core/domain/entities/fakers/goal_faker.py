from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.entities import Goal
from shifu.shared.core.interfaces.fakers import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class GoalFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> Goal:
        created = created_at or cls._faker.date_time(tzinfo=UTC)
        return Goal(
            id=id or cls._id_provider.generate(),
            account_id=account_id or cls._id_provider.generate(),
            title=title or cls._faker.sentence(nb_words=5).rstrip('.'),
            description=description or cls._faker.paragraph(),
            created_at=created,
            updated_at=updated_at or created,
        )

    @classmethod
    def fake_many(cls, count: int = 10, **overrides: object) -> list[Goal]:
        fake = cast('Callable[..., Goal]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
