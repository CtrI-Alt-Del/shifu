from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import (
    ActivityDifficulty,
    ActivityType,
)
from shifu.curriculum.core.domain.structures import (
    ActivityQuestion,
    ChoiceOption,
    CorrectnessEvaluationPart,
    EvaluationRule,
    SingleChoiceQuestion,
)
from shifu.fakers.shared.id_provider_faker import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class ActivityFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @staticmethod
    def _fake_questions(faker: Faker) -> tuple[ActivityQuestion, ...]:
        return tuple(
            SingleChoiceQuestion(
                key=key,
                prompt=faker.sentence(nb_words=7).rstrip('.') + '?',
                options=(
                    ChoiceOption(key='correct', text=faker.word(), is_correct=True),
                    ChoiceOption(
                        key='incorrect',
                        text=faker.word(),
                        is_correct=False,
                    ),
                ),
            )
            for key in ('question-one', 'question-two', 'question-three')
        )

    @staticmethod
    def _fake_evaluation_rule() -> EvaluationRule:
        return EvaluationRule(
            parts=tuple(
                CorrectnessEvaluationPart(
                    question_key=key,
                    weight_percentage=weight,
                )
                for key, weight in (
                    ('question-one', 34),
                    ('question-two', 33),
                    ('question-three', 33),
                )
            ),
        )

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        competency_id: str | None = None,
        activity_type: ActivityType = ActivityType.LEARNING,
        difficulty: ActivityDifficulty = ActivityDifficulty.EASY,
        title: str | None = None,
        objective: str | None = None,
        questions: tuple[ActivityQuestion, ...] | None = None,
        evaluation_rule: EvaluationRule | None = None,
    ) -> Activity:
        return Activity(
            id=id or cls._id_provider.generate(),
            competency_id=competency_id or cls._id_provider.generate(),
            activity_type=activity_type,
            difficulty=difficulty,
            title=title or cls._faker.sentence(nb_words=6).rstrip('.'),
            objective=objective or cls._faker.paragraph(),
            questions=questions or cls._fake_questions(cls._faker),
            evaluation_rule=evaluation_rule or cls._fake_evaluation_rule(),
        )

    @classmethod
    def fake_many(cls, count: int = 10, **overrides: object) -> list[Activity]:
        fake = cast('Callable[..., Activity]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
