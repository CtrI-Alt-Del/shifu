from shifu.shared.core.domain.entities import entity


@entity
class Skill:
    id: str
    name: str
    description: str
