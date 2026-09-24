from typing import Protocol

from shifu.shared.core.domain.structures import (
    CurriculumMaterialContentSnapshot,
    CurriculumSkillSnapshot,
)


class CurriculumContentProvider(Protocol):
    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None: ...

    def get_material_content(
        self, material_id: str
    ) -> CurriculumMaterialContentSnapshot | None: ...
