from typing import Literal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures import VerifiedOrdering
from shifu.shared.core.domain.entities import entity
from shifu.shared.core.domain.structures import CurriculumLearningActivitySnapshot


@entity
class OrderingPassage:
    id: str
    skill_experience_id: str
    activity_id: str
    passage_key: str
    activity_revision: str
    grading_snapshot: CurriculumLearningActivitySnapshot
    verified_orderings: tuple[VerifiedOrdering, ...]
    status: Literal['active', 'consumed']

    @classmethod
    def create(
        cls,
        *,
        id: str,
        skill_experience_id: str,
        activity_id: str,
        passage_key: str,
        activity_revision: str,
        grading_snapshot: CurriculumLearningActivitySnapshot,
    ) -> 'OrderingPassage':
        if (
            not id
            or not skill_experience_id
            or not activity_id
            or not passage_key
            or not activity_revision
            or grading_snapshot.id != activity_id
            or grading_snapshot.revision != activity_revision
            or grading_snapshot.activity_type != 'learning'
        ):
            raise InvalidAttemptError

        return cls(
            id=id,
            skill_experience_id=skill_experience_id,
            activity_id=activity_id,
            passage_key=passage_key,
            activity_revision=activity_revision,
            grading_snapshot=grading_snapshot,
            verified_orderings=(),
            status='active',
        )

    def add_verified(self, item: VerifiedOrdering) -> None:
        if self.status != 'active' or any(
            existing.question_key == item.question_key
            for existing in self.verified_orderings
        ):
            raise InvalidAttemptError
        self.verified_orderings = (*self.verified_orderings, item)

    def consume(self) -> None:
        if self.status != 'active':
            raise InvalidAttemptError
        self.status = 'consumed'
