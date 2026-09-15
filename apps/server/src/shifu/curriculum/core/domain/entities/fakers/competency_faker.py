from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.curriculum.core.domain.entities import Competency
from shifu.shared.core.interfaces.fakers import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class CompetencyFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        skill_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        position: int | None = None,
    ) -> Competency:
        return Competency(
            id=id or cls._id_provider.generate(),
            skill_id=skill_id or cls._id_provider.generate(),
            name=name or cls._faker.sentence(nb_words=3).rstrip('.'),
            description=description or cls._faker.paragraph(),
            position=position or cls._faker.pyint(min_value=1, max_value=10),
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[Competency]:
        fake = cast('Callable[..., Competency]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
