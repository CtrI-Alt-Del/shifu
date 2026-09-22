from shifu.shared.core.domain.structures.curriculum_activity_snapshot import (
    CurriculumActivitySnapshot,
)
from shifu.shared.core.domain.structures.curriculum_material_snapshot import (
    CurriculumMaterialSnapshot,
)


type CurriculumContentItem = CurriculumMaterialSnapshot | CurriculumActivitySnapshot
