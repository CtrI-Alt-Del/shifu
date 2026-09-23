from typing import Protocol

from shifu.shared.core.domain.structures import CurriculumSkillSnapshot


class CurriculumContentProvider(Protocol):
    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None: ...
