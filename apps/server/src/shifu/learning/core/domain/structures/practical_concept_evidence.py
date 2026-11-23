from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class PracticalConceptEvidence:
    """Evidence for one Concept, separate from the grade; null means inconclusive."""

    concept_id: str
    value: Decimal | None
