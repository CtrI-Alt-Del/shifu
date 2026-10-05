from shifu.curriculum.core.domain.errors import InvalidSkillError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class Skill:
    id: str
    name: str
    description: str
    initial_diagnostic_activity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.name = NonEmptyText.create(self.name, error_type=InvalidSkillError).value
        self.description = NonEmptyText.create(
            self.description, error_type=InvalidSkillError
        ).value
        if len(self.initial_diagnostic_activity_ids) != len(
            set(self.initial_diagnostic_activity_ids)
        ):
            raise InvalidSkillError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        name: str,
        description: str,
        initial_diagnostic_activity_ids: tuple[str, ...] = (),
    ) -> 'Skill':
        return cls(
            id=id,
            name=name,
            description=description,
            initial_diagnostic_activity_ids=initial_diagnostic_activity_ids,
        )
