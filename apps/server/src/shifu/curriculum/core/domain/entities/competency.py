from shifu.curriculum.core.domain.errors import InvalidCompetencyError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class Competency:
    id: str
    skill_id: str
    name: str
    description: str
    position: int

    def __post_init__(self) -> None:
        self.name = NonEmptyText.create(
            self.name, error_type=InvalidCompetencyError
        ).value
        self.description = NonEmptyText.create(
            self.description, error_type=InvalidCompetencyError
        ).value
        if self.position < 1:
            raise InvalidCompetencyError

    @classmethod
    def create(
        cls,
        *,
        id: str,
        skill_id: str,
        name: str,
        description: str,
        position: int,
    ) -> 'Competency':
        return cls(
            id=id,
            skill_id=skill_id,
            name=name,
            description=description,
            position=position,
        )
