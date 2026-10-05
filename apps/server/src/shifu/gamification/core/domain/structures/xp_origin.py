from shifu.gamification.core.domain.enums.xp_source import XpSource
from shifu.gamification.core.domain.errors import InvalidGamificationError
from shifu.shared.core.domain.structures import EnumValue, NonEmptyText, structure


@structure
class XpOrigin:
    source: XpSource
    reference_id: str
    label: str
    goal_id: str | None = None
    skill_experience_id: str | None = None

    def __post_init__(self) -> None:
        EnumValue.create(self.source, XpSource, error_type=InvalidGamificationError)
        NonEmptyText.create(self.reference_id, error_type=InvalidGamificationError)
        NonEmptyText.create(self.label, error_type=InvalidGamificationError)
        for reference in (self.goal_id, self.skill_experience_id):
            if reference is not None:
                NonEmptyText.create(reference, error_type=InvalidGamificationError)
