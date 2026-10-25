from shifu.intelligence.core.domain.enums.planning_intent_kind import (
    PlanningIntentKind,
)
from shifu.intelligence.core.domain.enums.planning_operation_result_kind import (
    PlanningOperationResultKind,
)
from shifu.intelligence.core.domain.structures.planning_proposal import (
    PlanningProposal,
)
from shifu.intelligence.core.domain.structures.planning_question_batch import (
    PlanningQuestionBatch,
)
from shifu.shared.core.domain.structures import structure

OUT_OF_SCOPE_MESSAGE = (
    'O Planejador ajuda você a planejar o que quer aprender ou desenvolver. '
    'Reformule sua intenção com algo que você queira aprender ou crie um '
    'Objetivo manualmente.'
)
UNSUPPORTED_MESSAGE = (
    'Ainda não há Habilidades no Currículo que representem bem esse objetivo. '
    'Reformule sua intenção ou crie um Objetivo manualmente.'
)
VALIDATION_FAILED_MESSAGE = (
    'Não foi possível montar uma proposta válida desta vez. '
    'Tente novamente ou crie um Objetivo manualmente.'
)
FAILED_MESSAGE = (
    'Não foi possível continuar o planejamento agora. '
    'Suas respostas foram preservadas; tente novamente.'
)
SERVICE_UNAVAILABLE_CODE = 'service_unavailable'
VALIDATION_EXHAUSTED_CODE = 'validation_exhausted'
OPERATION_TIMEOUT_CODE = 'operation_timeout'


@structure
class PlanningOperationResult:
    kind: PlanningOperationResultKind
    batch: PlanningQuestionBatch | None = None
    proposal: PlanningProposal | None = None
    message: str | None = None
    failure_code: str | None = None
    classification: PlanningIntentKind | None = None
    consulted_curriculum: bool = False

    def __post_init__(self) -> None:
        if (self.kind is PlanningOperationResultKind.BATCH) != (self.batch is not None):
            raise ValueError('A batch result carries exactly one batch.')
        if (self.kind is PlanningOperationResultKind.PROPOSAL) != (
            self.proposal is not None
        ):
            raise ValueError('A proposal result carries exactly one proposal.')
        if (
            self.kind
            in {
                PlanningOperationResultKind.OUT_OF_SCOPE,
                PlanningOperationResultKind.UNSUPPORTED,
                PlanningOperationResultKind.VALIDATION_FAILED,
                PlanningOperationResultKind.FAILED,
            }
            and not (self.message or '').strip()
        ):
            raise ValueError('An outcome result needs a message for the learner.')
        if self.kind is PlanningOperationResultKind.FAILED and not self.failure_code:
            raise ValueError('A failure result needs a failure code.')

    @staticmethod
    def for_batch(
        batch: PlanningQuestionBatch,
        *,
        classification: PlanningIntentKind | None = None,
        consulted_curriculum: bool = True,
    ) -> 'PlanningOperationResult':
        return PlanningOperationResult(
            kind=PlanningOperationResultKind.BATCH,
            batch=batch,
            classification=classification,
            consulted_curriculum=consulted_curriculum,
        )

    @staticmethod
    def for_proposal(
        proposal: PlanningProposal,
        *,
        classification: PlanningIntentKind | None = None,
        consulted_curriculum: bool = True,
    ) -> 'PlanningOperationResult':
        return PlanningOperationResult(
            kind=PlanningOperationResultKind.PROPOSAL,
            proposal=proposal,
            classification=classification,
            consulted_curriculum=consulted_curriculum,
        )

    @staticmethod
    def out_of_scope(
        *, classification: PlanningIntentKind | None = None
    ) -> 'PlanningOperationResult':
        return PlanningOperationResult(
            kind=PlanningOperationResultKind.OUT_OF_SCOPE,
            message=OUT_OF_SCOPE_MESSAGE,
            classification=classification,
        )

    @staticmethod
    def unsupported(
        *,
        classification: PlanningIntentKind | None = None,
        consulted_curriculum: bool = True,
    ) -> 'PlanningOperationResult':
        return PlanningOperationResult(
            kind=PlanningOperationResultKind.UNSUPPORTED,
            message=UNSUPPORTED_MESSAGE,
            classification=classification,
            consulted_curriculum=consulted_curriculum,
        )

    @staticmethod
    def validation_failed(
        *,
        classification: PlanningIntentKind | None = None,
        consulted_curriculum: bool = True,
    ) -> 'PlanningOperationResult':
        return PlanningOperationResult(
            kind=PlanningOperationResultKind.VALIDATION_FAILED,
            message=VALIDATION_FAILED_MESSAGE,
            failure_code=VALIDATION_EXHAUSTED_CODE,
            classification=classification,
            consulted_curriculum=consulted_curriculum,
        )

    @staticmethod
    def failed(
        failure_code: str = SERVICE_UNAVAILABLE_CODE,
        *,
        classification: PlanningIntentKind | None = None,
        consulted_curriculum: bool = False,
    ) -> 'PlanningOperationResult':
        return PlanningOperationResult(
            kind=PlanningOperationResultKind.FAILED,
            message=FAILED_MESSAGE,
            failure_code=failure_code,
            classification=classification,
            consulted_curriculum=consulted_curriculum,
        )
