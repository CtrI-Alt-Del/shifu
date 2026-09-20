from shifu.curriculum.core.domain.errors import InvalidSkillError
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.validation import require_non_empty


@entity
class Skill:
    id: str
    name: str
    description: str

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, InvalidSkillError)
        self.description = require_non_empty(self.description, InvalidSkillError)

    @classmethod
    def create(cls, *, id: str, name: str, description: str) -> 'Skill':
        return cls(id=id, name=name, description=description)
