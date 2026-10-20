from datetime import datetime, timedelta

from shifu.intelligence.core.domain.enums.planning_intent_kind import (
    PlanningIntentKind,
)
from shifu.intelligence.core.domain.enums.planning_operation_kind import (
    PlanningOperationKind,
)
from shifu.intelligence.core.domain.enums.planning_operation_result_kind import (
    PlanningOperationResultKind,
)
from shifu.intelligence.core.domain.enums.planning_session_status import (
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors.planning_answers_invalid_error import (
    PlanningAnswersInvalidError,
)
from shifu.intelligence.core.domain.errors.planning_operation_conflict_error import (
    PlanningOperationConflictError,
)
from shifu.intelligence.core.domain.errors.planning_state_conflict_error import (
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.structures.planning_answer import PlanningAnswer
from shifu.intelligence.core.domain.structures.planning_answered_batch import (
    PlanningAnsweredBatch,
    PlanningAnsweredQuestion,
)
from shifu.intelligence.core.domain.structures.planning_operation import (
    PlanningOperation,
)
from shifu.intelligence.core.domain.structures.planning_operation_result import (
    FAILED_MESSAGE,
    OPERATION_TIMEOUT_CODE,
    PlanningOperationResult,
)
from shifu.intelligence.core.domain.structures.planning_proposal import (
    PlanningProposal,
)
from shifu.intelligence.core.domain.structures.planning_question_batch import (
    PlanningQuestionBatch,
)
from shifu.shared.core.domain.entities import entity

MAX_INTENT_LENGTH = 4000
RETRYABLE_STATUSES = frozenset(
    {PlanningSessionStatus.FAILED, PlanningSessionStatus.VALIDATION_FAILED}
)


@entity
class PlanningSession:
    """Temporary planning bound to one account; every transition is a method."""

    id: str
    account_id: str
    access_revision: str
    intent: str
    generation: int
    version: int
    status: PlanningSessionStatus
    operation: PlanningOperation | None
    last_operation_kind: PlanningOperationKind | None
    classification: PlanningIntentKind | None
    consulted_curriculum: bool
    answered_batches: tuple[PlanningAnsweredBatch, ...]
    current_batch: PlanningQuestionBatch | None
    proposal: PlanningProposal | None
    message: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime

    @property
    def batch(self) -> PlanningQuestionBatch | None:
        """The batch waiting for answers; only exposed while interviewing."""
        return self.current_batch

    @property
    def answered_batch_count(self) -> int:
        return len(self.answered_batches)

    @classmethod
    def start(
        cls,
        planning_id: str,
        account_id: str,
        access_revision: str,
        intent: str,
        operation_id: str,
        now: datetime,
    ) -> 'PlanningSession':
        return cls(
            id=planning_id,
            account_id=account_id,
            access_revision=access_revision,
            intent=cls._validated_intent(intent),
            generation=1,
            version=0,
            status=PlanningSessionStatus.PROCESSING,
            operation=PlanningOperation(
                id=operation_id, kind=PlanningOperationKind.START, started_at=now
            ),
            last_operation_kind=PlanningOperationKind.START,
            classification=None,
            consulted_curriculum=False,
            answered_batches=(),
            current_batch=None,
            proposal=None,
            message=None,
            failure_code=None,
            created_at=now,
            updated_at=now,
        )

    def submit_answers(
        self,
        batch_id: str,
        answers: tuple[PlanningAnswer, ...],
        operation_id: str,
        now: datetime,
    ) -> None:
        self._require_idle()
        batch = self.current_batch
        if self.status is not PlanningSessionStatus.INTERVIEW or batch is None:
            raise PlanningStateConflictError
        if batch_id != batch.id:
            raise PlanningStateConflictError('Este lote de perguntas não é o atual.')
        by_question = {answer.question_id: answer for answer in answers}
        if len(by_question) != len(answers) or set(by_question) != {
            question.id for question in batch.questions
        }:
            raise PlanningAnswersInvalidError
        # Every question validates its own selection, including the exclusive option.
        answered = PlanningAnsweredBatch(
            batch_id=batch.id,
            items=tuple(
                PlanningAnsweredQuestion(
                    question=question,
                    option_ids=by_question[question.id].option_ids,
                )
                for question in batch.questions
            ),
        )
        self.answered_batches = (*self.answered_batches, answered)
        self.current_batch = None
        self._begin(PlanningOperationKind.ANSWER, operation_id, now)

    def restart(
        self, intent: str, access_revision: str, operation_id: str, now: datetime
    ) -> None:
        self._require_idle()
        self.intent = self._validated_intent(intent)
        self.access_revision = access_revision
        self.generation += 1
        self.classification = None
        self.consulted_curriculum = False
        self.answered_batches = ()
        self.current_batch = None
        self.proposal = None
        self._begin(PlanningOperationKind.RESTART, operation_id, now)

    def retry(self, operation_id: str, now: datetime) -> None:
        self._require_idle()
        if self.status not in RETRYABLE_STATUSES:
            raise PlanningStateConflictError(
                'Só é possível tentar novamente após uma falha.'
            )
        self._begin(PlanningOperationKind.RETRY, operation_id, now)

    def expire_operation(self, now: datetime, timeout: timedelta) -> bool:
        operation = self.operation
        if (
            operation is None
            or self.status is not PlanningSessionStatus.PROCESSING
            or operation.started_at + timeout > now
        ):
            return False
        self.operation = None
        self.status = PlanningSessionStatus.FAILED
        self.failure_code = OPERATION_TIMEOUT_CODE
        self.message = FAILED_MESSAGE
        self.updated_at = now
        return True

    def complete(
        self,
        operation_id: str,
        generation: int,
        result: PlanningOperationResult,
        now: datetime,
    ) -> bool:
        operation = self.operation
        # A result of a cancelled, restarted or superseded operation is discarded.
        if (
            operation is None
            or operation.id != operation_id
            or self.generation != generation
            or self.status is not PlanningSessionStatus.PROCESSING
        ):
            return False
        self.classification = result.classification or self.classification
        self.consulted_curriculum = (
            self.consulted_curriculum or result.consulted_curriculum
        )
        self.current_batch = None
        self.proposal = None
        self.message = result.message
        self.failure_code = result.failure_code
        if result.kind is PlanningOperationResultKind.BATCH:
            self.current_batch = result.batch
            self.status = PlanningSessionStatus.INTERVIEW
        elif result.kind is PlanningOperationResultKind.PROPOSAL:
            self.proposal = result.proposal
            self.status = PlanningSessionStatus.PROPOSAL
        elif result.kind is PlanningOperationResultKind.OUT_OF_SCOPE:
            self.status = PlanningSessionStatus.OUT_OF_SCOPE
        elif result.kind is PlanningOperationResultKind.UNSUPPORTED:
            self.status = PlanningSessionStatus.UNSUPPORTED
        elif result.kind is PlanningOperationResultKind.VALIDATION_FAILED:
            self.status = PlanningSessionStatus.VALIDATION_FAILED
        else:
            self.status = PlanningSessionStatus.FAILED
        self.operation = None
        self.updated_at = now
        return True

    def _begin(
        self, kind: PlanningOperationKind, operation_id: str, now: datetime
    ) -> None:
        self.operation = PlanningOperation(id=operation_id, kind=kind, started_at=now)
        self.last_operation_kind = kind
        self.status = PlanningSessionStatus.PROCESSING
        self.message = None
        self.failure_code = None
        self.updated_at = now

    def _require_idle(self) -> None:
        if self.operation is not None:
            raise PlanningOperationConflictError

    @staticmethod
    def _validated_intent(intent: str) -> str:
        normalized = ' '.join(intent.split())
        if not normalized or len(normalized) > MAX_INTENT_LENGTH:
            raise ValueError('A planning intent must be non-blank and bounded.')
        return normalized
