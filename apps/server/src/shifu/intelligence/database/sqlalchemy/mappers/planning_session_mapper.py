from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.database.sqlalchemy.models import PlanningSessionModel


class PlanningSessionMapper:
    @staticmethod
    def to_domain(model: PlanningSessionModel) -> PlanningSession:
        return PlanningSession(
            id=model.id,
            account_id=model.account_id,
            initial_intent=model.initial_intent,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(planning_session: PlanningSession) -> PlanningSessionModel:
        return PlanningSessionModel(
            id=planning_session.id,
            account_id=planning_session.account_id,
            initial_intent=planning_session.initial_intent,
            created_at=planning_session.created_at,
        )
