from typing import cast

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    CodeAnswer,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.shared.core.domain.structures import CurriculumChoiceActivitySnapshot
from shifu.shared.database.sqlalchemy.serialization import Serialization


class ActivityAttemptMapper:
    @staticmethod
    def to_domain(model: ActivityAttemptModel) -> ActivityAttempt:
        grading_snapshot = ActivityAttemptMapper._deserialize_snapshot(
            model.grading_snapshot
        )
        return ActivityAttempt(
            id=model.id,
            skill_experience_id=model.skill_experience_id,
            competency_id=model.competency_id,
            activity_id=model.activity_id,
            kind=ActivityAttemptKind(model.kind),
            answers=ActivityAttemptMapper._deserialize_answers(
                model.answers,
                grading_snapshot,
            ),
            submitted_at=model.submitted_at,
            submission_key=model.submission_key,
            grading_snapshot=grading_snapshot,
        )

    @staticmethod
    def _deserialize_snapshot(
        value: object | None,
    ) -> CurriculumChoiceActivitySnapshot | None:
        if value is None:
            return None
        data = cast('dict[str, object]', value)
        normalized = {**data}
        normalized.setdefault('required_concept_ids', [])
        normalized.setdefault('activity_type', 'learning')
        questions = cast('list[dict[str, object]]', normalized.get('questions', []))
        normalized['questions'] = [
            {**question, 'concept_criteria': question.get('concept_criteria', [])}
            for question in questions
        ]
        return cast(
            'CurriculumChoiceActivitySnapshot',
            Serialization.deserialize_value(
                normalized, CurriculumChoiceActivitySnapshot
            ),
        )

    @staticmethod
    def _deserialize_answers(
        value: object,
        grading_snapshot: CurriculumChoiceActivitySnapshot | None,
    ) -> tuple[ActivityAnswer, ...]:
        serialized = cast('list[dict[str, object]]', value)
        questions = (
            {question.key: question for question in grading_snapshot.questions}
            if grading_snapshot is not None
            else {}
        )
        answers: list[ActivityAnswer] = []
        for item in serialized:
            question_key = cast('str', item['question_key'])
            question = questions.get(question_key)
            if question is not None and question.kind == 'single_choice':
                answers.append(
                    SingleChoiceAnswer(
                        question_key=question_key,
                        selected_option_key=cast('str', item['selected_option_key']),
                    )
                )
            elif question is not None and question.kind == 'multiple_selection':
                answers.append(
                    MultipleSelectionAnswer(
                        question_key=question_key,
                        selected_option_keys=tuple(
                            cast('list[str]', item['selected_option_keys'])
                        ),
                    )
                )
            elif 'source_code' in item:
                answers.append(
                    CodeAnswer(
                        question_key=question_key,
                        source_code=cast('str', item['source_code']),
                    )
                )
            elif 'selected_option_key' in item:
                answers.append(
                    SingleChoiceAnswer(
                        question_key=question_key,
                        selected_option_key=cast('str', item['selected_option_key']),
                    )
                )
            else:
                raise TypeError('Stored activity answer does not match its snapshot.')
        return tuple(answers)

    @staticmethod
    def to_model(attempt: ActivityAttempt) -> ActivityAttemptModel:
        return ActivityAttemptModel(
            id=attempt.id,
            skill_experience_id=attempt.skill_experience_id,
            competency_id=attempt.competency_id,
            activity_id=attempt.activity_id,
            kind=attempt.kind.value,
            answers=Serialization.serialize_value(attempt.answers),
            submitted_at=attempt.submitted_at,
            submission_key=attempt.submission_key,
            grading_snapshot=(
                Serialization.serialize_value(attempt.grading_snapshot)
                if attempt.grading_snapshot is not None
                else None
            ),
        )
