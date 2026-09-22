"""Decimal helpers — money never touches a binary float."""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

CENTS = Decimal("0.01")
ZERO = Decimal("0.00")

Numberish = Union[int, float, str, Decimal, None]


def to_decimal(value: Numberish) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Numberish) -> Decimal:
    """Round to the nearest cent using the accounting convention."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)


def percentage(part: Numberish, whole: Numberish, digits: int = 2) -> float:
    whole_dec = to_decimal(whole)
    if whole_dec == 0:
        return 0.0
    return round(float(to_decimal(part) / whole_dec * 100), digits)


def safe_divide(numerator: Numberish, denominator: Numberish) -> Decimal:
    denom = to_decimal(denominator)
    if denom == 0:
        return ZERO
    return money(to_decimal(numerator) / denom)


def format_ugx(value: Numberish, currency: str = "UGX") -> str:
    """Server-side formatting for exported reports (PDF/CSV)."""
    amount = money(value)
    whole = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{currency} {whole:,}"
