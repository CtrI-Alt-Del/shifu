from shifu.gamification.core.domain.entities import RewardedMilestone
from shifu.gamification.core.domain.enums import MilestoneKind
from shifu.gamification.database.sqlalchemy.models import RewardedMilestoneModel


class RewardedMilestoneMapper:
    @staticmethod
    def to_domain(model: RewardedMilestoneModel) -> RewardedMilestone:
        return RewardedMilestone(
            id=model.id,
            account_id=model.account_id,
            fact_id=model.fact_id,
            kind=MilestoneKind(model.kind),
            subject_id=model.subject_id,
            xp_grant_id=model.xp_grant_id,
            occurred_at=model.occurred_at,
            rewarded_at=model.rewarded_at,
        )

    @staticmethod
    def to_model(milestone: RewardedMilestone) -> RewardedMilestoneModel:
        return RewardedMilestoneModel(
            id=milestone.id,
            account_id=milestone.account_id,
            fact_id=milestone.fact_id,
            kind=milestone.kind.value,
            subject_id=milestone.subject_id,
            xp_grant_id=milestone.xp_grant_id,
            occurred_at=milestone.occurred_at,
            rewarded_at=milestone.rewarded_at,
        )
