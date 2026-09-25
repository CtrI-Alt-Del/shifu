from shifu.learning.core.domain.structures.available_material_detail import (
    AvailableMaterialDetail,
)
from shifu.learning.core.domain.structures.unavailable_material_detail import (
    UnavailableMaterialDetail,
)

type MaterialDetail = AvailableMaterialDetail | UnavailableMaterialDetail
