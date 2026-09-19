from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.curriculum.core.domain.entities import Material
from shifu.curriculum.core.domain.enums import MaterialType
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class MaterialFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        skill_id: str | None = None,
        title: str | None = None,
        content: str | None = None,
        material_type: MaterialType = MaterialType.THEORY,
    ) -> Material:
        return Material(
            id=id or cls._id_provider.generate(),
            skill_id=skill_id or cls._id_provider.generate(),
            title=title or cls._faker.sentence(nb_words=5).rstrip('.'),
            content=content or cls._faker.paragraph(nb_sentences=3),
            material_type=material_type,
        )

    @classmethod
    def fake_many(cls, count: int = 10, **overrides: object) -> list[Material]:
        fake = cast('Callable[..., Material]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
