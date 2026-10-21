from dataclasses import replace
from itertools import count
from collections.abc import Callable
from unittest.mock import create_autospec
import pytest

from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
    MentorIntent,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseBlock,
    MentorRouteResult,
    MentorContextHint,
    MentorInferenceUsage,
    MentorGenerationRequest,
    MentorResponseEvent,
)
from shifu.intelligence.core.interfaces import (
    MentorRouteProvider,
    AnswerMentorMessageWorkflow,
)
from shifu.intelligence.core.use_cases import ProcessMentorResponseUseCase
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import MentorContextProvider, MentorCatalogProvider
from tests.intelligence.core.use_cases.mentor_response_test_setup import (
    MentorResponseTestSetup,
)


class TestProcessMentorResponseUseCase(MentorResponseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare()
        self.context_provider = create_autospec(MentorContextProvider, instance=True)
        self.catalog = create_autospec(MentorCatalogProvider, instance=True)
        self.catalog.search.return_value = ()
        self.context = MentorContextSnapshot(
            goal_id=None,
            skill_experience_id=None,
            skill_id=None,
            competency_id=None,
            activity_id=None,
            skill_completed=None,
            diagnostic_in_progress=False,
            facts=(),
            eligible_references=(),
            resolved_references=(),
            unavailable_sources=(),
        )
        self.context_provider.read.return_value = self.context
        self.router = create_autospec(MentorRouteProvider, instance=True)
        self.block = MentorResponseBlock(
            block_key='local-topic',
            ordinal=0,
            intent=MentorIntent.EXPLAIN_CONCEPT,
            content='Uma explicação editorial.',
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=(),
            clarification=None,
        )

        def current_snapshot(*_args: object) -> object:
            blocks = tuple(
                call.args[0].block
                for call in self.repositories.mentor_response_events.append.call_args_list
                if call.args[0].block is not None
            )
            return replace(self.snapshot, blocks=blocks)

        self.repositories.mentor_response_events.snapshot.side_effect = current_snapshot
        self.workflow = create_autospec(AnswerMentorMessageWorkflow, instance=True)
        usage_calls: dict[str, MentorInferenceUsage] = {}

        def journal(
            _attempt: str, _owner: str, _revision: str, usage: MentorInferenceUsage
        ) -> bool:
            usage_calls.setdefault(usage.call_key, usage)
            return True

        self.repositories.mentor_response_attempts.journal_usage.side_effect = journal

        def read_usage(_attempt: str) -> tuple[MentorInferenceUsage, ...]:
            return tuple(usage_calls.values())

        self.repositories.mentor_response_attempts.read_usage.side_effect = read_usage
        self.repositories.mentor_response_attempts.inference_started.return_value = (
            False
        )

        def reserve(*_args: object) -> bool:
            self.repositories.mentor_response_attempts.inference_started.return_value = True
            return True

        self.repositories.mentor_response_attempts.reserve_generation.side_effect = (
            reserve
        )

        def run(
            _request: MentorGenerationRequest,
            usage_recorder: Callable[[MentorInferenceUsage], None] | None = None,
            inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            assert usage_recorder is not None
            assert inference_guard is not None
            inference_guard()
            assert progress_recorder is not None
            progress_recorder(MentorWorkflowStep.WRITE_ANSWER)
            usage_recorder(
                MentorInferenceUsage(
                    call_key='writer:0', profile='writer', used_tokens=120
                )
            )
            inference_guard()
            progress_recorder(MentorWorkflowStep.REVIEW_ANSWER)
            usage_recorder(
                MentorInferenceUsage(
                    call_key='review:0', profile='review', used_tokens=60
                )
            )
            return self.workflow.run.return_value

        self.workflow.run.side_effect = run
        self.subject = ProcessMentorResponseUseCase(
            self.database,
            self.identifiers,
            self.clock,
            self.access,
            self.context_provider,
            self.router,
            self.workflow,
            self.catalog,
        )

    def test_should_complete_local_without_generator(self) -> None:
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        events = [
            call.args[0]
            for call in self.repositories.mentor_response_events.append.call_args_list
        ]
        assert [event.kind for event in events] == [
            MentorResponseEventKind.BLOCK,
            MentorResponseEventKind.COMPLETED,
        ]
        assert events[0].block == self.block
        response = self.repositories.mentor_messages.add.call_args.args[0]
        assert response.content == self.block.content
        assert response.in_reply_to_message_id == 'message'
        self.access.assert_current.assert_called()
        self.router.route.assert_called_once_with(self.message.content, self.context)
        self.repositories.mentor_messages.find_all.assert_called_once_with(
            'account', 'session'
        )
        self.repositories.mentor_response_attempts.find_continuity.assert_called_once_with(
            'account', 'session'
        )
        assert all(
            call.args == ('account', 'session')
            for call in self.repositories.mentor_response_events.snapshot.call_args_list
        )
        assert all(
            call.args == ('account', 'session')
            for call in self.repositories.mentor_sessions.find_by_id_for_update.call_args_list
        )
        assert all(
            call.args[0] == 'attempt'
            for call in self.repositories.mentor_response_attempts.find_by_id_for_update.call_args_list
        )
        assert all(
            call.args == ('account', 'session')
            for call in self.repositories.mentor_response_attempts.find_current.call_args_list
        )
        assert all(
            call.args == ('attempt', 'message-new', self.now)
            for call in self.repositories.mentor_response_attempts.has_claim.call_args_list
        )
        assert all(
            call.args[0] == 'account'
            for call in self.context_provider.read.call_args_list
        )

    def test_should_pass_complete_history_and_approved_local_prefix_to_workflow(
        self,
    ) -> None:
        older = replace(
            self.message, id='older', content='contexto persistido completo'
        )
        self.repositories.mentor_messages.find_all.return_value = (older, self.message)
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('parte gerada',),
            clarification=None,
        )
        self.workflow.run.return_value = MentorResponseBlock(
            block_key='writer',
            ordinal=0,
            intent=MentorIntent.LEARNING_CONVERSATION,
            content='Resposta aprovada cumulativamente.',
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        request = self.workflow.run.call_args.args[0]
        assert request.history == (older, self.message)
        assert request.approved_blocks == (self.block,)
        assert request.context == self.context
        assert request.requested_part == 'parte gerada'
        self.repositories.mentor_response_attempts.reserve_generation.assert_called_once_with(
            'attempt', 'generated-0', 'revision'
        )

    def test_should_keep_approved_partial_when_later_generation_fails(self) -> None:
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('gerar',),
            clarification=None,
        )
        self.workflow.run.side_effect = ServiceUnavailableError()
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        events = [
            call.args[0]
            for call in self.repositories.mentor_response_events.append.call_args_list
        ]
        assert events[0].block == self.block
        assert events[-1].kind is MentorResponseEventKind.FAILED
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_events.discard_partial.assert_not_called()

    def test_should_not_infer_or_publish_after_access_revocation(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.context_provider.read.assert_not_called()
        self.router.route.assert_not_called()
        self.workflow.run.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_reject_late_callback_after_cancel(self) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.side_effect = [
            self.attempt,
            replace(self.attempt, status=MentorResponseStatus.CANCELLED),
            replace(self.attempt, status=MentorResponseStatus.CANCELLED),
            replace(self.attempt, status=MentorResponseStatus.CANCELLED),
        ]
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_recover_committed_block_without_repeat_generation(self) -> None:
        generated = replace(self.block, block_key='generated-0')
        self.repositories.mentor_response_events.snapshot.side_effect = None
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(generated,)
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('gerar',),
            clarification=None,
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        self.repositories.mentor_response_attempts.reserve_generation.assert_not_called()

    def test_should_not_restart_persisted_exhausted_workflow_budget(self) -> None:
        self.repositories.mentor_response_attempts.reserve_generation.side_effect = None
        self.repositories.mentor_response_attempts.reserve_generation.return_value = (
            False
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('gerar',),
            clarification=None,
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.workflow.run.assert_not_called()

    def test_should_revalidate_changed_eligibility_before_publish(self) -> None:
        self.context_provider.read.side_effect = [
            self.context,
            replace(self.context, diagnostic_in_progress=True),
        ]
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        events = [
            call.args[0]
            for call in self.repositories.mentor_response_events.append.call_args_list
        ]
        assert all(event.block is None for event in events)
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_exclude_diagnostic_help_but_publish_independent_progress(
        self,
    ) -> None:
        self.message = replace(
            self.message, content='resolva essa atividade e mostre meu progresso'
        )
        self.repositories.mentor_messages.find_all.return_value = (self.message,)
        self.context_provider.read.return_value = replace(
            self.context, activity_id='diagnostic', diagnostic_in_progress=True
        )
        progress = replace(
            self.block,
            block_key='progress',
            intent=MentorIntent.CONSULT_PROGRESS,
            content='Progresso oficial.',
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block, progress),
            generation_requests=('resolva atividade',),
            clarification=None,
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        response = self.repositories.mentor_messages.add.call_args.args[0]
        assert progress.content in response.content
        assert 'Não posso ajudar' in response.content
        assert self.block.content not in response.content

    def test_should_use_original_hint_in_repeated_current_reads(self) -> None:
        attempt = replace(
            self.attempt,
            context_hint=MentorContextHint(goal_id='original', skill_id='skill'),
        )
        self.repositories.mentor_response_attempts.find_by_id.return_value = attempt
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = attempt
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        for call in self.context_provider.read.call_args_list:
            assert call.kwargs['goal_id'] == 'original'
            assert call.kwargs['skill_id'] == 'skill'

    def test_should_not_execute_concurrent_redelivery_with_active_claim(self) -> None:
        self.repositories.mentor_response_attempts.claim.return_value = False
        assert self.subject.execute('attempt') is MentorResponseStatus.PROCESSING
        self.context_provider.read.assert_not_called()
        self.workflow.run.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_use_structured_same_session_continuity_and_revalidate(self) -> None:
        references = ('01ARZ3NDEKTSV4RRFFQ69G5FAV',)
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            references
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert self.context_provider.read.call_args_list[0].args == (
            'account',
            references,
        )

    def test_should_prioritize_explicit_reference_over_continuity_hint(self) -> None:
        explicit = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=f'explique {explicit}'),
        )
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            'previous',
        )
        self.subject.execute('attempt')
        assert self.context_provider.read.call_args_list[0].args == (
            'account',
            (explicit,),
        )

    def test_should_not_publish_after_execution_lease_expired(self) -> None:
        self.repositories.mentor_response_attempts.claim.side_effect = (True, False)
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        assert self.subject.execute('attempt') is MentorResponseStatus.PROCESSING
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_emit_actual_local_stages_without_private_values(self) -> None:
        from contextlib import AbstractContextManager
        from shifu.intelligence.core.interfaces import MentorTelemetryProvider

        telemetry = create_autospec(MentorTelemetryProvider, instance=True)
        manager = create_autospec(AbstractContextManager, instance=True)
        manager.__exit__.return_value = False
        telemetry.scope.return_value = manager
        subject = ProcessMentorResponseUseCase(
            self.database,
            self.identifiers,
            self.clock,
            self.access,
            self.context_provider,
            self.router,
            self.workflow,
            self.catalog,
            telemetry,
        )
        assert subject.execute('attempt') is MentorResponseStatus.COMPLETED
        stages = [call.args[0] for call in telemetry.scope.call_args_list]
        assert {'context', 'route', 'local', 'publish', 'persist'}.issubset(stages)
        assert 'generate' not in stages
        assert all(
            len(call.args) == 1 and not call.kwargs
            for call in telemetry.scope.call_args_list
        )

    def test_should_answer_with_throwing_optional_telemetry(self) -> None:
        from shifu.intelligence.core.interfaces import MentorTelemetryProvider

        telemetry = create_autospec(MentorTelemetryProvider, instance=True)
        telemetry.scope.side_effect = RuntimeError('SDK unavailable')
        subject = ProcessMentorResponseUseCase(
            self.database,
            self.identifiers,
            self.clock,
            self.access,
            self.context_provider,
            self.router,
            self.workflow,
            self.catalog,
            telemetry,
        )
        assert subject.execute('attempt') is MentorResponseStatus.COMPLETED

    def test_should_preserve_workflow_failure_when_telemetry_exit_throws(self) -> None:
        from contextlib import AbstractContextManager
        from shifu.intelligence.core.interfaces import MentorTelemetryProvider

        telemetry = create_autospec(MentorTelemetryProvider, instance=True)
        manager = create_autospec(AbstractContextManager, instance=True)
        manager.__exit__.side_effect = RuntimeError('SDK unavailable')
        telemetry.scope.return_value = manager
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('gerar',),
            clarification=None,
        )
        self.workflow.run.side_effect = ServiceUnavailableError()
        subject = ProcessMentorResponseUseCase(
            self.database,
            self.identifiers,
            self.clock,
            self.access,
            self.context_provider,
            self.router,
            self.workflow,
            self.catalog,
            telemetry,
        )
        assert subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_messages.add.assert_not_called()
        assert 'generate' in [call.args[0] for call in telemetry.scope.call_args_list]

    def test_should_resolve_full_named_goal_before_catalog(self) -> None:
        goal_id = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        self.context = replace(
            self.context, facts=(('goals', f'{goal_id}: Matemática básica'),)
        )
        self.context_provider.read.return_value = self.context
        with self.database.transaction() as repositories:
            messages = repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content='Quero consultar Matemática básica'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert any(
            call.args[1] == (goal_id,)
            for call in self.context_provider.read.call_args_list
        )

    def test_should_clarify_duplicate_goal_title_without_generation(self) -> None:
        self.context = replace(
            self.context,
            facts=(
                ('goals', '01ARZ3NDEKTSV4RRFFQ69G5FAV: Matemática básica'),
                ('goals', '01ARZ3NDEKTSV4RRFFQ69G5FAW: Matemática básica'),
            ),
        )
        self.context_provider.read.return_value = self.context
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content='Quero consultar Matemática básica'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        self.catalog.search.assert_not_called()
        assert all(
            call.args[1] == () for call in self.context_provider.read.call_args_list
        )
        blocks = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block
        ]
        assert any('mais de um Objetivo' in block.content for block in blocks)

    @pytest.mark.parametrize(
        ('selection', 'expected'),
        [('primeiro', 'a'), ('segundo', 'b'), ('último', 'c')],
    )
    def test_should_resolve_ordinal_from_private_proposals(
        self, selection: str, expected: str
    ) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            'proposal:a',
            'proposal:b',
            'proposal:c',
        )
        self.context_provider.read.return_value = replace(
            self.context, eligible_references=('a', 'b', 'c')
        )
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content=f'Quero o {selection}'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert self.context_provider.read.call_args_list[0].args[1] == (expected,)

    def test_should_clarify_proposal_no_longer_eligible(self) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            'proposal:private-id',
        )
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content='Quero o primeiro'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        blocks = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block
        ]
        assert any('não está disponível' in block.content for block in blocks)
        self.workflow.run.assert_not_called()

    def test_should_isolate_execution_claims_for_concurrent_workers(self) -> None:
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier

        barrier = Barrier(2)

        def attempt_by_id(attempt_id: str) -> object:
            return replace(self.attempt, id=attempt_id, session_id=attempt_id)

        self.repositories.mentor_response_attempts.find_by_id.side_effect = (
            attempt_by_id
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.side_effect = (
            attempt_by_id
        )

        def current_attempt(_account: str, session: str) -> object:
            return attempt_by_id(session)

        self.repositories.mentor_response_attempts.find_current.side_effect = (
            current_attempt
        )
        observed: list[tuple[str, str]] = []
        self.identifiers.generate.side_effect = (
            'worker-one',
            'worker-two',
            'reply-one',
            'reply-two',
        )

        def route(*_args: object) -> MentorRouteResult:
            barrier.wait(timeout=5)
            return MentorRouteResult(
                intents=(),
                local_blocks=(self.block,),
                generation_requests=(),
                clarification=None,
            )

        self.router.route.side_effect = route

        def claimed(_attempt: str, owner: str, *_args: object) -> bool:
            observed.append(('claim', owner))
            return True

        self.repositories.mentor_response_attempts.claim.side_effect = claimed
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(
                executor.map(self.subject.execute, ('attempt', 'other-attempt'))
            )
        assert len(outcomes) == 2
        assert {owner for kind, owner in observed if kind == 'claim'} == {
            'worker-one',
            'worker-two',
        }
        released = {
            call.args[1]
            for call in self.repositories.mentor_response_attempts.release_claim.call_args_list
        }
        assert released == {'worker-one', 'worker-two'}

    def test_should_persist_catalog_proposal_order_privately(self) -> None:
        from shifu.shared.core.domain.structures import MentorCatalogEntry

        self.context_provider.read.return_value = replace(
            self.context, eligible_references=('a', 'b')
        )
        self.catalog.read_projection.return_value = tuple(
            MentorCatalogEntry(
                reference_id=reference,
                kind='skill',
                skill_id=reference,
                competency_id=None,
                title=title,
                description=None,
                concept_ids=(),
                source_version='v1',
            )
            for reference, title in (
                ('b', 'Segunda habilidade'),
                ('a', 'Primeira habilidade'),
            )
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(
                replace(
                    self.block,
                    block_key='progress',
                    intent=MentorIntent.CONSULT_PROGRESS,
                    content='Você concluiu duas Habilidades.',
                ),
                replace(self.block, ordinal=1, intent=MentorIntent.SEARCH_CURRICULUM),
            ),
            generation_requests=(),
            clarification=None,
            proposed_reference_ids=('b', 'a'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert (
            self.repositories.mentor_response_attempts.update_references.call_args.args[
                1
            ]
            == ('proposal:b', 'proposal:a')
        )
        blocks = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block
        ]
        assert blocks[0].content == 'Você concluiu duas Habilidades.'
        assert blocks[1].content == '1. Segunda habilidade\n2. Primeira habilidade'
        assert all(
            call.args[0] == 'attempt' and call.args[2] == 'revision'
            for call in self.repositories.mentor_response_attempts.update_references.call_args_list
        )

    @pytest.mark.parametrize('selection', ['segundo', 'primeiro e último'])
    def test_should_clarify_without_unambiguous_prior_proposal(
        self, selection: str
    ) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = ()
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content=f'Quero {selection}'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        blocks = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block
        ]
        assert any('nome completo' in block.content for block in blocks)
        self.workflow.run.assert_not_called()

    def test_should_durably_fail_revoked_start_without_public_event(self) -> None:
        self.access.assert_current.side_effect = ServiceUnavailableError()
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_response_attempts.claim.assert_called_once()
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.FAILED,
            'revision',
        )
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_fail_unexpected_adapter_exception(self) -> None:
        self.router.route.side_effect = TypeError('unexpected shape')
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_force_authoritative_context_clarification(self) -> None:
        self.context_provider.read.return_value = replace(
            self.context,
            facts=(('context_clarification', 'Qual Objetivo você quer usar?'),),
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('generate',),
            clarification=None,
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        blocks = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block
        ]
        assert len(blocks) == 1
        block = blocks[0]
        assert isinstance(block.block_key, str) and block.block_key
        assert isinstance(block.ordinal, int) and not isinstance(block.ordinal, bool)
        assert block.ordinal == 0
        assert block.intent is None
        assert 'Qual Objetivo' in block.content and 'quer usar' in block.content
        emitted = [
            call.args[0]
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].kind is MentorResponseEventKind.BLOCK
        ]
        assert emitted == [
            MentorResponseEvent(
                session_id='session',
                attempt_id='attempt',
                sequence=2,
                kind=MentorResponseEventKind.BLOCK,
                status=MentorResponseStatus.PROCESSING,
                block=block,
                consultation=None,
                failure_code=None,
                created_at=self.now,
            )
        ]
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == block.content
        )

    def test_should_renew_lease_during_execution_with_fresh_account_check(self) -> None:
        from unittest.mock import patch

        with patch(
            'shifu.intelligence.core.use_cases.process_mentor_response_use_case.Event'
        ) as event:
            event.return_value.wait.side_effect = (False, True)
            assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        renewal = self.repositories.mentor_response_attempts.renew_claim.call_args.args
        assert renewal[0] == 'attempt'
        assert renewal[1] == 'message-new'
        assert renewal[2] == self.now
        assert renewal[3] > self.now
        assert renewal[4] == 'revision'
        assert self.access.assert_current.call_count > 1

    def test_should_not_finalize_after_heartbeat_loses_claim(self) -> None:
        from unittest.mock import patch

        self.repositories.mentor_response_attempts.claim.side_effect = (True, False)

        def lose_claim(*_args: object) -> bool:
            self.repositories.mentor_response_attempts.has_claim.return_value = False
            return False

        self.repositories.mentor_response_attempts.renew_claim.side_effect = lose_claim
        with patch(
            'shifu.intelligence.core.use_cases.process_mentor_response_use_case.Event'
        ) as event:
            event.return_value.wait.side_effect = (False, True)
            assert self.subject.execute('attempt') is MentorResponseStatus.PROCESSING
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_not_called()

    def test_should_fail_queued_revocation_after_committed_start_claim(self) -> None:
        queued = replace(self.attempt, status=MentorResponseStatus.QUEUED)
        self.repositories.mentor_response_attempts.find_by_id.return_value = queued
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = queued
        self.repositories.mentor_response_attempts.find_current.return_value = queued
        self.access.assert_current.side_effect = ServiceUnavailableError()
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.FAILED,
            'revision',
        )
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_recover_expired_uncontested_claim_to_terminal_failure(self) -> None:
        self.repositories.mentor_response_attempts.has_claim.return_value = False
        self.repositories.mentor_response_attempts.claim.return_value = True
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        assert self.repositories.mentor_response_attempts.claim.call_count == 2
        assert all(
            call.args[0] == 'attempt'
            and call.args[1] == 'message-new'
            and call.args[2] == self.now
            and call.args[3] > self.now
            and call.args[4] == 'revision'
            for call in self.repositories.mentor_response_attempts.claim.call_args_list
        )
        assert all(
            call.args == ('attempt', 'message-new', self.now)
            for call in self.repositories.mentor_response_attempts.has_claim.call_args_list
        )
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.FAILED,
            'revision',
        )
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_fail_when_private_learner_message_is_missing(self) -> None:
        self.repositories.mentor_messages.find_all.return_value = ()
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_messages.add.assert_not_called()
        self.router.route.assert_not_called()

    def prepare_generated_usage(self) -> None:
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('explain',),
            clarification=None,
        )
        self.workflow.run.return_value = self.block

    def test_should_report_only_zero_for_verified_local_only_response(self) -> None:
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert all(
            call.args[1].used_tokens == 0
            for call in self.access.record_usage.call_args_list
        )
        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()

    def test_should_journal_each_call_before_reporting_actual_cumulative_usage(
        self,
    ) -> None:
        self.prepare_generated_usage()

        def reported(_grant: object, usage: object) -> None:
            assert self.repositories.mentor_response_attempts.journal_usage.called

        self.access.record_usage.side_effect = reported
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        receipts = (
            self.repositories.mentor_response_attempts.journal_usage.call_args_list
        )
        assert [call.args[3].used_tokens for call in receipts] == [120, 60]
        assert all(
            call.args[:3] == ('attempt', 'message-new', 'revision') for call in receipts
        )
        assert [call.args[3].profile for call in receipts] == ['writer', 'review']
        assert all(
            call.args[0] == self.access.authorize.return_value
            for call in self.access.record_usage.call_args_list
        )
        assert all(
            call.args[1].operation_key == 'operation'
            and call.args[1].attempt_id == 'attempt'
            and call.args[1].cancelled is False
            for call in self.access.record_usage.call_args_list
        )
        assert all(
            call.args[3].call_key.startswith('generated-0:') for call in receipts
        )
        assert self.access.record_usage.call_args.args[1].used_tokens == 180

    def test_should_account_known_rejected_candidate_calls(self) -> None:
        self.prepare_generated_usage()

        def rejected(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(
                    call_key='writer', profile='writer', used_tokens=120
                )
            )
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=60
                )
            )
            raise ServiceUnavailableError

        self.workflow.run.side_effect = rejected
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        assert self.access.record_usage.call_args.args[1].used_tokens == 180
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_preserve_unknown_primary_receipt_and_run_fallback_without_accounting_pass(
        self,
    ) -> None:
        self.prepare_generated_usage()

        def fallback(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(
                    call_key='primary', profile='writer', used_tokens=None
                )
            )
            recorder(
                MentorInferenceUsage(
                    call_key='fallback', profile='writer', used_tokens=120
                )
            )
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=60
                )
            )
            return self.block

        self.workflow.run.side_effect = fallback
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        assert self.repositories.mentor_response_attempts.journal_usage.call_count == 3
        self.access.record_usage.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_report_consumed_usage_after_cancellation(self) -> None:
        self.prepare_generated_usage()

        def cancelled(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(
                    call_key='writer', profile='writer', used_tokens=120
                )
            )
            current = replace(self.attempt, status=MentorResponseStatus.CANCELLED)
            self.repositories.mentor_response_attempts.find_by_id.return_value = current
            self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = current
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=60
                )
            )
            return self.block

        self.workflow.run.side_effect = cancelled
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        usage = self.access.record_usage.call_args.args[1]
        assert usage.used_tokens == 180
        assert usage.cancelled is True
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_replay_journal_after_external_accounting_failure(self) -> None:
        self.prepare_generated_usage()
        self.access.record_usage.side_effect = [ServiceUnavailableError(), None, None]
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        assert self.repositories.mentor_response_attempts.journal_usage.call_count == 1
        assert all(
            call.args[1].used_tokens == 120
            for call in self.access.record_usage.call_args_list
        )
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_reject_legacy_unknown_usage_even_for_local_answer(self) -> None:
        self.repositories.mentor_response_attempts.read_usage.side_effect = None
        self.repositories.mentor_response_attempts.read_usage.return_value = None
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.access.record_usage.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    @pytest.mark.parametrize(
        ('call_key', 'profile', 'used_tokens'),
        [
            ('', 'writer', 120),
            ('writer', '', 120),
            ('writer', 'writer', -1),
            ('writer', 'writer', True),
        ],
    )
    def test_should_reject_malformed_inference_receipt_without_fabricated_accounting(
        self,
        call_key: str,
        profile: str,
        used_tokens: int,
    ) -> None:
        self.prepare_generated_usage()

        def malformed(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(
                    call_key=call_key, profile=profile, used_tokens=used_tokens
                )
            )
            return self.block

        self.workflow.run.side_effect = malformed
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()
        self.access.record_usage.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_refuse_generated_answer_when_reserved_inference_has_no_receipt(
        self,
    ) -> None:
        self.prepare_generated_usage()
        self.workflow.run.side_effect = None
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_response_attempts.reserve_generation.assert_called_once()
        self.repositories.mentor_response_attempts.journal_usage.assert_not_called()
        self.access.record_usage.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_preserve_known_then_unknown_usage_without_accepting_partial_aggregate(
        self,
    ) -> None:
        self.prepare_generated_usage()

        def unknown_review(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(
                    call_key='writer', profile='writer', used_tokens=120
                )
            )
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=None
                )
            )
            return self.block

        self.workflow.run.side_effect = unknown_review
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        receipts = (
            self.repositories.mentor_response_attempts.journal_usage.call_args_list
        )
        assert [call.args[3].used_tokens for call in receipts] == [120, None]
        assert [
            call.args[1].used_tokens for call in self.access.record_usage.call_args_list
        ] == [120]
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_recheck_revoked_access_after_generation_and_account_consumed_calls(
        self,
    ) -> None:
        self.prepare_generated_usage()

        def revoked(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(
                    call_key='writer', profile='writer', used_tokens=120
                )
            )
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=60
                )
            )
            self.access.assert_current.side_effect = ServiceUnavailableError()
            return self.block

        self.workflow.run.side_effect = revoked
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        assert self.access.record_usage.call_args.args[1].used_tokens == 180
        self.repositories.mentor_messages.add.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.FAILED,
            'revision',
        )

    @pytest.mark.parametrize(
        'race', ['expired-owner', 'superseded-attempt', 'removed-session']
    )
    def test_should_not_publish_generated_content_after_final_fence_changes(
        self, race: str
    ) -> None:
        self.prepare_generated_usage()
        original = self.workflow.run.side_effect
        assert callable(original)

        def raced(
            request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            block = original(request, recorder, _inference_guard, progress_recorder)
            assert isinstance(block, MentorResponseBlock)
            if race == 'expired-owner':
                self.repositories.mentor_response_attempts.has_claim.return_value = (
                    False
                )
                self.repositories.mentor_response_attempts.claim.return_value = False
            elif race == 'superseded-attempt':
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    replace(self.attempt, id='new-attempt')
                )
            else:
                self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                    None
                )
            return block

        self.workflow.run.side_effect = raced
        assert self.subject.execute('attempt') in (
            MentorResponseStatus.PROCESSING,
            MentorResponseStatus.FAILED,
            MentorResponseStatus.CANCELLED,
        )
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    @pytest.mark.parametrize(
        'phrase',
        [
            'solução completa',
            'resposta pronta',
            'código completo',
            'resposta final',
            'resolva',
        ],
    )
    def test_should_gate_unfinished_activity_solution_and_preserve_independent_progress(
        self,
        phrase: str,
    ) -> None:
        self.context_provider.read.return_value = replace(
            self.context, activity_id='activity', skill_completed=False
        )
        messages = self.repositories.mentor_messages.find_all.return_value
        content = f'Meu progresso e {phrase} desta atividade'
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content=content),
        )
        progress = replace(
            self.block,
            block_key='progress',
            intent=MentorIntent.CONSULT_PROGRESS,
            content='Você concluiu duas Habilidades.',
        )
        solution = replace(
            self.block,
            block_key='solution',
            ordinal=1,
            content='A solução editorial completa.',
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(progress, solution),
            generation_requests=(),
            clarification=None,
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        response = self.repositories.mentor_messages.add.call_args.args[0]
        assert progress.content in response.content
        assert solution.content not in response.content
        assert 'dica' in response.content

    def test_should_allow_completed_skill_editorial_solution(self) -> None:
        self.context_provider.read.return_value = replace(
            self.context, activity_id='activity', skill_completed=True
        )
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content='Quero a solução completa desta atividade'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )

    @pytest.mark.parametrize(
        ('selection', 'proposals'),
        [
            ('segundo', ('proposal:a',)),
            ('primeiro e último', ('proposal:a', 'proposal:b')),
        ],
    )
    def test_should_clarify_invalid_or_conflicting_ordinals_from_present_list(
        self, selection: str, proposals: tuple[str, ...]
    ) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            proposals
        )
        self.context_provider.read.return_value = replace(
            self.context, eligible_references=('a', 'b')
        )
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content=f'Quero {selection}'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert self.context_provider.read.call_args_list[0].args[1] == ()
        assert (
            'nome completo'
            in self.repositories.mentor_messages.add.call_args.args[0].content
        )
        self.workflow.run.assert_not_called()

    def test_should_resolve_current_eligible_proposal_without_unnecessary_clarification(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            'proposal:a',
            'proposal:b',
        )
        self.context_provider.read.return_value = replace(
            self.context, eligible_references=('a', 'b'), resolved_references=()
        )
        messages = self.repositories.mentor_messages.find_all.return_value
        self.repositories.mentor_messages.find_all.return_value = (
            replace(messages[0], content='Quero o primeiro'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert self.context_provider.read.call_args_list[0].args[1] == ('a',)
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )

    @pytest.mark.parametrize(
        'change', ['cancelled', 'superseded', 'deleted', 'expired-claim', 'revoked']
    )
    def test_should_stop_next_inference_when_workflow_guard_loses_authority(
        self, change: str
    ) -> None:
        self.prepare_generated_usage()
        subsequent_calls: list[str] = []

        def guarded(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            assert inference_guard is not None
            inference_guard()
            recorder(
                MentorInferenceUsage(
                    call_key='writer', profile='writer', used_tokens=120
                )
            )
            if change == 'cancelled':
                current = replace(self.attempt, status=MentorResponseStatus.CANCELLED)
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    current
                )
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = current
            elif change == 'superseded':
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    replace(self.attempt, id='other-attempt')
                )
            elif change == 'deleted':
                self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                    None
                )
            elif change == 'expired-claim':
                self.repositories.mentor_response_attempts.has_claim.return_value = (
                    False
                )
                self.repositories.mentor_response_attempts.claim.return_value = False
            else:
                self.access.assert_current.side_effect = ServiceUnavailableError()
            with pytest.raises(ServiceUnavailableError):
                inference_guard()
                subsequent_calls.append('review')
            raise ServiceUnavailableError

        self.workflow.run.side_effect = guarded
        status = self.subject.execute('attempt')
        assert status is not MentorResponseStatus.COMPLETED
        assert subsequent_calls == []
        receipt = (
            self.repositories.mentor_response_attempts.journal_usage.call_args.args[3]
        )
        assert receipt.profile == 'writer'
        assert receipt.used_tokens == 120
        self.repositories.mentor_response_attempts.journal_usage.assert_called_once()
        assert all(
            call.args[1].used_tokens == 120
            for call in self.access.record_usage.call_args_list
        )
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_emit_canonical_approved_block_and_completed_events(self) -> None:
        self.repositories.mentor_response_events.next_sequence.side_effect = (2, 3)
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.repositories.mentor_response_events.append.assert_any_call(
            MentorResponseEvent(
                session_id='session',
                attempt_id='attempt',
                sequence=2,
                kind=MentorResponseEventKind.BLOCK,
                status=MentorResponseStatus.PROCESSING,
                block=self.block,
                consultation=None,
                failure_code=None,
                created_at=self.now,
            )
        )
        assert all(
            call.args == ('session',)
            for call in self.repositories.mentor_response_events.next_sequence.call_args_list
        )

    def test_should_emit_only_scoped_generic_failure_and_recover_owned_claim(
        self,
    ) -> None:
        self.router.route.side_effect = ServiceUnavailableError()
        self.repositories.mentor_response_events.next_sequence.return_value = 7
        assert self.subject.execute('attempt') is MentorResponseStatus.FAILED
        self.repositories.mentor_response_events.append.assert_called_once_with(
            MentorResponseEvent(
                session_id='session',
                attempt_id='attempt',
                sequence=7,
                kind=MentorResponseEventKind.FAILED,
                status=MentorResponseStatus.FAILED,
                block=None,
                consultation=None,
                failure_code='service_unavailable',
                created_at=self.now,
            )
        )
        assert all(
            call.args == ('account', 'session')
            for call in self.repositories.mentor_sessions.find_by_id_for_update.call_args_list
        )
        assert all(
            call.args == ('attempt',)
            for call in self.repositories.mentor_response_attempts.find_by_id_for_update.call_args_list
        )
        assert all(
            call.args == ('attempt', 'message-new', self.now)
            for call in self.repositories.mentor_response_attempts.has_claim.call_args_list
        )
        assert all(
            call.args == ('session',)
            for call in self.repositories.mentor_response_events.next_sequence.call_args_list
        )
        assert all(
            call.args[0] == self.access.authorize.return_value
            for call in self.access.assert_current.call_args_list
        )

    @pytest.mark.parametrize('missing', ['current', 'latest'])
    def test_should_refuse_local_publication_when_either_attempt_lookup_disappears(
        self, missing: str
    ) -> None:
        def route(_content: str, _context: MentorContextSnapshot) -> MentorRouteResult:
            if missing == 'current':
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
            else:
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    None
                )
            return MentorRouteResult(
                intents=(),
                local_blocks=(self.block,),
                generation_requests=(),
                clarification=None,
            )

        self.router.route.side_effect = route
        assert self.subject.execute('attempt') is not MentorResponseStatus.COMPLETED
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_return_cancelled_when_claim_lost_and_attempt_was_removed(
        self,
    ) -> None:
        def removed(*_args: object) -> bool:
            self.repositories.mentor_response_attempts.find_by_id.return_value = None
            return False

        self.repositories.mentor_response_attempts.claim.side_effect = removed
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        assert all(
            call.args == ('attempt',)
            for call in self.repositories.mentor_response_attempts.find_by_id.call_args_list
        )
        self.workflow.run.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_recover_approved_local_block_without_republishing_it(self) -> None:
        def persisted(*_args: object) -> object:
            return replace(self.snapshot, blocks=(self.block,))

        self.repositories.mentor_response_events.snapshot.side_effect = persisted
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )
        assert [
            call.args[0].kind
            for call in self.repositories.mentor_response_events.append.call_args_list
        ] == [MentorResponseEventKind.COMPLETED]

    @pytest.mark.parametrize(
        ('field', 'value'),
        [
            ('goal_id', 'goal'),
            ('skill_experience_id', 'experience'),
            ('eligible_references', ('skill',)),
            ('resolved_references', ('skill',)),
            ('facts', (('xp', '10'),)),
            ('facts', (('level', '2'),)),
            ('facts', (('streak', '3'),)),
            ('facts', (('achievements', 'Primeira conquista'),)),
        ],
    )
    def test_should_not_publish_consultation_from_context_presence(
        self, field: str, value: object
    ) -> None:
        self.context_provider.read.return_value = replace(
            self.context, **{field: value}
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert all(
            call.args[0].kind is not MentorResponseEventKind.CONSULTATION
            and call.args[0].progress is None
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_publish_only_executed_workflow_steps_in_order(self) -> None:
        self.prepare_generated_usage()
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        progress = [
            event
            for call in self.repositories.mentor_response_events.append.call_args_list
            if (event := call.args[0]).progress is not None
        ]
        assert [event.progress for event in progress] == [
            MentorWorkflowStep.WRITE_ANSWER,
            MentorWorkflowStep.REVIEW_ANSWER,
        ]
        assert all(
            event.kind is MentorResponseEventKind.STATUS
            and event.status is MentorResponseStatus.PROCESSING
            and event.consultation is None
            and event.block is None
            for event in progress
        )

    @pytest.mark.parametrize(
        'race', ['cancelled', 'superseded', 'removed', 'claim', 'access']
    )
    def test_should_fence_progress_after_authority_changes(self, race: str) -> None:
        self.prepare_generated_usage()

        def raced(
            _request: MentorGenerationRequest,
            _recorder: Callable[[MentorInferenceUsage], None] | None,
            _guard: Callable[[], None] | None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None,
        ) -> MentorResponseBlock:
            assert progress_recorder is not None
            if race == 'cancelled':
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
                    self.attempt, status=MentorResponseStatus.CANCELLED
                )
            elif race == 'superseded':
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    replace(self.attempt, id='replacement')
                )
            elif race == 'removed':
                self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                    None
                )
            elif race == 'claim':
                self.repositories.mentor_response_attempts.has_claim.return_value = (
                    False
                )
            else:
                self.access.assert_current.side_effect = ServiceUnavailableError
            progress_recorder(MentorWorkflowStep.WRITE_ANSWER)
            raise AssertionError('Progress recording must reject a stale authority')

        self.workflow.run.side_effect = raced
        assert self.subject.execute('attempt') is not MentorResponseStatus.COMPLETED
        assert all(
            call.args[0].progress is None
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    @pytest.mark.parametrize(
        ('selection', 'expected'),
        [('primeira', 'a'), ('segunda', 'b'), ('última', 'c'), ('ultima', 'c')],
    )
    def test_should_resolve_feminine_and_unaccented_ordinals(
        self, selection: str, expected: str
    ) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            'proposal:a',
            'proposal:b',
            'proposal:c',
        )
        self.context_provider.read.return_value = replace(
            self.context, eligible_references=('a', 'b', 'c')
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=f'Quero a {selection}'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert self.context_provider.read.call_args_list[0].args[1] == (expected,)
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )

    def test_should_not_treat_unselected_proposal_markers_as_resolved_references(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            'skill',
            'proposal:a',
            'proposal:b',
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert self.context_provider.read.call_args_list[0].args[1] == ('skill',)

    @pytest.mark.parametrize(
        ('content', 'matched'),
        [
            ('Quero MATEMATICA BASICA', True),
            ('Quero préMatemática básica adicional', False),
            ('Quero Matemática', False),
            ('Quero estudar geometria', False),
        ],
    )
    def test_should_resolve_only_complete_normalized_goal_title(
        self, content: str, matched: bool
    ) -> None:
        goal = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        self.context_provider.read.return_value = replace(
            self.context, facts=(('goals', f'{goal}: Matemática básica'),)
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        resolved = [call.args[1] for call in self.context_provider.read.call_args_list]
        assert ((goal,) in resolved) is matched

    @pytest.mark.parametrize(
        'activity_request',
        [
            'atividade',
            'exercício',
            'exercicio',
            'resposta',
            'solução',
            'solucao',
            '01ARZ3NDEKTSV4RRFFQ69G5FAV',
        ],
    )
    def test_should_refuse_each_diagnostic_activity_request_and_preserve_independent_facts(
        self, activity_request: str
    ) -> None:
        self.context_provider.read.return_value = replace(
            self.context,
            activity_id='01ARZ3NDEKTSV4RRFFQ69G5FAV',
            diagnostic_in_progress=True,
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=f'Explique {activity_request}'),
        )
        progress = replace(
            self.block,
            block_key='progress',
            ordinal=1,
            intent=MentorIntent.CONSULT_PROGRESS,
            content='Duas Habilidades concluídas.',
        )
        gamification = replace(
            self.block,
            block_key='xp',
            ordinal=2,
            intent=MentorIntent.CONSULT_GAMIFICATION,
            content='Você tem 10 XP.',
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block, progress, gamification),
            generation_requests=('solve',),
            clarification=None,
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_not_called()
        blocks = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block is not None
        ]
        assert [block.ordinal for block in blocks] == [0, 1, 2]
        assert all(
            isinstance(block.block_key, str) and block.block_key for block in blocks
        )
        assert blocks[0].content == progress.content
        assert blocks[1].content == gamification.content
        assert 'Não posso ajudar' in blocks[2].content
        assert all(block.content != self.block.content for block in blocks)

    def test_should_allow_unrelated_learning_topic_during_diagnostic(self) -> None:
        self.context_provider.read.return_value = replace(
            self.context, activity_id='activity', diagnostic_in_progress=True
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='Como criar um bom hábito de estudos?'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )

    def test_should_reconcile_newly_observed_durable_block_instead_of_duplicating_it(
        self,
    ) -> None:
        initial = replace(self.snapshot, blocks=())
        committed = replace(self.snapshot, blocks=(self.block,))
        reads = count()

        def observed(*_args: object) -> object:
            return initial if next(reads) == 0 else committed

        self.repositories.mentor_response_events.snapshot.side_effect = observed
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )
        assert [
            call.args[0].kind
            for call in self.repositories.mentor_response_events.append.call_args_list
        ] == [MentorResponseEventKind.COMPLETED]

    def test_should_not_discover_catalog_proposals_while_context_requires_clarification(
        self,
    ) -> None:
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(replace(self.block, intent=MentorIntent.SEARCH_CURRICULUM),),
            generation_requests=(),
            clarification='Qual Objetivo você quer usar?',
            proposed_reference_ids=('skill',),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.catalog.read_projection.assert_not_called()
        assert (
            'Qual Objetivo'
            in self.repositories.mentor_messages.add.call_args.args[0].content
        )

    def test_should_accept_confirmed_zero_cost_receipt_without_discarding_review_usage(
        self,
    ) -> None:
        self.prepare_generated_usage()

        def confirmed(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None],
            _inference_guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            recorder(
                MentorInferenceUsage(call_key='writer', profile='writer', used_tokens=0)
            )
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=60
                )
            )
            return self.block

        self.workflow.run.side_effect = confirmed
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        receipts = (
            self.repositories.mentor_response_attempts.journal_usage.call_args_list
        )
        assert [call.args[3].used_tokens for call in receipts] == [0, 60]
        assert self.access.record_usage.call_args.args[1].used_tokens == 60

    def test_should_not_publish_consultation_when_attempt_was_cancelled_after_context_read(
        self,
    ) -> None:
        self.context_provider.read.return_value = replace(self.context, goal_id='goal')
        lookups = count()

        def current(_attempt: str) -> object:
            if next(lookups) == 0:
                return self.attempt
            cancelled = replace(self.attempt, status=MentorResponseStatus.CANCELLED)
            self.repositories.mentor_response_attempts.find_by_id.return_value = (
                cancelled
            )
            self.repositories.mentor_response_attempts.find_current.return_value = (
                cancelled
            )
            return cancelled

        self.repositories.mentor_response_attempts.find_by_id_for_update.side_effect = (
            current
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    def test_should_commit_queued_start_status_and_scope_claims(self) -> None:
        queued = replace(self.attempt, status=MentorResponseStatus.QUEUED)
        self.repositories.mentor_response_attempts.find_by_id.return_value = queued
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = queued
        self.repositories.mentor_response_attempts.find_current.return_value = queued

        def transition(*args: object) -> bool:
            if args[1] is MentorResponseStatus.QUEUED:
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    self.attempt
                )
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    self.attempt
                )
            return True

        self.repositories.mentor_response_attempts.transition.side_effect = transition
        self.repositories.mentor_response_events.next_sequence.side_effect = count(2)
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.repositories.mentor_response_attempts.transition.assert_any_call(
            'attempt',
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
            'revision',
        )
        event = self.repositories.mentor_response_events.append.call_args_list[0].args[
            0
        ]
        assert all(
            call.args == ('session',)
            for call in self.repositories.mentor_response_events.next_sequence.call_args_list
        )
        assert event == MentorResponseEvent(
            session_id='session',
            attempt_id='attempt',
            sequence=2,
            kind=MentorResponseEventKind.STATUS,
            status=MentorResponseStatus.PROCESSING,
            block=None,
            consultation=None,
            failure_code=None,
            created_at=self.now,
        )
        claim = self.repositories.mentor_response_attempts.claim.call_args.args
        assert claim[:3] == ('attempt', 'message-new', self.now)
        assert claim[3] > self.now
        assert claim[4] == 'revision'
        self.repositories.mentor_response_attempts.release_claim.assert_called_once_with(
            'attempt', 'message-new'
        )
        assert all(
            call.args == ('attempt',)
            for call in self.repositories.mentor_response_attempts.find_by_id.call_args_list
        )
        assert all(
            call.args == ('attempt',)
            for call in self.repositories.mentor_response_attempts.read_usage.call_args_list
        )
        assert all(
            call.args == ('attempt',)
            for call in self.repositories.mentor_response_attempts.inference_started.call_args_list
        )
        assert all(
            call.args == (self.access.authorize.return_value,)
            for call in self.access.assert_current.call_args_list
        )

    def test_should_continue_remaining_generated_parts_after_committed_first_part(
        self,
    ) -> None:
        prior = replace(self.block, block_key='generated-0')

        def snapshot(*_args: object) -> object:
            published = tuple(
                call.args[0].block
                for call in self.repositories.mentor_response_events.append.call_args_list
                if call.args[0].block is not None
            )
            return replace(self.snapshot, blocks=(prior, *published))

        self.repositories.mentor_response_events.snapshot.side_effect = snapshot
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('first', 'second'),
            clarification=None,
        )
        self.workflow.run.return_value = replace(
            self.block,
            block_key='provider-key',
            ordinal=8,
            content='Segunda parte aprovada.',
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.workflow.run.assert_called_once()
        request = self.workflow.run.call_args.args[0]
        assert request.session_id == 'session'
        assert request.learner_message_id == 'message'
        assert request.attempt_id == 'attempt'
        assert request.requested_part == 'second'
        assert request.approved_blocks == (prior,)
        published = [
            call.args[0].block
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block is not None
        ]
        assert published == [
            replace(self.workflow.run.return_value, block_key='generated-1', ordinal=1)
        ]
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == prior.content + '\n\nSegunda parte aprovada.'
        )
        assert all(
            call.args[:2] == ('account', ())
            for call in self.context_provider.read.call_args_list
        )

    def test_should_resolve_named_catalog_entry_with_current_scope_and_original_hint(
        self,
    ) -> None:
        from shifu.shared.core.domain.structures import MentorCatalogEntry

        goal_id = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        skill_id = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
        hint = MentorContextHint(goal_id=goal_id)
        self.attempt = replace(self.attempt, context_hint=hint)
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
        self.repositories.mentor_response_attempts.find_current.return_value = (
            self.attempt
        )
        self.context = replace(
            self.context,
            eligible_references=(skill_id,),
            resolved_references=(skill_id,),
            facts=(('xp', '15'), ('goals', f'{goal_id}: Matemática: básica')),
        )
        self.context_provider.read.return_value = self.context
        content = 'Quero Matemática: básica e Frações equivalentes'
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content),
        )
        self.catalog.search.return_value = (
            MentorCatalogEntry(
                reference_id=skill_id,
                kind='skill',
                skill_id=skill_id,
                competency_id=None,
                title='Frações equivalentes',
                description=None,
                concept_ids=(),
                source_version='v1',
            ),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.catalog.search.assert_called_once_with('account', content, (skill_id,))
        self.context_provider.read.assert_any_call(
            'account',
            (goal_id,),
            goal_id=goal_id,
            material_id=None,
            skill_id=None,
            competency_id=None,
            activity_id=None,
        )
        self.context_provider.read.assert_any_call(
            'account',
            (goal_id, skill_id),
            goal_id=goal_id,
            material_id=None,
            skill_id=None,
            competency_id=None,
            activity_id=None,
        )
        self.repositories.mentor_response_attempts.update_references.assert_called_once_with(
            'attempt', (skill_id,), 'revision'
        )

    def test_should_exclude_prior_attempt_blocks_from_current_response(self) -> None:
        previous = replace(
            self.snapshot,
            attempt_id='previous-attempt',
            blocks=(
                replace(self.block, block_key='prior', content='Resposta anterior.'),
            ),
        )
        reads = count()

        def snapshot(*_args: object) -> object:
            if next(reads) == 0:
                return previous
            published = tuple(
                call.args[0].block
                for call in self.repositories.mentor_response_events.append.call_args_list
                if call.args[0].block is not None
            )
            return replace(self.snapshot, blocks=published)

        self.repositories.mentor_response_events.snapshot.side_effect = snapshot
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        response = self.repositories.mentor_messages.add.call_args.args[0]
        assert response.content == self.block.content
        assert 'Resposta anterior.' not in response.content

    def test_should_not_claim_superseded_attempt_at_start(self) -> None:
        self.repositories.mentor_response_attempts.find_current.return_value = replace(
            self.attempt, id='newer-attempt'
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.PROCESSING
        self.repositories.mentor_response_attempts.claim.assert_not_called()
        self.router.route.assert_not_called()
        self.repositories.mentor_response_events.append.assert_not_called()
        self.repositories.mentor_messages.add.assert_not_called()

    @pytest.mark.parametrize(
        'guard_lookup',
        [
            'session_account',
            'session_id',
            'attempt_id',
            'latest_account',
            'latest_session',
        ],
    )
    def test_should_infer_only_through_owned_current_repository_scope(
        self, guard_lookup: str
    ) -> None:
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('Explicar conceito',),
            clarification=None,
        )

        def run(
            request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None] | None = None,
            guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            assert guard is not None and recorder is not None
            recorder(
                MentorInferenceUsage(
                    call_key='writer:0', profile='writer', used_tokens=120
                )
            )

            def owned_session(account: str, session: str) -> object | None:
                return (
                    self.session
                    if (account, session) == ('account', 'session')
                    else None
                )

            def owned_attempt(attempt: str) -> object | None:
                return self.attempt if attempt == 'attempt' else None

            def latest_attempt(account: str, session: str) -> object | None:
                return (
                    self.attempt
                    if (account, session) == ('account', 'session')
                    else None
                )

            if guard_lookup.startswith('session'):
                self.repositories.mentor_sessions.find_by_id_for_update.side_effect = (
                    owned_session
                )
            elif guard_lookup == 'attempt_id':
                self.repositories.mentor_response_attempts.find_by_id.side_effect = (
                    owned_attempt
                )
            else:
                self.repositories.mentor_response_attempts.find_current.side_effect = (
                    latest_attempt
                )
            guard()
            recorder(
                MentorInferenceUsage(
                    call_key='review:0', profile='review', used_tokens=60
                )
            )
            assert (request.session_id, request.attempt_id) == ('session', 'attempt')
            return self.block

        self.workflow.run.side_effect = run
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )
        assert self.access.record_usage.call_args.args[1].used_tokens == 180
        if guard_lookup.startswith('session'):
            assert all(
                call.args == ('account', 'session')
                for call in self.repositories.mentor_sessions.find_by_id_for_update.call_args_list
            )
        elif guard_lookup == 'attempt_id':
            assert all(
                call.args == ('attempt',)
                for call in self.repositories.mentor_response_attempts.find_by_id.call_args_list
            )
        else:
            assert all(
                call.args == ('account', 'session')
                for call in self.repositories.mentor_response_attempts.find_current.call_args_list
            )

    def test_should_offer_ordered_eligible_catalog_results_for_search_alone(
        self,
    ) -> None:
        from shifu.shared.core.domain.structures import MentorCatalogEntry

        self.context_provider.read.return_value = replace(
            self.context, eligible_references=('skill-a', 'skill-b')
        )
        self.catalog.read_projection.return_value = tuple(
            MentorCatalogEntry(
                reference_id=reference,
                kind='skill',
                skill_id=reference,
                competency_id=None,
                title=title,
                description=None,
                concept_ids=(),
                source_version='v1',
            )
            for reference, title in (('skill-a', 'Frações'), ('skill-b', 'Equações'))
        )
        self.router.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(replace(self.block, intent=MentorIntent.SEARCH_CURRICULUM),),
            generation_requests=(),
            clarification=None,
            proposed_reference_ids=('skill-b', 'ineligible', 'skill-a'),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == '1. Equações\n2. Frações'
        )
        self.repositories.mentor_response_attempts.update_references.assert_any_call(
            'attempt', ('proposal:skill-b', 'proposal:skill-a'), 'revision'
        )
        self.workflow.run.assert_not_called()

    @pytest.mark.parametrize('fact_key', ['eligible_materials', 'activities'])
    def test_should_resolve_named_goal_only_from_goal_facts_namespace(
        self, fact_key: str
    ) -> None:
        goal_id = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        item_id = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
        title = 'Matemática básica'
        self.context = replace(
            self.context,
            goal_id=goal_id,
            facts=(('goals', f'{goal_id}: {title}'), (fact_key, f'{item_id}: {title}')),
            eligible_references=(item_id,),
            resolved_references=(goal_id,),
        )
        self.context_provider.read.return_value = self.context
        content = f'Quero consultar {title}'
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content),
        )
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        self.context_provider.read.assert_any_call('account', (goal_id,))
        assert all(
            call.args[1] in ((), (goal_id,))
            for call in self.context_provider.read.call_args_list
        )
        self.catalog.search.assert_called_once_with('account', content, (item_id,))
        self.router.route.assert_called_once_with(content, self.context)
        self.repositories.mentor_response_attempts.update_references.assert_called_once_with(
            'attempt', (goal_id,), 'revision'
        )
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )
        assert all(
            'mais de um Objetivo' not in call.args[0].block.content
            for call in self.repositories.mentor_response_events.append.call_args_list
            if call.args[0].block is not None
        )
        self.workflow.run.assert_not_called()

    def test_should_report_cancelled_consumption_when_cancel_wins_after_known_receipts(
        self,
    ) -> None:
        self.prepare_generated_usage()

        def run(
            _request: MentorGenerationRequest,
            recorder: Callable[[MentorInferenceUsage], None] | None = None,
            guard: Callable[[], None] | None = None,
            progress_recorder: Callable[[MentorWorkflowStep], None] | None = None,
        ) -> MentorResponseBlock:
            assert recorder is not None and guard is not None
            guard()
            recorder(
                MentorInferenceUsage(
                    call_key='writer', profile='writer', used_tokens=120
                )
            )
            guard()
            recorder(
                MentorInferenceUsage(
                    call_key='review', profile='review', used_tokens=60
                )
            )
            assert all(
                not call.args[1].cancelled
                for call in self.access.record_usage.call_args_list
            )
            return self.block

        def cancel_at_publish(
            _account: str, _references: tuple[str, ...], **_hints: str | None
        ) -> MentorContextSnapshot:
            if self.workflow.run.called:
                cancelled = replace(self.attempt, status=MentorResponseStatus.CANCELLED)
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    cancelled
                )
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = cancelled
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    cancelled
                )
            return self.context

        self.workflow.run.side_effect = run
        self.context_provider.read.side_effect = cancel_at_publish
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        receipts = self.repositories.mentor_response_attempts.read_usage('attempt')
        assert [receipt.used_tokens for receipt in receipts] == [120, 60]
        usage = self.access.record_usage.call_args.args[1]
        assert usage.used_tokens == 180 and usage.cancelled is True
        self.repositories.mentor_messages.add.assert_not_called()
        assert not any(
            call.args[0].block is not None
            for call in self.repositories.mentor_response_events.append.call_args_list
        )

    def test_should_preserve_original_goal_and_skill_hint_for_fresh_generation_context(
        self,
    ) -> None:
        goal_id = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        skill_id = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
        hint = MentorContextHint(goal_id=goal_id, skill_id=skill_id)
        self.attempt = replace(self.attempt, context_hint=hint)
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            self.attempt
        )
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = self.attempt
        self.repositories.mentor_response_attempts.find_current.return_value = (
            self.attempt
        )
        self.context = replace(
            self.context,
            goal_id=goal_id,
            skill_id=skill_id,
            resolved_references=(goal_id,),
            eligible_references=(skill_id,),
        )
        self.prepare_generated_usage()

        def read(
            _account: str, _references: tuple[str, ...], **hints: str | None
        ) -> MentorContextSnapshot:
            if self.router.route.called:
                assert hints['goal_id'] == goal_id
                assert hints['skill_id'] == skill_id
            return self.context

        self.context_provider.read.side_effect = read
        assert self.subject.execute('attempt') is MentorResponseStatus.COMPLETED
        request = self.workflow.run.call_args.args[0]
        assert request.context == self.context
        assert request.context.resolved_references == (goal_id,)
        assert request.context.eligible_references == (skill_id,)
        assert (
            self.repositories.mentor_messages.add.call_args.args[0].content
            == self.block.content
        )

    def test_should_return_cancelled_when_session_deleted_after_block_commit_before_finalize(
        self,
    ) -> None:
        deleted = False

        def commit(_type: object, _value: object, _traceback: object) -> bool:
            nonlocal deleted
            if not deleted and any(
                call.args[0].kind is MentorResponseEventKind.BLOCK
                for call in self.repositories.mentor_response_events.append.call_args_list
            ):
                deleted = True
                self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
                    None
                )
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    None
                )
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    None
                )
            return False

        self.database.transaction.return_value.__exit__.side_effect = commit
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        assert deleted is True
        self.repositories.mentor_messages.add.assert_not_called()
        assert [
            call.args[0].kind
            for call in self.repositories.mentor_response_events.append.call_args_list
        ] == [MentorResponseEventKind.BLOCK]

    def test_should_return_cancelled_when_session_deleted_after_usage_before_finalize(
        self,
    ) -> None:
        deleted = False

        def lock(account: str, session: str) -> object | None:
            nonlocal deleted
            assert (account, session) == ('account', 'session')
            if any(
                call.args[0].kind is MentorResponseEventKind.BLOCK
                for call in self.repositories.mentor_response_events.append.call_args_list
            ):
                deleted = True
                self.repositories.mentor_response_attempts.find_by_id.return_value = (
                    None
                )
                self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None
                self.repositories.mentor_response_attempts.find_current.return_value = (
                    None
                )
                return None
            return self.session

        self.repositories.mentor_sessions.find_by_id_for_update.side_effect = lock
        assert self.subject.execute('attempt') is MentorResponseStatus.CANCELLED
        assert deleted is True
        self.repositories.mentor_messages.add.assert_not_called()
        assert [
            call.args[0].kind
            for call in self.repositories.mentor_response_events.append.call_args_list
        ] == [MentorResponseEventKind.BLOCK]
