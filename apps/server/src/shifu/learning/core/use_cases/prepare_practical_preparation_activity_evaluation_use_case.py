from shifu.learning.core.domain.enums import (
    ActivityEvaluationStatus,
    PracticePhotoOwnerKind,
    PracticePhotoState,
)
from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    PracticalPreparationAnswer,
    PreparedPracticalPreparationEvaluation,
    PreparedPracticePhoto,
)
from shifu.learning.core.interfaces import LearningDatabase
from shifu.shared.core.domain.structures import (
    CurriculumLearningActivitySnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
)


class PreparePracticalPreparationActivityEvaluationUseCase:
    """Freeze what the assessor needs: the rubric and photo references, never bytes."""

    def __init__(self, learning_database: LearningDatabase) -> None:
        self._learning_database = learning_database

    def execute(
        self, attempt_id: str, run_id: str
    ) -> PreparedPracticalPreparationEvaluation | None:
        with self._learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(attempt_id)
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt_id
            )
            if (
                attempt is None
                or evaluation is None
                or evaluation.run_id != run_id
                or evaluation.status is not ActivityEvaluationStatus.PENDING
                or not isinstance(
                    attempt.grading_snapshot, CurriculumLearningActivitySnapshot
                )
            ):
                return None

            question = next(
                (
                    item
                    for item in attempt.grading_snapshot.questions
                    if isinstance(item, CurriculumPracticalPreparationQuestionSnapshot)
                ),
                None,
            )
            if question is None or not any(
                isinstance(answer, PracticalPreparationAnswer)
                and answer.question_key == question.key
                for answer in attempt.answers
            ):
                raise EvaluationUnavailableError

            by_record = {
                photo.record_key: photo
                for photo in repositories.practice_photos.list_for_attempt(attempt_id)
                if photo.owner_kind is PracticePhotoOwnerKind.ATTEMPT
                and photo.state is PracticePhotoState.READY
            }
            if set(by_record) != {record.key for record in question.records}:
                raise EvaluationUnavailableError

            # The assessor receives the photos in the order of the Curriculum records.
            photos = tuple(by_record[record.key] for record in question.records)

            return PreparedPracticalPreparationEvaluation(
                attempt_id=attempt_id,
                run_id=run_id,
                question=question,
                photos=tuple(
                    PreparedPracticePhoto(
                        record_key=photo.record_key,
                        object_key=photo.object_key,
                        media_type=photo.media_type,
                    )
                    for photo in photos
                ),
            )
