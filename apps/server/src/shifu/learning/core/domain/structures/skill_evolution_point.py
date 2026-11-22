from datetime import datetime
from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class SkillEvolutionPoint:
    occurred_at: datetime
    result: Decimal  # Habilidade result, 0..100
    is_partial: bool
    is_baseline: bool
