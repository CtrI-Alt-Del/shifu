from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING, ClassVar, cast

from pydantic import TypeAdapter

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.errors import PlanningStateConflictError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from redis import Redis
    from redis.commands.core import Script

_ADD_SCRIPT = """
local key = KEYS[1]
local account_index_key = KEYS[2]
if redis.call('EXISTS', key) == 1 then
  return 0
end
redis.call('HSET', key, 'version', ARGV[1], 'document', ARGV[2])
redis.call('EXPIRE', key, tonumber(ARGV[3]))
local server_time = redis.call('TIME')
local expires_at = tonumber(server_time[1]) + tonumber(ARGV[3])
  + tonumber(server_time[2]) / 1000000
local cutoff = expires_at - tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', account_index_key, '-inf', cutoff)
redis.call('ZADD', account_index_key, expires_at, ARGV[4])
redis.call('EXPIRE', account_index_key, tonumber(ARGV[3]))
return 1
"""

_UPDATE_SCRIPT = """
local key = KEYS[1]
local account_index_key = KEYS[2]
local current = redis.call('HGET', key, 'version')
if current == false then
  return 0
end
if tonumber(current) ~= tonumber(ARGV[1]) then
  return 0
end
redis.call('HSET', key, 'version', tostring(tonumber(ARGV[1]) + 1), 'document', ARGV[2])
redis.call('EXPIRE', key, tonumber(ARGV[3]))
local server_time = redis.call('TIME')
local expires_at = tonumber(server_time[1]) + tonumber(ARGV[3])
  + tonumber(server_time[2]) / 1000000
local cutoff = expires_at - tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', account_index_key, '-inf', cutoff)
redis.call('ZADD', account_index_key, expires_at, ARGV[4])
redis.call('EXPIRE', account_index_key, tonumber(ARGV[3]))
return 1
"""

_REMOVE_SCRIPT = """
local deleted = redis.call('DEL', KEYS[1])
redis.call('ZREM', KEYS[2], ARGV[1])
if redis.call('ZCARD', KEYS[2]) == 0 then
  redis.call('DEL', KEYS[2])
end
return deleted
"""

_REMOVE_BY_ACCOUNT_SCRIPT = """
local planning_ids = redis.call('ZRANGE', KEYS[1], 0, -1)
local removed = 0
for _, planning_id in ipairs(planning_ids) do
  removed = removed + redis.call('DEL', ARGV[1] .. planning_id)
end
redis.call('DEL', KEYS[1])
return removed
"""


class RedisPlanningSessionsRepository:
    """Store planning hashes and a temporary account index for coordinated removal."""

    _KEY_PREFIX: ClassVar[str] = 'shifu:planning:'
    _ACCOUNT_INDEX_KEY_PREFIX: ClassVar[str] = 'shifu:planning:account:'
    _client: Redis
    _ttl_seconds: int
    _add_script: Script
    _update_script: Script
    _remove_script: Script
    _remove_by_account_script: Script
    _adapter: TypeAdapter[PlanningSession]

    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        if ttl_seconds < 1:
            raise ValueError('The planning TTL must be positive')
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._add_script = client.register_script(_ADD_SCRIPT)
        self._update_script = client.register_script(_UPDATE_SCRIPT)
        self._remove_script = client.register_script(_REMOVE_SCRIPT)
        self._remove_by_account_script = client.register_script(
            _REMOVE_BY_ACCOUNT_SCRIPT
        )
        self._adapter = TypeAdapter(PlanningSession)

    def add(self, session: PlanningSession) -> None:
        stored = self._add_script(
            keys=[
                self._key(session.id),
                self._account_index_key(session.account_id),
            ],
            args=[
                session.version,
                self._document(session),
                self._ttl_seconds,
                session.id,
            ],
        )
        if stored != 1:
            raise PlanningStateConflictError('Este planejamento já existe.')

    def find_by_id(self, planning_id: str) -> PlanningSession | None:
        values = cast(
            'list[str | None]',
            self._client.hmget(  # pyright: ignore[reportUnknownMemberType] - sync clients return an untyped union.
                self._key(planning_id), ['version', 'document']
            ),
        )
        version, document = values[0], values[1]
        if version is None or document is None:
            return None
        session = self._adapter.validate_json(document)
        # The hash field is the authority; the document copy may lag a write.
        session.version = int(version)
        return session

    def update(self, session: PlanningSession) -> bool:
        stored = self._update_script(
            keys=[
                self._key(session.id),
                self._account_index_key(session.account_id),
            ],
            args=[
                session.version,
                self._document(session),
                self._ttl_seconds,
                session.id,
            ],
        )
        if stored != 1:
            return False
        session.version += 1
        return True

    def remove(self, planning_id: str) -> bool:
        session = self.find_by_id(planning_id)
        if session is None:
            return False
        deleted = self._remove_script(
            keys=[
                self._key(planning_id),
                self._account_index_key(session.account_id),
            ],
            args=[planning_id],
        )
        return deleted > 0

    def remove_by_account_id(self, account_id: str) -> int:
        if not account_id.strip():
            raise ValueError('An account id is required to remove planning sessions.')
        removed = cast(
            'int',
            self._remove_by_account_script(
                keys=[self._account_index_key(account_id)],
                args=[self._KEY_PREFIX],
            ),
        )
        # Sessions created before the account index was introduced still need
        # erasure. Their remaining TTL is bounded, but account deletion is not
        # allowed to leave them available during that window.
        scan_iter = cast(
            'Callable[..., Iterable[str | bytes]]',
            self._client.scan_iter,
        )
        for raw_key in scan_iter(match=f'{self._KEY_PREFIX}*'):
            key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
            if key.startswith(self._ACCOUNT_INDEX_KEY_PREFIX):
                continue
            planning_id = key.removeprefix(self._KEY_PREFIX)
            session = self.find_by_id(planning_id)
            if session is not None and session.account_id == account_id:
                removed += int(self.remove(planning_id))
        return removed

    def _document(self, session: PlanningSession) -> str:
        return self._adapter.dump_json(session).decode()

    @classmethod
    def _key(cls, planning_id: str) -> str:
        return f'{cls._KEY_PREFIX}{planning_id}'

    @classmethod
    def _account_index_key(cls, account_id: str) -> str:
        account_key = sha256(account_id.encode('utf-8')).hexdigest()
        return f'{cls._ACCOUNT_INDEX_KEY_PREFIX}{account_key}'
