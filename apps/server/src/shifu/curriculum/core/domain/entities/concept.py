from shifu.curriculum.core.domain.errors import InvalidCompetencyError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_non_empty


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
        require_non_empty(self.id, InvalidCompetencyError)
        self.competency_id = require_non_empty(
            self.competency_id, InvalidCompetencyError
        )
        self.name = require_non_empty(self.name, InvalidCompetencyError)
        self.description = require_non_empty(self.description, InvalidCompetencyError)
        self.observation_criteria = require_non_empty(
            self.observation_criteria, InvalidCompetencyError
        )
        if self.position < 1 or self.id in self.prerequisite_ids:
            raise InvalidCompetencyError
        if len(self.prerequisite_ids) != len(set(self.prerequisite_ids)):
            raise InvalidCompetencyError
