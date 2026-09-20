from shifu.shared.core.domain.structures.structure import structure


@structure
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
