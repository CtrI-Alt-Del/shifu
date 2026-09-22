from shifu.learning.core.domain.structures.available_competency_detail import (
    AvailableCompetencyDetail,
)
from shifu.learning.core.domain.structures.competency_activity_detail import (
    CompetencyActivityDetail,
)
from shifu.learning.core.domain.structures.competency_material_detail import (
    CompetencyMaterialDetail,
)
from shifu.learning.core.domain.structures.unavailable_competency_detail import (
    UnavailableCompetencyDetail,
)

type CompetencyDetailItem = CompetencyMaterialDetail | CompetencyActivityDetail
type CompetencyDetail = AvailableCompetencyDetail | UnavailableCompetencyDetail
