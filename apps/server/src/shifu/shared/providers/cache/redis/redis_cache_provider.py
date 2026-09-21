from typing import TYPE_CHECKING

from redis.asyncio import Redis

from shifu.shared.core.domain.structures import RateLimitDecision
from shifu.shared.core.interfaces import CacheProvider

if TYPE_CHECKING:
    from redis.commands.core import AsyncScript

_TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_per_second = tonumber(ARGV[2])
local ttl_seconds = tonumber(ARGV[3])

local time = redis.call('TIME')
local now = tonumber(time[1]) + tonumber(time[2]) / 1000000

local bucket = redis.call('HMGET', key, 'tokens', 'updated_at')
local tokens = tonumber(bucket[1])
local updated_at = tonumber(bucket[2])

if tokens == nil then
  tokens = capacity
  updated_at = now
end

local elapsed = math.max(0, now - updated_at)
tokens = math.min(capacity, tokens + elapsed * refill_per_second)

local allowed = 0
local retry_after = 0

if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
else
  local deficit = 1 - tokens
  retry_after = math.ceil(deficit / refill_per_second)
end

redis.call('HSET', key, 'tokens', tostring(tokens), 'updated_at', tostring(now))
redis.call('EXPIRE', key, ttl_seconds)

return {allowed, retry_after}
"""


class RedisCacheProvider(CacheProvider):
    def __init__(self, client: Redis) -> None:
        self._client = client
        self._consume_script: AsyncScript = client.register_script(_TOKEN_BUCKET_SCRIPT)

    @classmethod
    def connect(cls, redis_url: str) -> 'RedisCacheProvider':
        client = Redis.from_url(redis_url)  # pyright: ignore[reportUnknownMemberType]
        return cls(client)

    async def ping(self) -> bool:
        return await self._client.ping()  # pyright: ignore[reportUnknownMemberType]

    async def close(self) -> None:
        await self._client.aclose()

    async def consume_rate_limit_token(
        self, key: str, capacity: int, refill_per_second: float
    ) -> RateLimitDecision:
        ttl_seconds = int(capacity / refill_per_second) + 60
        allowed, retry_after = await self._consume_script(
            keys=[key], args=[capacity, refill_per_second, ttl_seconds]
        )
        return RateLimitDecision(
            allowed=bool(allowed), retry_after_seconds=int(retry_after)
        )
