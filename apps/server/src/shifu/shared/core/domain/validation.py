import re
from collections.abc import Iterable
from decimal import Decimal

from shifu.shared.core.domain.errors import AppError, ValidationError

_EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def normalize_email(value: str, error_type: type[AppError] = ValidationError) -> str:
    normalized = value.strip().casefold()
    if not _EMAIL_PATTERN.fullmatch(normalized):
        raise error_type()
    return normalized


def require_non_empty(value: str, error_type: type[AppError]) -> str:
    normalized = value.strip()
    if not normalized:
        raise error_type()
    return normalized


def require_percentage(
    value: object,
    error_type: type[AppError] = ValidationError,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise error_type()
    numeric = Decimal(str(value))
    if numeric < Decimal('0') or numeric > Decimal('100'):
        raise error_type()


def require_weight_total(
    values: Iterable[int],
    error_type: type[AppError],
) -> None:
    weights = tuple(values)
    if not weights or any(weight < 0 or weight > 100 for weight in weights):
        raise error_type()
    if sum(weights) != 100:
        raise error_type()
