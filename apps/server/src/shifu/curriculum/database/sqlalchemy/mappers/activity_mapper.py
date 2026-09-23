from typing import cast

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    CodeQuestion,
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    MultipleSelectionQuestion,
    QualitativeEvaluationPart,
    SingleChoiceQuestion,
    TestCasesEvaluationPart,
)
from shifu.curriculum.database.sqlalchemy.models import ActivityModel
from shifu.shared.database.sqlalchemy.serialization import Serialization


class ActivityMapper:
    @staticmethod
    def to_domain(model: ActivityModel) -> Activity:
        raw_questions = cast('list[dict[str, object]]', model.questions)
        questions = tuple(
            ActivityMapper._question_from_data(question) for question in raw_questions
        )
        return Activity(
            id=model.id,
            competency_id=model.competency_id,
            activity_type=ActivityType(model.activity_type),
            difficulty=ActivityDifficulty(model.difficulty),
            title=model.title,
            objective=model.objective,
            questions=questions,
            evaluation_rule=EvaluationRule(
                parts=cast(
                    'tuple[CorrectnessEvaluationPart | TestCasesEvaluationPart | QualitativeEvaluationPart, ...]',
                    Serialization.deserialize_value(
                        cast('dict[str, object]', model.evaluation_rule)['parts'],
                        tuple[
                            CorrectnessEvaluationPart
                            | TestCasesEvaluationPart
                            | QualitativeEvaluationPart,
                            ...,
                        ],
                    ),
                )
            ),
        )

    @staticmethod
    def _question_from_data(
        data: dict[str, object],
    ) -> SingleChoiceQuestion | MultipleSelectionQuestion | CodeQuestion:
        if 'options' not in data:
            return cast(
                'CodeQuestion',
                Serialization.deserialize_value(data, CodeQuestion),
            )

        options = cast(
            'tuple[ChoiceOption, ...]',
            Serialization.deserialize_value(data['options'], tuple[ChoiceOption, ...]),
        )
        key = cast('str', data['key'])
        prompt = cast('str', data['prompt'])
        correct_explanation = cast('str | None', data.get('correct_explanation'))
        incorrect_explanation = cast('str | None', data.get('incorrect_explanation'))
        if sum(option.is_correct for option in options) == 1:
            return SingleChoiceQuestion(
                key=key,
                prompt=prompt,
                options=options,
                correct_explanation=correct_explanation,
                incorrect_explanation=incorrect_explanation,
            )
        return MultipleSelectionQuestion(
            key=key,
            prompt=prompt,
            options=options,
            correct_explanation=correct_explanation,
            incorrect_explanation=incorrect_explanation,
        )

    @staticmethod
    def to_model(activity: Activity) -> ActivityModel:
        return ActivityModel(
            id=activity.id,
            competency_id=activity.competency_id,
            activity_type=activity.activity_type.value,
            difficulty=activity.difficulty.value,
            title=activity.title,
            objective=activity.objective,
            questions=Serialization.serialize_value(activity.questions),
            evaluation_rule=Serialization.serialize_value(activity.evaluation_rule),
        )
