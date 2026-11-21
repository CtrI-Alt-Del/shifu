from typing import ClassVar

from shifu.communication.core.domain.errors import InvalidCommunicationError
from shifu.shared.core.domain.structures import structure


@structure
class StreakReminderMessage:
    TITLE: ClassVar[str] = 'Shifu'
    URL: ClassVar[str] = '/'
    TAG: ClassVar[str] = 'shifu-streak-reminder'

    title: str
    body: str
    url: str
    tag: str

    @classmethod
    def for_streak(cls, streak_days: int) -> 'StreakReminderMessage':
        if streak_days < 1:
            raise InvalidCommunicationError
        unit = 'dia' if streak_days == 1 else 'dias'
        return cls(
            title=cls.TITLE,
            body=(
                f'Sua sequência de {streak_days} {unit} termina hoje'
                ' — pratique para mantê-la'
            ),
            url=cls.URL,
            tag=cls.TAG,
        )
