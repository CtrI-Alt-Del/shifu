from typing import cast

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    CodeQuestion,
    CodeRubricEvaluationPart,
    ChoiceConceptCriterion,
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    JavascriptStdinQuestion,
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
                parts=tuple(
                    ActivityMapper._part_from_data(part, questions)
                    for part in cast(
                        'list[dict[str, object]]',
                        cast('dict[str, object]', model.evaluation_rule)['parts'],
                    )
                )
            ),
            required_concept_ids=tuple(cast('list[str]', model.required_concept_ids)),
        )

    @staticmethod
    def _question_from_data(
        data: dict[str, object],
    ) -> (
        SingleChoiceQuestion
        | MultipleSelectionQuestion
        | CodeQuestion
        | JavascriptStdinQuestion
    ):
        if data.get('kind') == 'javascript_stdin':
            return cast(
                'JavascriptStdinQuestion',
                Serialization.deserialize_value(data, JavascriptStdinQuestion),
            )
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
        concept_criteria = cast(
            'tuple[ChoiceConceptCriterion, ...]',
            Serialization.deserialize_value(
                data.get('concept_criteria', []), tuple[ChoiceConceptCriterion, ...]
            ),
        )
        if sum(option.is_correct for option in options) == 1:
            return SingleChoiceQuestion(
                key=key,
                prompt=prompt,
                options=options,
                correct_explanation=correct_explanation,
                incorrect_explanation=incorrect_explanation,
                concept_criteria=concept_criteria,
            )
        return MultipleSelectionQuestion(
            key=key,
            prompt=prompt,
            options=options,
            correct_explanation=correct_explanation,
            incorrect_explanation=incorrect_explanation,
            concept_criteria=concept_criteria,
        )

    @staticmethod
    def _part_from_data(
        data: dict[str, object],
        questions: tuple[
            SingleChoiceQuestion
            | MultipleSelectionQuestion
            | CodeQuestion
            | JavascriptStdinQuestion,
            ...,
        ],
    ) -> (
        CorrectnessEvaluationPart
        | TestCasesEvaluationPart
        | QualitativeEvaluationPart
        | CodeRubricEvaluationPart
    ):
        question = next(
            (item for item in questions if item.key == data.get('question_key')), None
        )
        criteria = data.get('criteria')
        if isinstance(criteria, list) and criteria:
            first = cast('object', criteria[0])
            part_type = (
                CodeRubricEvaluationPart
                if isinstance(first, dict) and 'fixed_comments' in first
                else QualitativeEvaluationPart
            )
        elif 'criteria' in data:
            part_type = QualitativeEvaluationPart
        elif isinstance(question, CodeQuestion):
            part_type = TestCasesEvaluationPart
        else:
            part_type = CorrectnessEvaluationPart
        return cast(
            'CorrectnessEvaluationPart | TestCasesEvaluationPart | QualitativeEvaluationPart | CodeRubricEvaluationPart',
            Serialization.deserialize_value(data, part_type),
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
            required_concept_ids=list(activity.required_concept_ids),
        )
