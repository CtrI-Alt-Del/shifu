from shifu.learning.core.domain.structures import GoalConfirmation
from shifu.learning.database.sqlalchemy.models import GoalConfirmationModel


class GoalConfirmationMapper:
    @staticmethod
    def to_domain(model: GoalConfirmationModel) -> GoalConfirmation:
        return GoalConfirmation(
            account_id=model.account_id,
            confirmation_key=model.confirmation_key,
            planning_id=model.planning_id,
            goal_id=model.goal_id,
            fingerprint=model.fingerprint,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(confirmation: GoalConfirmation) -> GoalConfirmationModel:
        return GoalConfirmationModel(
            account_id=confirmation.account_id,
            confirmation_key=confirmation.confirmation_key,
            planning_id=confirmation.planning_id,
            goal_id=confirmation.goal_id,
            fingerprint=confirmation.fingerprint,
            created_at=confirmation.created_at,
        )
