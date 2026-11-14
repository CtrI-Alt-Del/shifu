from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.curriculum.core.domain.entities import Concept
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class ConceptFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        competency_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        position: int | None = None,
        observation_criteria: str | None = None,
        prerequisite_ids: tuple[str, ...] = (),
    ) -> Concept:
        return Concept(
            id=id or cls._id_provider.generate(),
            competency_id=competency_id or cls._id_provider.generate(),
            name=name or cls._faker.sentence(nb_words=3).rstrip('.'),
            description=description or cls._faker.paragraph(),
            position=position or cls._faker.pyint(min_value=1, max_value=10),
            observation_criteria=observation_criteria or cls._faker.sentence(),
            prerequisite_ids=prerequisite_ids,
        )

    @classmethod
    def fake_many(cls, count: int = 10, **overrides: object) -> list[Concept]:
        fake = cast('Callable[..., Concept]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
