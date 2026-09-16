from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.curriculum.core.domain.entities import Skill
from shifu.shared.core.interfaces.fakers import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class SkillFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> Skill:
        return Skill(
            id=id or cls._id_provider.generate(),
            name=name or cls._faker.sentence(nb_words=3).rstrip('.'),
            description=description or cls._faker.paragraph(),
        )

    @classmethod
    def fake_many(cls, count: int = 10, **overrides: object) -> list[Skill]:
        fake = cast('Callable[..., Skill]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
