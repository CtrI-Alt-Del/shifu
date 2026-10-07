from decimal import Decimal


def demonstrated_progress(values: tuple[Decimal | None, ...]) -> Decimal | None:
    """Display observed evidence against the full Concept catalog."""
    if not values or all(value is None for value in values):
        return None

    return sum(
        (value for value in values if value is not None), Decimal('0')
    ) / Decimal(len(values))
