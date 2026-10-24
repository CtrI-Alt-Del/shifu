from datetime import UTC, datetime
from typing import ClassVar

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.gamification.core.domain.entities import ActivityXpRecognition


class ActivityXpRecognitionFaker:
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        activity_id: str | None = None,
        attempt_id: str | None = None,
        granted_xp: int = 0,
        xp_grant_id: str | None = None,
        occurred_at: datetime | None = None,
        recognized_at: datetime | None = None,
    ) -> ActivityXpRecognition:
        now = datetime.now(UTC)
        return ActivityXpRecognition(
            id=id if id is not None else cls._id_provider.generate(),
            account_id=account_id
            if account_id is not None
            else cls._id_provider.generate(),
            activity_id=activity_id
            if activity_id is not None
            else cls._id_provider.generate(),
            attempt_id=attempt_id
            if attempt_id is not None
            else cls._id_provider.generate(),
            granted_xp=granted_xp,
            xp_grant_id=xp_grant_id
            if xp_grant_id is not None
            else (cls._id_provider.generate() if granted_xp else None),
            occurred_at=occurred_at or now,
            recognized_at=recognized_at or now,
        )
