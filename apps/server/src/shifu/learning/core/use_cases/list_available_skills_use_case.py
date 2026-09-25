from shifu.shared.core.domain.structures import CurriculumSkillSnapshot
from shifu.shared.core.interfaces import CurriculumContentProvider


class ListAvailableSkillsUseCase:
    def __init__(self, curriculum: CurriculumContentProvider) -> None:
        self._curriculum = curriculum

    def execute(self) -> tuple[CurriculumSkillSnapshot, ...]:
        return self._curriculum.list_skill_content()
