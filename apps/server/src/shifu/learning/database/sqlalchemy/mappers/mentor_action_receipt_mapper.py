from shifu.learning.core.domain.entities import MentorActionReceipt
from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
)
from shifu.learning.database.sqlalchemy.models import MentorActionReceiptModel


class MentorActionReceiptMapper:
    @staticmethod
    def to_domain(model: MentorActionReceiptModel) -> MentorActionReceipt:
        return MentorActionReceipt(
            id=model.id,
            account_id=model.account_id,
            confirmation_id=model.confirmation_id,
            operation=MentorActionOperation(model.operation),
            goal_id=model.goal_id,
            skill_id=model.skill_id,
            skill_experience_id=model.skill_experience_id,
            outcome=MentorActionOutcome(model.outcome),
            rejection_reason=(
                MentorActionRejectionReason(model.rejection_reason)
                if model.rejection_reason is not None
                else None
            ),
            request_fingerprint=model.request_fingerprint,
            resolved_at=model.resolved_at,
        )

    @staticmethod
    def to_model(receipt: MentorActionReceipt) -> MentorActionReceiptModel:
        return MentorActionReceiptModel(
            id=receipt.id,
            account_id=receipt.account_id,
            confirmation_id=receipt.confirmation_id,
            operation=receipt.operation.value,
            goal_id=receipt.goal_id,
            skill_id=receipt.skill_id,
            skill_experience_id=receipt.skill_experience_id,
            outcome=receipt.outcome.value,
            rejection_reason=(
                receipt.rejection_reason.value
                if receipt.rejection_reason is not None
                else None
            ),
            request_fingerprint=receipt.request_fingerprint,
            resolved_at=receipt.resolved_at,
        )
