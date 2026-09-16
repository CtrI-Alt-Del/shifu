from shifu.shared.core.domain.entities import entity


@entity
class Competency:
    id: str
    skill_id: str
    name: str
    description: str
    position: int
