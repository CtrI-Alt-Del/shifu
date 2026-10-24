from typing import ClassVar, cast

from redis import Redis
from redis.exceptions import RedisError

from shifu.shared.core.domain.errors import ServiceUnavailableError


class RedisMentorGenerationLimitProvider:
    """Rolling-hour limit per account, kept as a sorted set of attempt ids.

    The score is the Redis server time in seconds, so every worker shares one clock.
    """

    KEY_PREFIX: ClassVar[str] = 'mentor:generation-limit:'
    WINDOW_SECONDS: ClassVar[int] = 3600
    _SCRIPT: ClassVar[str] = """
        local now = redis.call('TIME')
        local seconds = tonumber(now[1]) + tonumber(now[2]) / 1000000
        redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', seconds - tonumber(ARGV[3]))
        if redis.call('ZSCORE', KEYS[1], ARGV[1]) then
            redis.call('EXPIRE', KEYS[1], ARGV[3])
            return 1
        end
        if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then
            return 0
        end
        redis.call('ZADD', KEYS[1], seconds, ARGV[1])
        redis.call('EXPIRE', KEYS[1], ARGV[3])
        return 1
    """

    def __init__(self, client: Redis, limit_per_hour: int) -> None:
        self._client = client
        self._limit = limit_per_hour

    @classmethod
    def key_for(cls, account_id: str) -> str:
        return f'{cls.KEY_PREFIX}{account_id}'

    def try_acquire(self, account_id: str, attempt_id: str) -> bool:
        try:
            allowed = cast(
                'int',
                self._client.eval(  # pyright: ignore[reportUnknownMemberType] - redis-py types eval loosely.
                    self._SCRIPT,
                    1,
                    self.key_for(account_id),
                    attempt_id,
                    self._limit,
                    self.WINDOW_SECONDS,
                ),
            )
        except RedisError as error:
            raise ServiceUnavailableError from error
        return allowed == 1
