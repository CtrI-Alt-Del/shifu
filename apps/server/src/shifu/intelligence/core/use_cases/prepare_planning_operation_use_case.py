from shifu.intelligence.core.domain.enums import PlanningSessionStatus
from shifu.intelligence.core.domain.structures import PlanningOperationContext
from shifu.intelligence.core.interfaces import PlanningSessionsRepository
from shifu.shared.core.domain.errors import AuthorizationError
from shifu.shared.core.domain.structures import MentorAccessGrant
from shifu.shared.core.interfaces import MentorAccessProvider


class PreparePlanningOperationUseCase:
    def __init__(
        self, sessions: PlanningSessionsRepository, access: MentorAccessProvider
    ) -> None:
        self._sessions = sessions
        self._access = access

    def execute(
        self, planning_id: str, operation_id: str, generation: int
    ) -> PlanningOperationContext | None:
        session = self._sessions.find_by_id(planning_id)
        if session is None:
            return None
        operation = session.operation
        if (
            operation is None
            or operation.id != operation_id
            or session.generation != generation
            or session.status is not PlanningSessionStatus.PROCESSING
        ):
            return None
        try:
            self._access.assert_current(
                MentorAccessGrant(
                    account_id=session.account_id,
                    access_revision=session.access_revision,
                    operation_key=planning_id,
                )
            )
        except AuthorizationError:
            # A closed or revised account loses its temporary planning at once.
            self._sessions.remove(planning_id)
            return None
        return PlanningOperationContext(
            planning_id=planning_id,
            operation_id=operation_id,
            generation=generation,
            account_id=session.account_id,
            intent=session.intent,
            answered_batches=session.answered_batches,
            classification=session.classification,
        )
