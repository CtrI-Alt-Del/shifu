from shifu.learning.core.domain.enums import PracticeDraftStatus
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.shared.core.domain.entities import entity

MAX_REFLECTION_LENGTH = 4000


@entity
class PracticeDraft:
    id: str
    skill_experience_id: str
    activity_id: str
    reflection: str
    revision: int
    status: PracticeDraftStatus

    @classmethod
    def create(
        cls,
        *,
        id: str,
        skill_experience_id: str,
        activity_id: str,
    ) -> 'PracticeDraft':
        if not id or not skill_experience_id or not activity_id:
            raise InvalidAttemptError

        return cls(
            id=id,
            skill_experience_id=skill_experience_id,
            activity_id=activity_id,
            reflection='',
            revision=0,
            status=PracticeDraftStatus.ACTIVE,
        )

    def bump_revision(self) -> None:
        self._require_active()
        self.revision += 1

    def write_reflection(self, reflection: str) -> None:
        self._require_active()
        if len(reflection) > MAX_REFLECTION_LENGTH:
            raise InvalidAttemptError
        self.reflection = reflection
        self.revision += 1

    def consume(self) -> None:
        self._require_active()
        self.status = PracticeDraftStatus.CONSUMED

    def _require_active(self) -> None:
        if self.status is not PracticeDraftStatus.ACTIVE:
            raise InvalidAttemptError
