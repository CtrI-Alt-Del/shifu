from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from faker import Faker

from shifu.learning.core.domain.entities import ActivityAttempt
from shifu.learning.core.domain.enums import ActivityAttemptKind
from shifu.learning.core.domain.structures import ActivityAnswer, SingleChoiceAnswer
from shifu.shared.core.interfaces.fakers import IdProviderFaker

if TYPE_CHECKING:
    from collections.abc import Callable


class ActivityAttemptFaker:
    _faker: Faker = Faker('pt_BR')
    _id_provider: IdProviderFaker = IdProviderFaker()

    @classmethod
    def _fake_answers(cls) -> tuple[ActivityAnswer, ...]:
        return tuple(
            SingleChoiceAnswer(
                question_key=f'question-{position}',
                selected_option_key=cls._faker.word(),
            )
            for position in range(1, 4)
        )

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        skill_experience_id: str | None = None,
        competency_id: str | None = None,
        activity_id: str | None = None,
        kind: ActivityAttemptKind = ActivityAttemptKind.LEARNING,
        answers: tuple[ActivityAnswer, ...] | None = None,
        submitted_at: datetime | None = None,
    ) -> ActivityAttempt:
        return ActivityAttempt(
            id=id or cls._id_provider.generate(),
            skill_experience_id=skill_experience_id or cls._id_provider.generate(),
            competency_id=competency_id or cls._id_provider.generate(),
            activity_id=activity_id or cls._id_provider.generate(),
            kind=kind,
            answers=answers if answers is not None else cls._fake_answers(),
            submitted_at=submitted_at or cls._faker.date_time(tzinfo=UTC),
        )

    @classmethod
    def fake_many(
        cls,
        count: int = 10,
        **overrides: object,
    ) -> list[ActivityAttempt]:
        fake = cast('Callable[..., ActivityAttempt]', cls.fake)
        return [fake(**overrides) for _ in range(count)]
