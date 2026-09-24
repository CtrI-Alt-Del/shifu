from decimal import Decimal

from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.shared.core.domain.structures import structure


@structure
class AdaptiveConceptState:
    concept_id: str
    initial_progress: Decimal | None
    progress: Decimal | None
    observed_difficulties: frozenset[ActivityDifficulty]
    distinct_activity_ids: frozenset[str]
    hard_confirmation: bool
    evidence_verification: bool
    inconclusive_activity_ids: tuple[str, ...]
    current_contributions: tuple[tuple[str, Decimal], ...]

    @property
    def coverage_complete(self) -> bool:
        return self.observed_difficulties == frozenset(ActivityDifficulty)
