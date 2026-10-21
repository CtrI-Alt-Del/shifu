from shifu.curriculum.core.domain.errors import InvalidCompetencyError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import NonEmptyText


@entity
class Concept:
    id: str
    competency_id: str
    name: str
    description: str
    position: int
    observation_criteria: str
    prerequisite_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        NonEmptyText.create(self.id, error_type=InvalidCompetencyError)
        self.competency_id = NonEmptyText.create(
            self.competency_id, error_type=InvalidCompetencyError
        ).value
        self.name = NonEmptyText.create(
            self.name, error_type=InvalidCompetencyError
        ).value
        self.description = NonEmptyText.create(
            self.description, error_type=InvalidCompetencyError
        ).value
        self.observation_criteria = NonEmptyText.create(
            self.observation_criteria, error_type=InvalidCompetencyError
        ).value
        if self.position < 1 or self.id in self.prerequisite_ids:
            raise InvalidCompetencyError

        if len(self.prerequisite_ids) != len(set(self.prerequisite_ids)):
            raise InvalidCompetencyError
