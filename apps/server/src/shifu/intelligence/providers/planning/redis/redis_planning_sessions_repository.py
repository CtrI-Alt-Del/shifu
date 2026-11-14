from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from pydantic import TypeAdapter

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.errors import PlanningStateConflictError

if TYPE_CHECKING:
    from redis import Redis
    from redis.commands.core import Script

_ADD_SCRIPT = """
local key = KEYS[1]
if redis.call('EXISTS', key) == 1 then
  return 0
end
redis.call('HSET', key, 'version', ARGV[1], 'document', ARGV[2])
redis.call('EXPIRE', key, tonumber(ARGV[3]))
return 1
"""

_UPDATE_SCRIPT = """
local key = KEYS[1]
local current = redis.call('HGET', key, 'version')
if current == false then
  return 0
end
if tonumber(current) ~= tonumber(ARGV[1]) then
  return 0
end
redis.call('HSET', key, 'version', tostring(tonumber(ARGV[1]) + 1), 'document', ARGV[2])
redis.call('EXPIRE', key, tonumber(ARGV[3]))
return 1
"""


class RedisPlanningSessionsRepository:
    """One hash per planning: `version` for compare-and-set and the JSON document."""

    _KEY_PREFIX: ClassVar[str] = 'shifu:planning:'
    _client: Redis
    _ttl_seconds: int
    _add_script: Script
    _update_script: Script
    _adapter: TypeAdapter[PlanningSession]

    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        if ttl_seconds < 1:
            raise ValueError('The planning TTL must be positive')
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._add_script = client.register_script(_ADD_SCRIPT)
        self._update_script = client.register_script(_UPDATE_SCRIPT)
        self._adapter = TypeAdapter(PlanningSession)

    def add(self, session: PlanningSession) -> None:
        stored = self._add_script(
            keys=[self._key(session.id)],
            args=[session.version, self._document(session), self._ttl_seconds],
        )
        if stored != 1:
            raise PlanningStateConflictError('Este planejamento já existe.')

    def find_by_id(self, planning_id: str) -> PlanningSession | None:
        values = cast(
            'list[str | None]',
            self._client.hmget(self._key(planning_id), ['version', 'document']),  # pyright: ignore[reportUnknownMemberType] - redis-py returns an untyped union for sync clients.
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
            keys=[self._key(session.id)],
            args=[session.version, self._document(session), self._ttl_seconds],
        )
        if stored != 1:
            return False
        session.version += 1
        return True

    def remove(self, planning_id: str) -> bool:
        deleted = self._client.delete(self._key(planning_id))
        return deleted > 0

    def _document(self, session: PlanningSession) -> str:
        return self._adapter.dump_json(session).decode()

    @classmethod
    def _key(cls, planning_id: str) -> str:
        return f'{cls._KEY_PREFIX}{planning_id}'
