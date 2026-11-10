"""Disposable code for the SHIFU-87 VM-02 check. It is never merged."""


def vm02_clamp(value: int, minimum: int, maximum: int) -> int:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def vm02_sign(value: int) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def vm02_label(value: int) -> str:
    if value < 10:
        return "low"
    if value < 100:
        return "medium"
    return "high"


def vm02_grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def vm02_bucket(value: int) -> int:
    if value < 0:
        return 0
    if value < 50:
        return 1
    if value < 500:
        return 2
    return 3


def vm02_parity(value: int) -> str:
    if value % 2 == 0:
        return "even"
    return "odd"
