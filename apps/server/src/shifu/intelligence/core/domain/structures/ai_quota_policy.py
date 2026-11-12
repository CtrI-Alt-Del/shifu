from decimal import Decimal

from shifu.shared.core.domain.structures import structure


@structure
class AiQuotaPolicy:
    monthly_limit_units: int
    input_weight: Decimal
    output_weight: Decimal

    def __post_init__(self) -> None:
        if (
            self.monthly_limit_units <= 0
            or self.input_weight <= 0
            or self.output_weight <= 0
        ):
            raise ValueError('The AI quota limit and weights must be positive.')
