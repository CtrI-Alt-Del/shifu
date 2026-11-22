from dataclasses import replace
from decimal import Decimal

import pytest

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.errors import InvalidActivityError
from shifu.curriculum.core.domain.structures import (
    ChoiceConceptCriterion,
    CorrectnessEvaluationPart,
    EvaluationRule,
    ImageChoiceOption,
    ImageChoiceQuestion,
    QualitativeCriterion,
    QualitativeEvaluationPart,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import (
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumCodeInconclusiveCommentSnapshot,
    CurriculumCodeRubricCommentSnapshot,
    CurriculumCodeRubricCriterionSnapshot,
    CurriculumCodeRubricPartSnapshot,
    CurriculumImageChoiceOptionSnapshot,
    CurriculumImageChoiceQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
)


def _option(
    index: int,
    *,
    key: str | None = None,
    image_path: str | None = None,
    description: str | None = None,
    is_correct: bool = False,
    feedback: str | None = None,
) -> ImageChoiceOption:
    return ImageChoiceOption(
        key=key if key is not None else f'opt-{index:012x}',
        image_path=(
            image_path
            if image_path is not None
            else f'/curriculum/images/{index:016x}.webp'
        ),
        description=(
            description if description is not None else f'Descrição visual {index}'
        ),
        is_correct=is_correct,
        feedback=feedback if feedback is not None else f'Linha de retorno {index}',
    )


def _options(size: int = 4) -> tuple[ImageChoiceOption, ...]:
    return tuple(_option(index, is_correct=index == 1) for index in range(1, size + 1))


def _criterion() -> ChoiceConceptCriterion:
    return ChoiceConceptCriterion(
        concept_id='concept-1',
        criterion='Reconhece o ponto de cocção.',
        examples='Cebola macia e escura.',
        limits='Não mede a execução.',
        correct_score=100,
        incorrect_score=0,
    )


def _question(
    *,
    options: tuple[ImageChoiceOption, ...] | None = None,
    prompt: str = 'Qual destas cebolas está caramelizada?',
    correct_explanation: str = 'Acerto.',
    incorrect_explanation: str = 'Erro.',
    concept_criteria: tuple[ChoiceConceptCriterion, ...] | None = None,
) -> ImageChoiceQuestion:
    return ImageChoiceQuestion(
        key='image-1',
        prompt=prompt,
        options=options if options is not None else _options(),
        correct_explanation=correct_explanation,
        incorrect_explanation=incorrect_explanation,
        concept_criteria=(
            concept_criteria if concept_criteria is not None else (_criterion(),)
        ),
    )


def _activity(activity_type: ActivityType) -> Activity:
    question = _question()
    return Activity.create(
        id='activity-1',
        competency_id='competency-1',
        activity_type=activity_type,
        difficulty=ActivityDifficulty.EASY,
        title='Ponto de cocção',
        objective='Reconhecer o ponto de cocção.',
        questions=(question,),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(
                    question_key=question.key, weight_percentage=100
                ),
            )
        ),
    )


def _snapshot_options(size: int = 4) -> tuple[CurriculumImageChoiceOptionSnapshot, ...]:
    return tuple(
        CurriculumImageChoiceOptionSnapshot(
            key=option.key,
            image_path=option.image_path,
            description=option.description,
            is_correct=option.is_correct,
            feedback=option.feedback,
        )
        for option in _options(size)
    )


def _snapshot_question(
    *,
    options: tuple[CurriculumImageChoiceOptionSnapshot, ...] | None = None,
    concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...]
    | None = None,
) -> CurriculumImageChoiceQuestionSnapshot:
    return CurriculumImageChoiceQuestionSnapshot(
        key='image-1',
        kind='image_choice',
        prompt='Qual destas cebolas está caramelizada?',
        options=options if options is not None else _snapshot_options(),
        correct_explanation='Acerto.',
        incorrect_explanation='Erro.',
        concept_criteria=(
            concept_criteria
            if concept_criteria is not None
            else (
                CurriculumChoiceConceptCriterionSnapshot(
                    concept_id='concept-1',
                    criterion='Reconhece o ponto de cocção.',
                    examples='Cebola macia e escura.',
                    limits='Não mede a execução.',
                    correct_score=Decimal(100),
                    incorrect_score=Decimal(0),
                ),
            )
        ),
    )


def _activity_snapshot(activity_type: str) -> CurriculumLearningActivitySnapshot:
    question = _snapshot_question()
    other_questions = tuple(replace(question, key=f'image-{index}') for index in (2, 3))
    questions = (question, *other_questions)
    return CurriculumLearningActivitySnapshot(
        id='activity-1',
        competency_id='competency-1',
        difficulty='easy',
        title='Ponto de cocção',
        questions=questions,
        parts=tuple(
            CurriculumChoicePartSnapshot(
                question_key=item.key, weight_percentage=Decimal(weight)
            )
            for item, weight in zip(questions, (30, 40, 30), strict=True)
        ),
        required_concept_ids=(),
        activity_type=activity_type,
        schema_version=1,
        revision='revision-1',
    )


class TestImageChoiceQuestion:
    @pytest.mark.parametrize('size', (2, 3, 4))
    def test_should_accept_two_to_four_distinct_images_with_one_correct(
        self, size: int
    ) -> None:
        question = _question(options=_options(size))

        assert question.kind == 'image_choice'
        assert tuple(option.key for option in question.options) == tuple(
            f'opt-{index:012x}' for index in range(1, size + 1)
        )

    @pytest.mark.parametrize('size', (1, 5))
    def test_should_reject_a_count_of_images_outside_two_to_four(
        self, size: int
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _question(options=_options(size))

    @pytest.mark.parametrize(
        'options',
        (
            (_option(1), _option(2), _option(3)),
            (
                _option(1, is_correct=True),
                _option(2, is_correct=True),
                _option(3),
            ),
        ),
        ids=('no-correct', 'two-correct'),
    )
    def test_should_require_exactly_one_correct_image(
        self, options: tuple[ImageChoiceOption, ...]
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _question(options=options)

    @pytest.mark.parametrize(
        'options',
        (
            (_option(1, is_correct=True), _option(2, key='opt-000000000001')),
            (
                _option(1, is_correct=True),
                _option(2, image_path='/curriculum/images/0000000000000001.webp'),
            ),
            (_option(1, is_correct=True), _option(2, description='Descrição visual 1')),
            (_option(1, is_correct=True), _option(2, description='DESCRIÇÃO VISUAL 1')),
        ),
        ids=('key', 'path', 'description', 'description-case'),
    )
    def test_should_reject_repeated_keys_paths_or_descriptions(
        self, options: tuple[ImageChoiceOption, ...]
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _question(options=options)

    @pytest.mark.parametrize(
        'overrides',
        (
            {'description': ''},
            {'description': '   '},
            {'feedback': ''},
            {'key': ''},
            {'image_path': ''},
        ),
        ids=('description', 'blank-description', 'feedback', 'key', 'path'),
    )
    def test_should_reject_empty_option_text(self, overrides: dict[str, str]) -> None:
        with pytest.raises(InvalidActivityError):
            _option(1, is_correct=True, **overrides)

    @pytest.mark.parametrize(
        'image_path',
        (
            '/curriculum/images/onion-raw.webp',
            '/curriculum/images/000000000000001.webp',
            '/curriculum/images/00000000000000001.webp',
            '/curriculum/images/000000000000000g.webp',
            '/curriculum/images/0000000000000001.png',
            'curriculum/images/0000000000000001.webp',
            'https://example.com/curriculum/images/0000000000000001.webp',
            '/curriculum/images/0000000000000001.webp/extra',
        ),
        ids=(
            'descriptive',
            'short-hex',
            'long-hex',
            'non-hex',
            'other-extension',
            'relative',
            'absolute-url',
            'trailing-segment',
        ),
    )
    def test_should_reject_an_image_path_outside_the_opaque_pattern(
        self, image_path: str
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _option(1, is_correct=True, image_path=image_path)

    @pytest.mark.parametrize(
        'key',
        ('raw-onion', 'opt-00000000001', 'opt-0000000000001', 'opt-00000000000g'),
    )
    def test_should_reject_an_option_key_outside_the_opaque_pattern(
        self, key: str
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _option(1, is_correct=True, key=key)

    @pytest.mark.parametrize(
        'overrides',
        (
            {'prompt': ' '},
            {'correct_explanation': ''},
            {'incorrect_explanation': ' '},
            {'concept_criteria': ()},
        ),
        ids=('prompt', 'correct-explanation', 'incorrect-explanation', 'no-criteria'),
    )
    def test_should_reject_missing_question_text_or_concept_criteria(
        self, overrides: dict[str, object]
    ) -> None:
        with pytest.raises(InvalidActivityError):
            _question(**overrides)  # type: ignore[arg-type]

    def test_should_allow_the_format_only_in_learning_activities(self) -> None:
        assert _activity(ActivityType.LEARNING).questions == (_question(),)

        with pytest.raises(InvalidActivityError):
            _activity(ActivityType.DIAGNOSTIC)

    def test_should_require_a_correctness_part_for_the_image_question(self) -> None:
        question = _question()

        with pytest.raises(InvalidActivityError):
            Activity.create(
                id='activity-1',
                competency_id='competency-1',
                activity_type=ActivityType.LEARNING,
                difficulty=ActivityDifficulty.EASY,
                title='Ponto de cocção',
                objective='Reconhecer o ponto de cocção.',
                questions=(question,),
                evaluation_rule=EvaluationRule(
                    parts=(
                        QualitativeEvaluationPart(
                            question_key=question.key,
                            weight_percentage=100,
                            criteria=(
                                QualitativeCriterion(
                                    name='Critério',
                                    description='Descrição',
                                    weight_percentage=100,
                                ),
                            ),
                        ),
                    )
                ),
            )


class TestCurriculumImageChoiceSnapshot:
    @pytest.mark.parametrize('size', (2, 4))
    def test_should_mirror_the_accepted_image_counts(self, size: int) -> None:
        question = _snapshot_question(options=_snapshot_options(size))

        assert len(question.options) == size

    @pytest.mark.parametrize('size', (1, 5))
    def test_should_reject_image_counts_outside_two_to_four(self, size: int) -> None:
        with pytest.raises(ValidationError):
            _snapshot_question(options=_snapshot_options(size))

    def test_should_reject_zero_or_two_correct_images_repeats_and_missing_criteria(
        self,
    ) -> None:
        options = _snapshot_options()
        no_correct = tuple(replace(option, is_correct=False) for option in options)
        two_correct = tuple(replace(option, is_correct=True) for option in options[:2])
        repeated_description = (
            options[0],
            replace(options[1], description=options[0].description.upper()),
        )
        repeated_path = (
            options[0],
            replace(options[1], image_path=options[0].image_path),
        )
        repeated_key = (options[0], replace(options[1], key=options[0].key))
        for invalid in (
            no_correct,
            two_correct,
            repeated_description,
            repeated_path,
            repeated_key,
        ):
            with pytest.raises(ValidationError):
                _snapshot_question(options=invalid)

        with pytest.raises(ValidationError):
            _snapshot_question(concept_criteria=())

    @pytest.mark.parametrize(
        'overrides',
        (
            {'image_path': '/curriculum/images/onion-raw.webp'},
            {'key': 'raw-onion'},
            {'description': ''},
            {'feedback': ' '},
        ),
        ids=('path', 'key', 'description', 'feedback'),
    )
    def test_should_reject_an_invalid_snapshot_option(
        self, overrides: dict[str, str]
    ) -> None:
        with pytest.raises(ValidationError):
            replace(_snapshot_options()[0], **overrides)

    def test_should_allow_the_snapshot_only_in_learning_activities(self) -> None:
        assert len(_activity_snapshot('learning').questions) == 3

        with pytest.raises(ValidationError):
            _activity_snapshot('diagnostic')

    def test_should_require_a_choice_part_for_the_image_snapshot(self) -> None:
        snapshot = _activity_snapshot('learning')
        rubric_part = CurriculumCodeRubricPartSnapshot(
            question_key='image-3',
            weight_percentage=Decimal(30),
            criteria=(
                CurriculumCodeRubricCriterionSnapshot(
                    key='render',
                    name='Renderização',
                    description='Renderiza',
                    weight_percentage=100,
                    required=True,
                    fixed_comments=tuple(
                        CurriculumCodeRubricCommentSnapshot(
                            id=f'level-{level}', level=level, text=f'Nível {level}'
                        )
                        for level in (0, 25, 50, 75, 100)
                    ),
                    inconclusive_comment=CurriculumCodeInconclusiveCommentSnapshot(
                        id='inconclusive', text='Inconclusivo'
                    ),
                ),
            ),
        )

        with pytest.raises(ValidationError):
            replace(snapshot, parts=(*snapshot.parts[:2], rubric_part))
