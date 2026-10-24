from datetime import UTC, datetime
from typing import ClassVar

from faker import Faker

from shifu.fakers.shared.id_provider_faker import IdProviderFaker
from shifu.learning.core.domain.entities import MentorActionReceipt
from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)


class MentorActionReceiptFaker:
    _faker: ClassVar[Faker] = Faker('pt_BR')
    _id_provider: ClassVar[IdProviderFaker] = IdProviderFaker()

    @classmethod
    def fake(
        cls,
        *,
        id: str | None = None,
        account_id: str | None = None,
        confirmation_id: str | None = None,
        operation: MentorActionOperation = MentorActionOperation.ADD_SKILL,
        goal_id: str | None = None,
        skill_id: str | None = None,
        skill_experience_id: str | None = None,
        outcome: MentorActionOutcome = MentorActionOutcome.ADDED,
        rejection_reason: MentorActionRejectionReason | None = None,
        request_fingerprint: str | None = None,
        resolved_at: datetime | None = None,
    ) -> MentorActionReceipt:
        reason = rejection_reason
        if outcome is MentorActionOutcome.REJECTED and reason is None:
            reason = MentorActionRejectionReason.GOAL_UNAVAILABLE

        return MentorActionReceipt.create(
            id=id or cls._id_provider.generate(),
            account_id=account_id or cls._id_provider.generate(),
            confirmation_id=confirmation_id or cls._id_provider.generate(),
            operation=operation,
            goal_id=goal_id or cls._id_provider.generate(),
            skill_id=skill_id or cls._id_provider.generate(),
            skill_experience_id=(
                skill_experience_id
                if skill_experience_id is not None
                else cls._id_provider.generate()
            ),
            outcome=outcome,
            rejection_reason=reason,
            request_fingerprint=request_fingerprint or cls._faker.sha256(),
            resolved_at=resolved_at or cls._faker.date_time(tzinfo=UTC),
        )
