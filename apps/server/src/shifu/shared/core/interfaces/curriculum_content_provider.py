from typing import Protocol

from shifu.shared.core.domain.structures import (
    CurriculumSkillOverview,
    CurriculumSkillSnapshot,
)


class CurriculumContentProvider(Protocol):
    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None: ...

    def get_skill_overviews(
        self,
        skill_ids: tuple[str, ...],
    ) -> tuple[CurriculumSkillOverview, ...]: ...
