from shifu.curriculum.core.domain.errors import InvalidSkillError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_non_empty


@entity
class Skill:
    id: str
    name: str
    description: str
    initial_diagnostic_activity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, InvalidSkillError)
        self.description = require_non_empty(self.description, InvalidSkillError)
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
