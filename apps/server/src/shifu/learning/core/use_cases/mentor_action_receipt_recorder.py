import hashlib
import json
from collections.abc import Mapping
from datetime import UTC

from shifu.learning.core.domain.entities import MentorActionReceipt
from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)
from shifu.learning.core.domain.errors import MentorActionConflictError
from shifu.learning.core.domain.events import (
    MentorSkillActionResolvedEvent,
    MentorSkillActionResolvedPayload,
)
from shifu.learning.core.domain.structures import MentorActionResolution
from shifu.learning.core.interfaces import LearningDatabaseRepositories
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class MentorActionReceiptRecorder:
    """Shared receipt, replay and outcome-event steps of the Mentor action use cases."""

    def __init__(
        self,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
    ) -> None:
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider

    @staticmethod
    def fingerprint(request: Mapping[str, str]) -> str:
        canonical = json.dumps(
            dict(request),
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    @staticmethod
    def replay(
        repositories: LearningDatabaseRepositories,
        account_id: str,
        confirmation_id: str,
        fingerprint: str,
    ) -> MentorActionResolution | None:
        receipt = repositories.mentor_action_receipts.find_by_confirmation_id(
            account_id, confirmation_id
        )
        if receipt is None:
            return None
        if receipt.request_fingerprint != fingerprint:
            raise MentorActionConflictError
        return MentorActionReceiptRecorder._resolution_of(receipt)

    def record(
        self,
        repositories: LearningDatabaseRepositories,
        *,
        account_id: str,
        confirmation_id: str,
        operation: MentorActionOperation,
        goal_id: str,
        skill_id: str | None,
        skill_experience_id: str | None,
        outcome: MentorActionOutcome,
        rejection_reason: MentorActionRejectionReason | None,
        fingerprint: str,
    ) -> MentorActionResolution:
        now = self._clock_provider.now()
        receipt = MentorActionReceipt.create(
            id=self._identifier_provider.generate(),
            account_id=account_id,
            confirmation_id=confirmation_id,
            operation=operation,
            goal_id=goal_id,
            skill_id=skill_id,
            skill_experience_id=skill_experience_id,
            outcome=outcome,
            rejection_reason=rejection_reason,
            request_fingerprint=fingerprint,
            resolved_at=now,
        )
        if repositories.mentor_action_receipts.try_add(receipt):
            repositories.events.add(
                MentorSkillActionResolvedEvent(
                    payload=MentorSkillActionResolvedPayload(
                        account_id=account_id,
                        confirmation_id=confirmation_id,
                        operation=operation.value,
                        outcome=outcome.value,
                        rejection_reason=(
                            rejection_reason.value
                            if rejection_reason is not None
                            else None
                        ),
                        goal_id=goal_id,
                        skill_id=skill_id,
                        skill_experience_id=skill_experience_id,
                        resolved_at=now.astimezone(UTC)
                        .isoformat()
                        .replace('+00:00', 'Z'),
                    )
                )
            )
            return self._resolution_of(receipt)

        winner = repositories.mentor_action_receipts.find_by_confirmation_id(
            account_id, confirmation_id
        )
        effect_performed = outcome in {
            MentorActionOutcome.ADDED,
            MentorActionOutcome.REMOVED,
        }
        if (
            winner is None
            or effect_performed
            or winner.request_fingerprint != fingerprint
        ):
            raise MentorActionConflictError
        return self._resolution_of(winner)

    @staticmethod
    def _resolution_of(receipt: MentorActionReceipt) -> MentorActionResolution:
        return MentorActionResolution(
            confirmation_id=receipt.confirmation_id,
            operation=receipt.operation,
            outcome=receipt.outcome,
            rejection_reason=receipt.rejection_reason,
            goal_id=receipt.goal_id,
            skill_id=receipt.skill_id,
            skill_experience_id=receipt.skill_experience_id,
        )
