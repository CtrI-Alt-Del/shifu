"""Planner run: classify, retrieve, interview or compose, validate and publish."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from json import dumps, loads
from typing import TYPE_CHECKING, ClassVar, Literal, cast

from agno.run.base import RunStatus
from agno.workflow import Loop
from agno.workflow.step import Step
from agno.workflow.types import StepInput, StepOutput
from agno.workflow.workflow import Workflow
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.intelligence.ai.agno.models.mentor_openai_chat import (
    mentor_transport_failure_scope,
)
from shifu.intelligence.ai.agno.outputs.planning_interview_output import (
    PlanningInterviewOutput,
)
from shifu.intelligence.ai.agno.outputs.planning_proposal_output import (
    PlanningProposalOutput,
)
from shifu.intelligence.core.domain.enums import (
    PlanningIntentKind,
    PlanningQuestionKind,
)
from shifu.intelligence.core.domain.structures import (
    PlanningOperationContext,
    PlanningOperationResult,
    PlanningOption,
    PlanningProposal,
    PlanningProposalDraft,
    PlanningProposalDraftSkill,
    PlanningProposalSkill,
    PlanningQuery,
    PlanningQuestion,
    PlanningQuestionBatch,
    PlanningSkillCandidate,
    PlanningSkillRelation,
)
from shifu.intelligence.core.domain.structures.planning_question import (
    MAX_OPTIONS,
    MIN_OPTIONS,
)
from shifu.intelligence.core.domain.structures.planning_question_batch import (
    MAX_QUESTIONS,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.messaging.agentos.workflow_helpers import copy_agent

if TYPE_CHECKING:
    from collections.abc import Sequence

    from agno.agent import Agent
    from agno.run.agent import RunOutput

    from shifu.intelligence.ai.agno.agents import (
        PlanningInterviewAgent,
        PlanningProposalAgent,
    )
    from shifu.intelligence.core.use_cases import (
        ClassifyPlanningIntentUseCase,
        CompletePlanningOperationUseCase,
        PreparePlanningOperationUseCase,
        RetrievePlanningSkillsUseCase,
    )
    from shifu.shared.core.interfaces import IdentifierProvider
    from shifu.shared.messaging.agentos.agentos_handoff_store import (
        AgentOSHandoffStore,
    )


_UNAVAILABLE = 'Planning operation processing is unavailable.'
_HANDOFF_CAPABILITY = 'plan-goal'
_ULID = r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$'
MAX_BATCHES = 3
MAX_DRAFTS = 4
_FORBIDDEN_OPTION_TEXTS = frozenset(
    {'outro', 'outra', 'outros', 'outras', 'não sei', 'nao sei'}
)


class _Input(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    planning_id: str = Field(pattern=_ULID)
    operation_id: str = Field(pattern=_ULID)
    generation: str = Field(pattern=r'^[1-9][0-9]{0,5}$')
    event_id: str | None = Field(default=None, pattern=_ULID)


class _StepReference(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    handoff: str = Field(min_length=32, max_length=128)
    decision: Literal['continue', 'retry', 'done']
    drafts: int = Field(default=0, ge=0, le=MAX_DRAFTS)


@dataclass(slots=True)
class _ExecutionState:
    context: PlanningOperationContext | None
    classification: PlanningIntentKind | None = None
    candidates: tuple[PlanningSkillCandidate, ...] = ()
    consulted_curriculum: bool = False
    problems: tuple[str, ...] = ()
    drafts: int = 0
    result: PlanningOperationResult | None = None


class PlanGoalWorkflow(Workflow):
    """Bounded Planner run; private state travels through handoff references."""

    ID: ClassVar[str] = 'intelligence-plan-goal'

    def __init__(
        self,
        *,
        prepare_use_case: PreparePlanningOperationUseCase,
        complete_use_case: CompletePlanningOperationUseCase,
        classify_use_case: ClassifyPlanningIntentUseCase,
        retrieve_use_case: RetrievePlanningSkillsUseCase,
        interview_agent: PlanningInterviewAgent,
        interview_fallback_agent: PlanningInterviewAgent,
        proposal_agent: PlanningProposalAgent,
        proposal_fallback_agent: PlanningProposalAgent,
        identifier_provider: IdentifierProvider,
        handoffs: AgentOSHandoffStore,
    ) -> None:
        self._prepare = prepare_use_case
        self._complete = complete_use_case
        self._classify = classify_use_case
        self._retrieve = retrieve_use_case
        self._interview = interview_agent
        self._interview_fallback = interview_fallback_agent
        self._proposal = proposal_agent
        self._proposal_fallback = proposal_fallback_agent
        self._identifiers = identifier_provider
        self._handoffs = handoffs
        super().__init__(
            id=self.ID,
            name='Plan Goal',
            steps=[
                Step(
                    name='prepare-and-classify',
                    executor=self._prepare_and_classify,
                    max_retries=0,
                ),
                Step(
                    name='retrieve-and-interview',
                    executor=self._retrieve_and_interview,
                    max_retries=0,
                ),
                Loop(
                    name='compose-and-validate-proposal',
                    steps=[
                        Step(
                            name='compose-and-validate-draft',
                            executor=self._compose_and_validate,
                            max_retries=0,
                        )
                    ],
                    end_condition=self._composition_complete,
                    max_iterations=MAX_DRAFTS,
                    forward_iteration_output=True,
                ),
                Step(
                    name='publish-result',
                    executor=self._publish_result,
                    max_retries=0,
                ),
            ],
            telemetry=False,
            store_events=False,
            store_media=False,
            store_executor_outputs=False,
            cache_session=False,
        )

    def deep_copy(self, *, update: dict[str, object] | None = None) -> PlanGoalWorkflow:
        workflow = PlanGoalWorkflow(
            prepare_use_case=self._prepare,
            complete_use_case=self._complete,
            classify_use_case=self._classify,
            retrieve_use_case=self._retrieve,
            interview_agent=copy_agent(self._interview),
            interview_fallback_agent=copy_agent(self._interview_fallback),
            proposal_agent=copy_agent(self._proposal),
            proposal_fallback_agent=copy_agent(self._proposal_fallback),
            identifier_provider=self._identifiers,
            handoffs=self._handoffs,
        )
        workflow.db = self.db
        if update:
            for name, value in update.items():
                setattr(workflow, name, value)
        return workflow

    def _prepare_and_classify(self, step_input: StepInput) -> StepOutput:
        request = self._request(step_input)
        context = self._prepare.execute(
            request.planning_id, request.operation_id, int(request.generation)
        )
        if context is None:
            return self._store(_ExecutionState(context=None), 'done')
        state = _ExecutionState(context=context, classification=context.classification)
        # The intent of a generation is classified once; answers never change it.
        if context.answered_batches or context.classification is not None:
            return self._store(state, 'continue')
        try:
            classification = self._classify.execute(
                PlanningQuery(intent=context.intent)
            )
        except ServiceUnavailableError:
            return self._finish(state, PlanningOperationResult.failed())
        state.classification = classification.kind
        if classification.kind is PlanningIntentKind.OUT_OF_SCOPE:
            return self._finish(
                state,
                PlanningOperationResult.out_of_scope(
                    classification=state.classification
                ),
            )
        return self._store(state, 'continue')

    def _retrieve_and_interview(self, step_input: StepInput) -> StepOutput:
        state = self._consume(step_input)
        context = state.context
        if context is None or state.result is not None:
            return self._store(state, 'done')
        try:
            retrieval = self._retrieve.execute(
                PlanningQuery(intent=context.intent, answers=context.answers)
            )
        except ServiceUnavailableError:
            return self._finish(state, self._failed(state))
        state.candidates = retrieval.candidates
        state.consulted_curriculum = True
        if not retrieval.candidates:
            return self._finish(state, self._unsupported(state))
        if len(context.answered_batches) >= MAX_BATCHES:
            return self._store(state, 'continue')
        try:
            output = self._run_with_fallback(
                self._interview,
                self._interview_fallback,
                PlanningInterviewOutput,
                self._interview_payload(state),
            )
        except Exception:  # noqa: BLE001 - private model failures fail closed.
            return self._finish(state, self._failed(state))
        batch = self._batch_from(output) if output.needs_clarification else None
        if batch is not None:
            return self._finish(
                state,
                PlanningOperationResult.for_batch(
                    batch, classification=state.classification
                ),
            )
        return self._store(state, 'continue')

    def _compose_and_validate(self, step_input: StepInput) -> StepOutput:
        state = self._consume(step_input)
        context = state.context
        if context is None or state.result is not None:
            return self._store(state, 'done')
        try:
            output = self._run_with_fallback(
                self._proposal,
                self._proposal_fallback,
                PlanningProposalOutput,
                self._proposal_payload(state),
            )
        except Exception:  # noqa: BLE001 - private model failures fail closed.
            return self._finish(state, self._failed(state))
        state.drafts += 1
        if not output.supported:
            return self._finish(state, self._unsupported(state))
        names = {candidate.skill_id: candidate.name for candidate in state.candidates}
        draft = PlanningProposalDraft(
            title=output.title,
            description=output.description,
            skills=tuple(
                PlanningProposalDraftSkill(
                    skill_id=skill.skill_id, justification=skill.justification
                )
                for skill in output.skills
            ),
        )
        problems = draft.problems(names)
        if not problems:
            proposal = PlanningProposal(
                title=' '.join(draft.title.split()),
                description=' '.join(draft.description.split()),
                skills=tuple(
                    PlanningProposalSkill(
                        skill_id=skill.skill_id,
                        name=names[skill.skill_id],
                        justification=' '.join(skill.justification.split()),
                    )
                    for skill in draft.skills
                ),
                relations=self._relations(
                    state.candidates, tuple(skill.skill_id for skill in draft.skills)
                ),
            )
            return self._finish(
                state,
                PlanningOperationResult.for_proposal(
                    proposal, classification=state.classification
                ),
            )
        # The learner never sees this draft; the composer gets the problems instead.
        state.problems = problems
        if state.drafts >= MAX_DRAFTS:
            return self._finish(
                state,
                PlanningOperationResult.validation_failed(
                    classification=state.classification
                ),
            )
        return self._store(state, 'retry')

    def _publish_result(self, step_input: StepInput) -> StepOutput:
        state = self._consume(step_input)
        context = state.context
        if context is None:
            return StepOutput(content='skipped')
        result = state.result or self._failed(state)
        applied = self._complete.execute(
            context.planning_id, context.operation_id, context.generation, result
        )
        return StepOutput(content=result.kind.value if applied else 'discarded')

    @staticmethod
    def _composition_complete(outputs: Sequence[StepOutput]) -> bool:
        if not outputs or not isinstance(outputs[-1].content, str):
            return True
        try:
            reference = _StepReference.model_validate_json(
                outputs[-1].content, strict=True
            )
        except (ValidationError, ValueError, TypeError):
            return True
        return reference.decision != 'retry'

    def _run_with_fallback[Output: BaseModel](
        self,
        primary: Agent,
        fallback: Agent,
        output_type: type[Output],
        payload: dict[str, object],
    ) -> Output:
        """Ask the primary model; a transport or schema failure asks the fallback once."""
        try:
            return output_type.model_validate(
                self._run_agent(primary, payload), strict=True
            )
        except Exception:  # noqa: BLE001 - any primary failure is recoverable by the fallback.
            return output_type.model_validate(
                self._run_agent(fallback, payload), strict=True
            )

    def _run_agent(self, agent: Agent, payload: dict[str, object]) -> object:
        with mentor_transport_failure_scope() as failure:
            response: RunOutput = agent.run(  # pyright: ignore[reportUnknownMemberType] - Agno Agent lacks complete stubs.
                input=dumps(payload, ensure_ascii=False)
            )
            failure.raise_if_failed()
        if response.status != RunStatus.completed:
            raise ServiceUnavailableError(_UNAVAILABLE)
        content = cast('object', response.content)
        if isinstance(content, BaseModel):
            return content.model_dump()
        if isinstance(content, str):
            return cast('object', loads(content))
        return content

    @staticmethod
    def _interview_payload(state: _ExecutionState) -> dict[str, object]:
        context = state.context
        if context is None:
            raise ServiceUnavailableError(_UNAVAILABLE)
        return {
            'intent': context.intent,
            'answers': PlanGoalWorkflow._answers_payload(context),
            'candidates': PlanGoalWorkflow._candidates_payload(state.candidates),
            'remaining_batches': MAX_BATCHES - len(context.answered_batches),
        }

    @staticmethod
    def _proposal_payload(state: _ExecutionState) -> dict[str, object]:
        context = state.context
        if context is None:
            raise ServiceUnavailableError(_UNAVAILABLE)
        return {
            'intent': context.intent,
            'answers': PlanGoalWorkflow._answers_payload(context),
            'candidates': PlanGoalWorkflow._candidates_payload(state.candidates),
            'problems': list(state.problems),
        }

    @staticmethod
    def _answers_payload(context: PlanningOperationContext) -> list[dict[str, object]]:
        return [
            {
                'question': item.question.text,
                'kind': item.question.kind.value,
                'selected': list(item.selected_texts),
            }
            for batch in context.answered_batches
            for item in batch.items
        ]

    @staticmethod
    def _candidates_payload(
        candidates: tuple[PlanningSkillCandidate, ...],
    ) -> list[dict[str, object]]:
        names = {candidate.skill_id: candidate.name for candidate in candidates}
        return [
            {
                'skill_id': candidate.skill_id,
                'name': candidate.name,
                'description': candidate.description,
                'foundations': [
                    names[skill_id]
                    for skill_id in candidate.foundation_skill_ids
                    if skill_id in names
                ],
            }
            for candidate in candidates
        ]

    def _batch_from(
        self, output: PlanningInterviewOutput
    ) -> PlanningQuestionBatch | None:
        questions: list[PlanningQuestion] = []
        for item in output.questions:
            options: list[PlanningOption] = []
            for text in item.options:
                normalized = ' '.join(text.split())
                lowered = normalized.casefold()
                if not normalized or lowered in _FORBIDDEN_OPTION_TEXTS:
                    continue
                if any(option.text.casefold() == lowered for option in options):
                    continue
                options.append(
                    PlanningOption(id=f'o{len(options) + 1}', text=normalized)
                )
            if not MIN_OPTIONS <= len(options) <= MAX_OPTIONS:
                continue
            if item.allow_unknown:
                options.append(PlanningOption.unknown())
            questions.append(
                PlanningQuestion(
                    id=f'q{len(questions) + 1}',
                    text=' '.join(item.text.split()),
                    kind=PlanningQuestionKind(item.kind),
                    options=tuple(options),
                )
            )
            if len(questions) == MAX_QUESTIONS:
                break
        if not questions:
            return None
        return PlanningQuestionBatch(
            id=self._identifiers.generate(), questions=tuple(questions)
        )

    @staticmethod
    def _relations(
        candidates: tuple[PlanningSkillCandidate, ...], skill_ids: tuple[str, ...]
    ) -> tuple[PlanningSkillRelation, ...]:
        proposed = set(skill_ids)
        return tuple(
            PlanningSkillRelation(
                skill_id=candidate.skill_id, foundation_skill_id=foundation_id
            )
            for candidate in candidates
            if candidate.skill_id in proposed
            for foundation_id in candidate.foundation_skill_ids
            if foundation_id in proposed
        )

    @staticmethod
    def _failed(state: _ExecutionState) -> PlanningOperationResult:
        return PlanningOperationResult.failed(
            classification=state.classification,
            consulted_curriculum=state.consulted_curriculum,
        )

    @staticmethod
    def _unsupported(state: _ExecutionState) -> PlanningOperationResult:
        return PlanningOperationResult.unsupported(classification=state.classification)

    def _finish(
        self, state: _ExecutionState, result: PlanningOperationResult
    ) -> StepOutput:
        state.result = result
        return self._store(state, 'done')

    def _store(
        self, state: _ExecutionState, decision: Literal['continue', 'retry', 'done']
    ) -> StepOutput:
        reference = self._handoffs.create(
            capability=_HANDOFF_CAPABILITY,
            input_value=state,
            ttl=timedelta(minutes=5),
        )
        return StepOutput(
            content=_StepReference(
                handoff=reference, decision=decision, drafts=state.drafts
            ).model_dump_json()
        )

    def _consume(self, step_input: StepInput) -> _ExecutionState:
        content = step_input.get_last_step_content()
        try:
            reference = _StepReference.model_validate_json(
                cast('str', content), strict=True
            )
            value = self._handoffs.read_input(
                reference.handoff, capability=_HANDOFF_CAPABILITY
            )
            self._handoffs.discard(reference.handoff)
        except (ValidationError, ValueError, TypeError, KeyError):
            value = None
        if isinstance(value, _ExecutionState):
            return value
        # A lost reference cannot be recovered privately; the operation fails closed.
        request = self._request(step_input)
        context = self._prepare.execute(
            request.planning_id, request.operation_id, int(request.generation)
        )
        return _ExecutionState(context=context, result=PlanningOperationResult.failed())

    @staticmethod
    def _request(step_input: StepInput) -> _Input:
        raw = step_input.input
        try:
            return (
                _Input.model_validate_json(raw, strict=True)
                if isinstance(raw, str)
                else _Input.model_validate(raw, strict=True)
            )
        except (ValidationError, ValueError, TypeError):
            raise ServiceUnavailableError(_UNAVAILABLE) from None
