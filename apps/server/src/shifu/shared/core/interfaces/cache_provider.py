from typing import Protocol

from shifu.shared.core.domain.structures import RateLimitDecision


class CacheProvider(Protocol):
    async def consume_rate_limit_token(
        self, key: str, capacity: int, refill_per_second: float
    ) -> RateLimitDecision:
        """Atomically consume one token from the bucket identified by key.

        Create the bucket at full capacity on first use, refill it continuously up to
        capacity at refill_per_second, and consume one token when available. Return a
        decision without side effects when the bucket has no token left.
        """
        ...
