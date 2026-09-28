from typing import cast

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.core.domain.structures import (
    ActivityAnswer,
    CodeAnswer,
    CodeSubmittedFile,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.database.sqlalchemy.models import ActivityAttemptModel
from shifu.shared.core.domain.structures import (
    CurriculumChoiceActivitySnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumJavascriptStdinQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
)
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
            diagnostic_run_id=model.diagnostic_run_id,
        )

    @staticmethod
    def _deserialize_snapshot(
        value: object | None,
    ) -> CurriculumChoiceActivitySnapshot | CurriculumLearningActivitySnapshot | None:
        if value is None:
            return None
        data = cast('dict[str, object]', value)
        normalized = {**data}
        normalized.setdefault('required_concept_ids', [])
        normalized.setdefault('activity_type', 'learning')
        # Persisted attempts created before diagnostic revisions used the
        # ordinary activity revision field. Keep that historical value while
        # accepting the new opaque diagnostic revision when present.
        normalized.setdefault('diagnostic_revision', None)
        questions = cast('list[dict[str, object]]', normalized.get('questions', []))
        normalized['questions'] = [
            {**question, 'concept_criteria': question.get('concept_criteria', [])}
            for question in questions
        ]
        if 'schema_version' in normalized and 'revision' in normalized:
            mixed_questions = tuple(
                Serialization.deserialize_value(
                    question,
                    CurriculumJavascriptStdinQuestionSnapshot
                    if question.get('kind') == 'javascript_stdin'
                    else CurriculumChoiceQuestionSnapshot,
                )
                for question in normalized['questions']
            )
            mixed_parts = tuple(
                Serialization.deserialize_value(
                    part,
                    CurriculumCodeRubricPartSnapshot
                    if 'criteria' in part
                    else CurriculumChoicePartSnapshot,
                )
                for part in cast('list[dict[str, object]]', normalized['parts'])
            )
            return CurriculumLearningActivitySnapshot(
                id=cast('str', normalized['id']),
                competency_id=cast('str', normalized['competency_id']),
                difficulty=cast('str', normalized['difficulty']),
                title=cast('str', normalized['title']),
                questions=cast(
                    'tuple[CurriculumChoiceQuestionSnapshot | CurriculumJavascriptStdinQuestionSnapshot, ...]',
                    mixed_questions,
                ),
                parts=cast(
                    'tuple[CurriculumChoicePartSnapshot | CurriculumCodeRubricPartSnapshot, ...]',
                    mixed_parts,
                ),
                required_concept_ids=tuple(
                    cast('list[str]', normalized['required_concept_ids'])
                ),
                activity_type=cast('str', normalized['activity_type']),
                schema_version=cast('int', normalized['schema_version']),
                revision=cast('str', normalized['revision']),
                diagnostic_revision=cast(
                    'str | None', normalized['diagnostic_revision']
                ),
            )
        return cast(
            'CurriculumChoiceActivitySnapshot',
            Serialization.deserialize_value(
                normalized, CurriculumChoiceActivitySnapshot
            ),
        )

    @staticmethod
    def _deserialize_answers(
        value: object,
        grading_snapshot: CurriculumChoiceActivitySnapshot
        | CurriculumLearningActivitySnapshot
        | None,
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
            if 'files' in item:
                serialized_files = cast('list[dict[str, str]]', item['files'])
                answers.append(
                    CodeAnswer(
                        question_key=question_key,
                        files=tuple(
                            CodeSubmittedFile(
                                path=file['path'], content=file['content']
                            )
                            for file in serialized_files
                        ),
                    )
                )
                continue
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
            diagnostic_run_id=attempt.diagnostic_run_id,
        )
