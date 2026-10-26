from dataclasses import replace
from datetime import timedelta

from unittest.mock import create_autospec

import pytest
from datetime import UTC, datetime

from shifu.fakers.intelligence.entities import LearnerMemoryFaker
from shifu.intelligence.core.domain.entities import MentorMessage, MentorSessionSummary
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    MentorActionKind,
    MentorSummaryExcerptKind,
    MentorAttachmentStatus,
    MentorIntent,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorActionCandidateGoal,
    MentorActionProposalDraft,
    MentorContextHint,
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
    LearnerMemoryContext,
    MentorAttachmentView,
    MentorIntentMatch,
    MentorResponseBlock,
    MentorRouteResult,
)
from shifu.intelligence.core.interfaces import (
    LearnerMemorySimilarityProvider,
    MentorGenerationLimitProvider,
)
from shifu.shared.core.domain.structures import (
    MentorGoalDestination,
    MentorGoalDestinations,
)
from shifu.shared.core.interfaces import MentorGoalDestinationsProvider
from shifu.intelligence.core.domain.structures.prepared_mentor_response import (
    PreparedMentorResponse,
)
from shifu.intelligence.core.use_cases.prepare_mentor_response_use_case import (
    PrepareMentorResponseUseCase,
)
from shifu.shared.core.domain.errors import NotFoundError, ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorCatalogEntry
from tests.intelligence.core.use_cases.mentor_response_phase_test_setup import (
    MentorResponsePhaseTestSetup,
    context_snapshot,
)


class _PrepareSubjectSetup(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase(MentorResponseStatus.QUEUED)
        self.memory_similarity = create_autospec(
            LearnerMemorySimilarityProvider, instance=True
        )
        self.memory_similarity.similarity.return_value = 0.0
        self.generation_limit = create_autospec(
            MentorGenerationLimitProvider, instance=True
        )
        self.generation_limit.try_acquire.return_value = True
        self.repositories.mentor_messages.find_memory_analysis.return_value = None
        self.repositories.learner_memories.find_many_by_account.return_value = ()
        self.goal_destinations = create_autospec(
            MentorGoalDestinationsProvider, instance=True
        )
        self.goal_destinations.read.return_value = MentorGoalDestinations(goals=())
        self.subject = PrepareMentorResponseUseCase(
            self.database,
            self.clock,
            self.access,
            self.context_provider,
            self.route_provider,
            self.catalog_provider,
            self.attachment_context_use_case,
            self.memory_similarity,
            0.3,
            self.generation_limit,
            self.goal_destinations,
        )
        processing_attempt = replace(
            self.attempt, status=MentorResponseStatus.PROCESSING
        )
        self.repositories.mentor_response_attempts.find_by_id.return_value = (
            processing_attempt
        )
        self.repositories.mentor_response_attempts.find_current.return_value = (
            processing_attempt
        )


class TestPrepareMentorResponseUseCase(_PrepareSubjectSetup):
    def test_should_claim_and_prepare_local_response_without_private_events(
        self,
    ) -> None:
        prepared = self.subject.execute('attempt', 'owner')

        assert prepared == PreparedMentorResponse(
            attempt_id='attempt',
            execution_owner='owner',
            account_id='account',
            session_id='session',
            learner_message_id='message',
            context=self.context,
            local_blocks=(self.block,),
            attachment_request=None,
        )
        self.repositories.mentor_response_attempts.claim.assert_called_once_with(
            'attempt', 'owner', self.now, self.now + timedelta(minutes=5), 'revision'
        )
        self.repositories.mentor_response_attempts.transition.assert_called_once_with(
            'attempt',
            MentorResponseStatus.QUEUED,
            MentorResponseStatus.PROCESSING,
            'revision',
        )
        event = self.repositories.mentor_response_events.append.call_args.args[0]
        assert event.kind is MentorResponseEventKind.STATUS
        assert event.status is MentorResponseStatus.PROCESSING
        assert event.block is None
        assert event.consultation is None
        assert event.failure_code is None

    def test_should_return_none_when_attempt_is_not_the_current_claimable_attempt(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = None

        assert self.subject.execute('missing', 'owner') is None

        self.access.assert_current.assert_not_called()
        self.repositories.mentor_messages.find_all.assert_not_called()

    def test_should_return_none_when_session_or_latest_attempt_is_missing(self) -> None:
        self.repositories.mentor_sessions.find_by_id_for_update.return_value = None
        assert self.subject.execute('attempt', 'owner') is None
        self.repositories.mentor_response_attempts.claim.assert_not_called()

        self.repositories.mentor_sessions.find_by_id_for_update.return_value = (
            self.session
        )
        self.repositories.mentor_response_attempts.find_current.return_value = None
        assert self.subject.execute('attempt', 'owner') is None
        self.repositories.mentor_response_attempts.claim.assert_not_called()

    def test_should_return_none_when_claim_or_queued_transition_is_rejected(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.claim.return_value = False
        assert self.subject.execute('attempt', 'owner') is None
        self.repositories.mentor_response_attempts.transition.assert_not_called()

        self.repositories.mentor_response_attempts.claim.return_value = True
        self.repositories.mentor_response_attempts.transition.return_value = False
        assert self.subject.execute('attempt', 'owner') is None
        self.repositories.mentor_response_events.append.assert_not_called()

    def test_should_fail_closed_when_learner_message_is_missing(self) -> None:
        self.repositories.mentor_messages.find_all.return_value = ()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

    def test_should_fail_closed_when_reference_update_or_entitlement_is_stale(
        self,
    ) -> None:
        self.repositories.mentor_response_attempts.update_references.return_value = (
            False
        )

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

        self.repositories.mentor_response_attempts.update_references.return_value = True
        self.access.assert_current.side_effect = ServiceUnavailableError()
        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

    @pytest.mark.parametrize('content', ['', ' \n\t '])
    def test_should_ask_attachment_intent_without_routing_or_model_request(
        self, content: str
    ) -> None:
        attachment = MentorAttachmentView(
            attachment_id='ready',
            filename='image.png',
            media_type='image/png',
            size_bytes=20,
            status=MentorAttachmentStatus.READY,
            failure_code=None,
            analyzed_pages=(1,),
            illegible_pages=(),
            uninterpreted_pages=(),
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content, attachments=(attachment,)),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert len(prepared.local_blocks) == 1
        assert prepared.local_blocks[0].content == 'Como posso ajudar com os anexos?'
        assert prepared.attachment_request is None
        self.route_provider.route.assert_not_called()
        self.attachment_context_use_case.execute.assert_not_called()
        self.access.assert_current.assert_called()

    def test_should_keep_a_generation_request_local_when_every_part_has_a_curated_answer(
        self,
    ) -> None:
        approved = replace(self.block, block_key='approved', ordinal=0)
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(approved,)
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('Explicar a próxima etapa.',),
            clarification=None,
            unanswered_requests=(),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks == (self.block,)
        assert prepared.attachment_request is None
        assert prepared.generation_fallback is None
        self.attachment_context_use_case.execute.assert_not_called()
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_prepare_attachment_generation_with_history_and_approved_prefix(
        self,
    ) -> None:
        approved = replace(self.block, block_key='approved', ordinal=0)
        attachment = MentorAttachmentView(
            attachment_id='ready',
            filename='material.pdf',
            media_type='application/pdf',
            size_bytes=20,
            status=MentorAttachmentStatus.READY,
            failure_code=None,
            analyzed_pages=(1,),
            illegible_pages=(),
            uninterpreted_pages=(),
        )
        message = replace(
            self.message,
            content='Explique este trecho do documento.',
            attachments=(attachment,),
        )
        self.repositories.mentor_messages.find_all.return_value = (message,)
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(approved,)
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('Explicar a próxima etapa.',),
            clarification=None,
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.history == (message,)
        assert prepared.attachment_request.context == self.context
        assert prepared.attachment_request.approved_blocks == (approved,)
        assert prepared.attachment_request.requested_part == 'Explicar a próxima etapa.'
        assert prepared.attachment_request.attachment_context == self.attachment_context

    def test_should_load_only_ready_attachments_and_requested_pages(self) -> None:
        ready = MentorAttachmentView(
            attachment_id='ready',
            filename='material.pdf',
            media_type='application/pdf',
            size_bytes=20,
            status=MentorAttachmentStatus.READY,
            failure_code=None,
            analyzed_pages=(1, 2, 3),
            illegible_pages=(),
            uninterpreted_pages=(),
        )
        partial = replace(
            ready, attachment_id='partial', status=MentorAttachmentStatus.PARTIAL
        )
        failed = replace(
            ready, attachment_id='failed', status=MentorAttachmentStatus.FAILED
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(
                self.message,
                content='Analise o documento, páginas 2, página 2 e página 3.',
                attachments=(ready, partial, failed),
            ),
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('Resuma o arquivo.',),
            clarification=None,
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.attachment_context == self.attachment_context
        self.attachment_context_use_case.execute.assert_called_once_with(
            account_id='account',
            session_id='session',
            attachment_ids=('ready', 'partial'),
            page_numbers=(2, 3),
        )

    @pytest.mark.parametrize(
        ('content', 'attachments'),
        [
            ('Explique o conceito.', ()),
            (
                'Fale sobre o documento.',
                (
                    MentorAttachmentView(
                        attachment_id='processing',
                        filename='material.pdf',
                        media_type='application/pdf',
                        size_bytes=20,
                        status=MentorAttachmentStatus.PROCESSING,
                        failure_code=None,
                        analyzed_pages=(),
                        illegible_pages=(),
                        uninterpreted_pages=(),
                    ),
                ),
            ),
        ],
    )
    def test_should_skip_attachment_lookup_without_request_or_eligible_file(
        self, content: str, attachments: tuple[MentorAttachmentView, ...]
    ) -> None:
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content, attachments=attachments),
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(),
            generation_requests=('gerar',),
            clarification=None,
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.attachment_request is None
        self.attachment_context_use_case.execute.assert_not_called()

    def test_should_apply_context_clarifications_and_catalog_proposals(self) -> None:
        reference = '01J7N3V8WX8Y6QKR4A5C6D7E8F'
        entry = MentorCatalogEntry(
            reference_id=reference,
            kind='lesson',
            skill_id='skill',
            competency_id=None,
            title='Álgebra básica',
            description=None,
            concept_ids=(),
            source_version='v1',
        )
        search_block = replace(
            self.block, intent=MentorIntent.SEARCH_CURRICULUM, content=''
        )
        initial = context_snapshot(
            eligible_references=(reference,),
            resolved_references=('skill',),
            facts=(('context_clarification', 'Qual assunto?'),),
        )
        self.context_provider.read.return_value = initial
        self.catalog_provider.read_projection.return_value = (entry,)
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(search_block,),
            generation_requests=('gerar',),
            clarification=None,
            proposed_reference_ids=(reference, 'missing', reference),
        )
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            f'proposal:{reference}',
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks[0].content == 'Qual assunto?'
        assert prepared.attachment_request is None
        assert len(self.route_provider.route.call_args.args) == 2
        self.catalog_provider.read_projection.assert_not_called()
        assert (
            self.repositories.mentor_response_attempts.update_references.call_count == 1
        )

    def test_should_propose_catalog_entries_only_when_currently_eligible(self) -> None:
        reference = '01J7N3V8WX8Y6QKR4A5C6D7E8F'
        other = '01J7N3V8WX8Y6QKR4A5C6D7E8H'
        eligible = MentorCatalogEntry(
            reference_id=reference,
            kind='lesson',
            skill_id='skill',
            competency_id=None,
            title='Álgebra básica',
            description=None,
            concept_ids=(),
            source_version='v1',
        )
        excluded = replace(eligible, reference_id=other, title='Outra aula')
        self.context = context_snapshot(eligible_references=(reference,))
        self.context_provider.read.return_value = self.context
        search_block = replace(
            self.block, intent=MentorIntent.SEARCH_CURRICULUM, content='Busca'
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(search_block,),
            generation_requests=(),
            clarification=None,
            proposed_reference_ids=(other, reference, reference),
        )
        self.catalog_provider.read_projection.return_value = (eligible, excluded)

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks[0].content == '1. Álgebra básica'
        self.repositories.mentor_response_attempts.update_references.assert_any_call(
            'attempt', ('proposal:01J7N3V8WX8Y6QKR4A5C6D7E8F',), 'revision'
        )

    def test_should_not_propose_when_route_clarifies_or_catalog_is_empty(self) -> None:
        search_block = replace(
            self.block, intent=MentorIntent.SEARCH_CURRICULUM, content='Busca'
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(search_block,),
            generation_requests=(),
            clarification='Qual aula?',
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks[0].block_key == 'clarification'
        assert prepared.attachment_request is None
        self.catalog_provider.read_projection.assert_not_called()

    @pytest.mark.parametrize(
        ('diagnostic', 'activity_id', 'content', 'expected_key'),
        [
            (True, None, 'Ajude com a atividade', 'diagnostic-boundary'),
            (
                False,
                'activity',
                'Dê a solução completa para activity',
                'unfinished-activity-boundary',
            ),
        ],
    )
    def test_should_enforce_pedagogical_activity_boundaries(
        self, diagnostic: bool, activity_id: str | None, content: str, expected_key: str
    ) -> None:
        self.context = context_snapshot(
            diagnostic_in_progress=diagnostic,
            activity_id=activity_id,
            skill_completed=False,
        )
        self.context_provider.read.return_value = self.context
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content),
        )
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('Não gere.',),
            clarification=None,
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert tuple(block.block_key for block in prepared.local_blocks) == (
            expected_key,
        )
        assert prepared.attachment_request is None

    def test_should_resolve_named_goal_and_catalog_title_with_original_hints(
        self,
    ) -> None:
        goal = '01J7N3V8WX8Y6QKR4A5C6D7E8F'
        catalog_id = '01J7N3V8WX8Y6QKR4A5C6D7EG'
        entry = MentorCatalogEntry(
            reference_id=catalog_id,
            kind='lesson',
            skill_id='skill',
            competency_id=None,
            title='Álgebra básica',
            description=None,
            concept_ids=(),
            source_version='v1',
        )
        self.context = context_snapshot(facts=(('goals', f'{goal}: Meu Objetivo'),))
        self.context_provider.read.side_effect = (
            self.context,
            self.context,
            context_snapshot(resolved_references=(goal, catalog_id)),
        )
        self.catalog_provider.search.return_value = (entry,)
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='Explique Meu Objetivo e Álgebra básica.'),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert self.context_provider.read.call_args_list[1].args[1] == (goal,)
        assert self.context_provider.read.call_args_list[2].args[1] == (
            goal,
            catalog_id,
        )

    def test_should_clarify_ambiguous_named_goals(self) -> None:
        first = '01J7N3V8WX8Y6QKR4A5C6D7E8F'
        second = '01J7N3V8WX8Y6QKR4A5C6D7E8H'
        self.context = context_snapshot(
            facts=(('goals', f'{first}: Álgebra'), ('goals', f'{second}: Álgebra'))
        )
        self.context_provider.read.return_value = self.context
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='Quero Álgebra.'),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks[0].content.startswith(
            'Encontrei mais de um Objetivo'
        )
        self.catalog_provider.search.assert_not_called()

    @pytest.mark.parametrize(
        ('content', 'continuity', 'expected'),
        [
            (
                'consulte 01J7N3V8WX8Y6QKR4A5C6D7E8F',
                ('ref-a', 'proposal:ref-b'),
                ('01J7N3V8WX8Y6QKR4A5C6D7E8F',),
            ),
            ('o primeiro', ('proposal:ref-a', 'proposal:ref-b'), ('ref-a',)),
            ('o segundo', ('proposal:ref-a', 'proposal:ref-b'), ('ref-b',)),
            ('o último', ('proposal:ref-a', 'proposal:ref-b'), ('ref-b',)),
        ],
    )
    def test_should_select_explicit_and_ordinal_continuity_references(
        self, content: str, continuity: tuple[str, ...], expected: tuple[str, ...]
    ) -> None:
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content),
        )
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            continuity
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert self.context_provider.read.call_args.args[1] == expected

    @pytest.mark.parametrize(
        'continuity',
        [
            (),
            ('proposal:ref-a', 'proposal:ref-b'),
        ],
    )
    def test_should_clarify_ambiguous_or_missing_ordinal_references(
        self, continuity: tuple[str, ...]
    ) -> None:
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='o primeiro e o último'),
        )
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            continuity
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert self.context_provider.read.call_args.args[1] == ()
        assert prepared.local_blocks[0].block_key == 'clarification'
        assert prepared.local_blocks[0].content.startswith(
            'Qual item da lista você quer consultar?'
        )

    def test_should_revalidate_removed_proposals(self) -> None:
        removed = '01J7N3V8WX8Y6QKR4A5C6D7E8F'
        current = '01J7N3V8WX8Y6QKR4A5C6D7E8H'
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='o primeiro'),
        )
        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            f'proposal:{removed}',
        )
        self.context_provider.read.return_value = context_snapshot(
            eligible_references=(current,)
        )

        removed_prepared = self.subject.execute('attempt', 'owner')

        assert removed_prepared is not None
        assert removed_prepared.local_blocks[0].block_key == 'clarification'
        assert removed_prepared.local_blocks[0].content.startswith(
            'Esse item não está disponível'
        )

        self.repositories.mentor_response_attempts.find_continuity.return_value = (
            f'proposal:{current}',
        )
        current_prepared = self.subject.execute('attempt', 'owner')

        assert current_prepared is not None
        assert current_prepared.local_blocks == (self.block,)

    def test_should_normalize_catalog_titles_and_require_word_boundaries(self) -> None:
        entry = MentorCatalogEntry(
            reference_id='01J7N3V8WX8Y6QKR4A5C6D7E8F',
            kind='lesson',
            skill_id='skill',
            competency_id=None,
            title='Álgebra básica',
            description=None,
            concept_ids=(),
            source_version='v1',
        )
        self.catalog_provider.search.return_value = (entry,)
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='Estude algebra basica agora'),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert self.context_provider.read.call_count == 2

        self.context_provider.read.reset_mock()
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='álgebras'),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert self.context_provider.read.call_count == 1

    def ready_summary(self) -> tuple[MentorSessionSummary, MentorMessage]:
        source = replace(
            self.message,
            id='old-learner',
            content='Meu laço não mostra o último item.',
            created_at=datetime(2026, 10, 1, tzinfo=UTC),
        )
        started = MentorSessionSummary.start(
            id='summary',
            account_id='account',
            session_id='session',
            attempt_id='old-attempt',
            version=2,
            boundary=MentorSummaryBoundary(
                message_id='old-boundary', created_at=datetime(2026, 10, 2, tzinfo=UTC)
            ),
            covered_message_count=21,
            first_message_id='old-learner',
            now=self.now,
        )
        ready = started.complete(
            MentorConversationSummaryDraft(
                topics=('range', 'listas'),
                excerpts=(
                    MentorSummaryExcerptSpan(
                        message_id='old-learner',
                        start=0,
                        end=34,
                        kind=MentorSummaryExcerptKind.DOUBT,
                    ),
                ),
                algorithm_version='v1',
            ),
            self.now,
        )
        return ready, source

    def attachment_message(self) -> MentorMessage:
        attachment = MentorAttachmentView(
            attachment_id='ready',
            filename='material.pdf',
            media_type='application/pdf',
            size_bytes=20,
            status=MentorAttachmentStatus.READY,
            failure_code=None,
            analyzed_pages=(1,),
            illegible_pages=(),
            uninterpreted_pages=(),
        )
        return replace(
            self.message,
            content='Explique este trecho do documento.',
            attachments=(attachment,),
        )

    def test_should_read_only_messages_after_the_boundary_and_render_the_summary(
        self,
    ) -> None:
        ready, source = self.ready_summary()
        message = self.attachment_message()
        summaries = self.repositories.mentor_session_summaries
        summaries.find_ready.return_value = ready
        self.repositories.mentor_messages.find_range.return_value = (message,)
        self.repositories.mentor_messages.find_by_ids.return_value = (source,)
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('Explicar a próxima etapa.',),
            clarification=None,
        )

        prepared = self.subject.execute('attempt', 'owner')

        self.repositories.mentor_messages.find_all.assert_not_called()
        self.repositories.mentor_messages.find_range.assert_called_once_with(
            'account', 'session', ready.boundary
        )
        self.repositories.mentor_messages.find_by_ids.assert_called_once_with(
            'account', 'session', ('old-learner',)
        )
        assert prepared is not None and prepared.attachment_request is not None
        request = prepared.attachment_request
        assert request.history == (message,)
        assert request.summary == MentorConversationSummaryContext.from_summary(
            ready, (source,)
        )
        assert request.summary is not None
        assert request.summary.topics == ('range', 'listas')
        assert request.context == self.context
        assert request.requested_part == 'Explicar a próxima etapa.'
        assert request.attachment_context == self.attachment_context

    def test_should_pass_the_summary_topics_to_the_router(self) -> None:
        ready, source = self.ready_summary()
        self.repositories.mentor_session_summaries.find_ready.return_value = ready
        self.repositories.mentor_messages.find_range.return_value = (self.message,)
        self.repositories.mentor_messages.find_by_ids.return_value = (source,)

        self.subject.execute('attempt', 'owner')

        self.route_provider.route.assert_called_once_with(
            self.message.content, self.context, ('range', 'listas')
        )

    def test_should_read_fresh_context_with_the_same_hints_and_references(self) -> None:
        ready, source = self.ready_summary()
        self.repositories.mentor_session_summaries.find_ready.return_value = ready
        self.repositories.mentor_messages.find_range.return_value = (self.message,)
        self.repositories.mentor_messages.find_by_ids.return_value = (source,)

        self.subject.execute('attempt', 'owner')

        self.context_provider.read.assert_called_once_with('account', ())

    def test_should_keep_todays_inputs_without_a_ready_summary(self) -> None:
        message = self.attachment_message()
        self.repositories.mentor_messages.find_all.return_value = (message,)
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=(self.block,),
            generation_requests=('Explicar.',),
            clarification=None,
        )

        prepared = self.subject.execute('attempt', 'owner')

        self.repositories.mentor_messages.find_range.assert_not_called()
        self.repositories.mentor_messages.find_by_ids.assert_not_called()
        self.route_provider.route.assert_called_once_with(message.content, self.context)
        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.history == (message,)
        assert prepared.attachment_request.summary is None

    def test_should_fail_closed_when_the_pending_message_is_not_after_the_boundary(
        self,
    ) -> None:
        ready, source = self.ready_summary()
        self.repositories.mentor_session_summaries.find_ready.return_value = ready
        self.repositories.mentor_messages.find_range.return_value = ()
        self.repositories.mentor_messages.find_by_ids.return_value = (source,)

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

    def test_should_fail_closed_when_a_summary_source_message_is_missing(self) -> None:
        ready, _ = self.ready_summary()
        self.repositories.mentor_session_summaries.find_ready.return_value = ready
        self.repositories.mentor_messages.find_range.return_value = (self.message,)
        self.repositories.mentor_messages.find_by_ids.return_value = ()

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')


class TestPrepareMentorResponseMemories(_PrepareSubjectSetup):
    """RF-07 acknowledgement of statement-only messages and RF-08 memory selection."""

    _ACKNOWLEDGEMENT = 'Anotado. Vou considerar isso nas próximas explicações.'

    def _abstention(self) -> MentorResponseBlock:
        return MentorResponseBlock(
            block_key=PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY,
            ordinal=0,
            intent=None,
            content='Ainda não encontrei uma resposta local confiável.',
        )

    def _statement_receipt(self, statement_only: bool = True) -> None:
        self.repositories.mentor_messages.find_memory_analysis.return_value = (
            self.now,
            statement_only,
        )

    def _route(
        self,
        blocks: tuple[MentorResponseBlock, ...],
        *,
        intents: tuple[MentorIntentMatch, ...] = (),
        requests: tuple[str, ...] = ('Responder à mensagem.',),
        clarification: str | None = None,
    ) -> None:
        self.route_provider.route.return_value = MentorRouteResult(
            intents=intents,
            local_blocks=blocks,
            generation_requests=requests,
            clarification=clarification,
        )

    def _ready_attachment(self) -> MentorAttachmentView:
        return MentorAttachmentView(
            attachment_id='ready',
            filename='material.pdf',
            media_type='application/pdf',
            size_bytes=20,
            status=MentorAttachmentStatus.READY,
            failure_code=None,
            analyzed_pages=(1,),
            illegible_pages=(),
            uninterpreted_pages=(),
        )

    def test_should_define_the_abstention_key_used_by_the_local_route(self) -> None:
        import hashlib

        expected = hashlib.sha256(b'local-abstention').hexdigest()[:32]

        assert expected == PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY

    def test_should_replace_only_the_abstention_for_a_statement_only_message(
        self,
    ) -> None:
        # The real route adds a generation request next to the abstention.
        self._route((self._abstention(),))
        self._statement_receipt()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == [
            self._ACKNOWLEDGEMENT
        ]
        assert prepared.local_blocks[0].ordinal == 0
        assert prepared.local_blocks[0].intent is None
        assert prepared.attachment_request is None
        self.repositories.mentor_messages.find_memory_analysis.assert_called_once_with(
            'message'
        )
        self.route_provider.route.assert_called_once_with(
            self.message.content, self.context
        )

    @pytest.mark.parametrize('receipt', [None, False])
    def test_should_keep_the_abstention_without_a_statement_only_receipt(
        self, receipt: bool | None
    ) -> None:
        abstention = self._abstention()
        self._route((abstention,))
        if receipt is not None:
            self._statement_receipt(receipt)

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks == (abstention,)

    def test_should_acknowledge_when_only_a_generative_intent_matched(self) -> None:
        # The real route matches generative intents (for example explain_concept
        # for "Prefiro exemplos curtos em JavaScript.") that have no local block.
        self._route(
            (self._abstention(),),
            intents=(
                MentorIntentMatch(intent=MentorIntent.EXPLAIN_CONCEPT, similarity=0.6),
            ),
        )
        self._statement_receipt()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == [
            self._ACKNOWLEDGEMENT
        ]

    def test_should_keep_every_block_when_the_abstention_is_not_the_only_one(
        self,
    ) -> None:
        abstention = self._abstention()
        other = replace(self.block, ordinal=1)
        self._route((replace(self.block, ordinal=0), replace(abstention, ordinal=1)))
        self._statement_receipt()
        prepared = self.subject.execute('attempt', 'owner')
        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == [
            self.block.content,
            abstention.content,
        ]

        self._route((other,))
        prepared = self.subject.execute('attempt', 'owner')
        assert prepared is not None
        assert prepared.local_blocks == (other,)

    def test_should_keep_the_abstention_for_an_attachment_backed_request(
        self,
    ) -> None:
        abstention = self._abstention()
        self.repositories.mentor_messages.find_all.return_value = (
            replace(
                self.message,
                content='Prefiro respostas curtas. Resuma o documento.',
                attachments=(self._ready_attachment(),),
            ),
        )
        self._route((abstention,))
        self._statement_receipt()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks == (abstention,)
        assert prepared.attachment_request is not None

    def test_should_acknowledge_when_the_message_only_mentions_a_pending_file(
        self,
    ) -> None:
        pending = replace(
            self._ready_attachment(),
            attachment_id='pending',
            status=MentorAttachmentStatus.PROCESSING,
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(
                self.message,
                content='Prefiro respostas curtas no documento.',
                attachments=(pending,),
            ),
        )
        self._route((self._abstention(),))
        self._statement_receipt()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == [
            self._ACKNOWLEDGEMENT
        ]
        assert prepared.attachment_request is None

    def test_should_let_a_clarification_replace_the_acknowledgement(self) -> None:
        self._route((self._abstention(),), clarification='Qual Objetivo?')
        self._statement_receipt()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == ['Qual Objetivo?']

    def test_should_let_the_diagnostic_boundary_win_over_the_acknowledgement(
        self,
    ) -> None:
        self.context_provider.read.return_value = context_snapshot(
            diagnostic_in_progress=True
        )
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content='Prefiro dicas sobre a atividade.'),
        )
        self._route((self._abstention(),))
        self._statement_receipt()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.block_key for block in prepared.local_blocks] == [
            'diagnostic-boundary'
        ]

    def _remember(self, *memories: tuple[LearnerMemoryCategory, str, int]) -> None:
        self.repositories.learner_memories.find_many_by_account.return_value = tuple(
            LearnerMemoryFaker.fake(
                id=f'memory-{index}',
                account_id='account',
                category=category,
                content=content,
                updated_at=self.now + timedelta(minutes=minutes),
            )
            for index, (category, content, minutes) in enumerate(memories)
        )

    def _attachment_message(self) -> None:
        self.repositories.mentor_messages.find_all.return_value = (
            replace(
                self.message,
                content='Explique este trecho do documento sobre listas.',
                attachments=(self._ready_attachment(),),
            ),
        )
        self._route((self._abstention(),), requests=('Explicar o trecho.',))

    def test_should_pass_recent_preferences_and_relevant_memories_to_attachment_answers(
        self,
    ) -> None:
        preference = LearnerMemoryCategory.EXPLANATION_PREFERENCE
        knowledge = LearnerMemoryCategory.DECLARED_KNOWLEDGE
        difficulty = LearnerMemoryCategory.RECURRING_DIFFICULTY
        self._remember(
            (preference, 'Prefiro exemplos antigos.', 1),
            (preference, 'Prefiro respostas curtas.', 5),
            (preference, 'Prefiro exemplos em Python.', 4),
            (preference, 'Prefiro tom informal.', 3),
            (knowledge, 'Sei listas.', 2),
            (difficulty, 'Tenho dificuldade com ponteiros.', 6),
            (knowledge, 'Sei exatamente no limite.', 7),
        )
        scores = {
            'Prefiro exemplos antigos.': 0.1,
            'Sei listas.': 0.9,
            'Tenho dificuldade com ponteiros.': 0.29,
            'Sei exatamente no limite.': 0.3,
        }

        def score(_message: str, memory: str) -> float:
            return scores[memory]

        self.memory_similarity.similarity.side_effect = score
        self._attachment_message()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.memories == (
            LearnerMemoryContext(
                category=preference, content='Prefiro respostas curtas.'
            ),
            LearnerMemoryContext(
                category=preference, content='Prefiro exemplos em Python.'
            ),
            LearnerMemoryContext(category=preference, content='Prefiro tom informal.'),
            LearnerMemoryContext(category=knowledge, content='Sei listas.'),
            LearnerMemoryContext(
                category=knowledge, content='Sei exatamente no limite.'
            ),
        )
        contents = [
            call.args[1] for call in self.memory_similarity.similarity.call_args_list
        ]
        assert 'Prefiro respostas curtas.' not in contents

    def test_should_also_send_an_older_preference_that_is_relevant(self) -> None:
        preference = LearnerMemoryCategory.EXPLANATION_PREFERENCE
        knowledge = LearnerMemoryCategory.DECLARED_KNOWLEDGE
        self._remember(
            (preference, 'Prefiro listas com exemplos.', 1),
            (preference, 'Prefiro respostas curtas.', 5),
            (preference, 'Prefiro exemplos em Python.', 4),
            (preference, 'Prefiro tom informal.', 3),
            (knowledge, 'Sei violão.', 2),
        )
        scores = {
            'Prefiro listas com exemplos.': 0.3,
            'Sei violão.': 0.29,
        }

        def score(_message: str, memory: str) -> float:
            return scores[memory]

        self.memory_similarity.similarity.side_effect = score
        self._attachment_message()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert [item.content for item in prepared.attachment_request.memories] == [
            'Prefiro respostas curtas.',
            'Prefiro exemplos em Python.',
            'Prefiro tom informal.',
            'Prefiro listas com exemplos.',
        ]

    def test_should_limit_relevant_memories_to_five_by_similarity(self) -> None:
        knowledge = LearnerMemoryCategory.DECLARED_KNOWLEDGE
        self._remember(*((knowledge, f'Sei tema {n}.', n) for n in range(7)))

        def score(_message: str, memory: str) -> float:
            return 0.4 + int(memory.split()[2].rstrip('.')) / 100

        self.memory_similarity.similarity.side_effect = score
        self._attachment_message()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert [item.content for item in prepared.attachment_request.memories] == [
            f'Sei tema {n}.' for n in (6, 5, 4, 3, 2)
        ]

    def test_should_keep_attachment_inputs_without_memories(self) -> None:
        self._attachment_message()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.memories == ()
        self.memory_similarity.similarity.assert_not_called()

    def test_should_not_read_memories_for_local_answers(self) -> None:
        self._remember(
            (LearnerMemoryCategory.EXPLANATION_PREFERENCE, 'Prefiro curtas.', 1)
        )
        self._route((self.block,), requests=('Explicar a próxima etapa.',))

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks == (self.block,)
        assert prepared.attachment_request is None
        self.repositories.learner_memories.find_many_by_account.assert_not_called()
        self.memory_similarity.similarity.assert_not_called()

    def test_should_continue_without_memories_when_selection_fails(self) -> None:
        self._remember((LearnerMemoryCategory.DECLARED_KNOWLEDGE, 'Sei listas.', 1))
        self.memory_similarity.similarity.side_effect = RuntimeError('similarity')
        self._attachment_message()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.memories == ()


class TestPrepareMentorGeneration(_PrepareSubjectSetup):
    """A generated answer for unanswered parts: the decision and its exclusions."""

    _SLOT = ('account', 'attempt')

    def _abstention(self) -> MentorResponseBlock:
        return MentorResponseBlock(
            block_key=PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY,
            ordinal=0,
            intent=None,
            content='Ainda não encontrei uma resposta local confiável.',
        )

    def _attachment(
        self, status: MentorAttachmentStatus, attachment_id: str = 'file'
    ) -> MentorAttachmentView:
        return MentorAttachmentView(
            attachment_id=attachment_id,
            filename='material.pdf',
            media_type='application/pdf',
            size_bytes=20,
            status=status,
            failure_code=None,
            analyzed_pages=(1,),
            illegible_pages=(),
            uninterpreted_pages=(),
        )

    def _say(
        self, content: str, attachments: tuple[MentorAttachmentView, ...] = ()
    ) -> None:
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content, attachments=attachments),
        )

    def _route_unanswered(
        self,
        *parts: str,
        blocks: tuple[MentorResponseBlock, ...] | None = None,
        requests: tuple[str, ...] | None = None,
        clarification: str | None = None,
    ) -> None:
        self.route_provider.route.return_value = MentorRouteResult(
            intents=(),
            local_blocks=blocks if blocks is not None else (self._abstention(),),
            generation_requests=requests if requests is not None else parts,
            clarification=clarification,
            unanswered_requests=parts,
        )

    def _expect_abstention_kept(self, prepared: PreparedMentorResponse | None) -> None:
        assert prepared is not None
        assert prepared.attachment_request is None
        assert prepared.generation_fallback is None
        assert [block.block_key for block in prepared.local_blocks] == [
            PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY
        ]

    def test_should_build_a_general_request_and_defer_the_abstention(self) -> None:
        self._say('Olá')
        self._route_unanswered('Olá')
        self._remember_preference()

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        request = prepared.attachment_request
        assert request is not None
        assert request.attachment_context is None
        assert request.requested_part == 'Olá'
        assert request.attempt_id == 'attempt'
        assert request.correction is None
        assert [memory.content for memory in request.memories] == ['Prefiro curtas.']
        assert prepared.local_blocks == ()
        assert prepared.generation_fallback == self._abstention()
        self.generation_limit.try_acquire.assert_called_once_with(*self._SLOT)
        self.attachment_context_use_case.execute.assert_not_called()

    def test_should_keep_the_local_blocks_first_and_send_only_the_unanswered_parts(
        self,
    ) -> None:
        faq = replace(self.block, block_key='faq', ordinal=0)
        abstention = replace(self._abstention(), ordinal=1)
        self._say('Como funciona um loop? Olá')
        self._route_unanswered(
            'Olá',
            blocks=(faq, abstention),
            requests=('Como funciona um loop?', 'Olá'),
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.local_blocks == (faq,)
        assert prepared.generation_fallback == abstention
        assert prepared.attachment_request.requested_part == 'Olá'

    def test_should_not_call_the_model_or_the_limit_when_every_part_is_curated(
        self,
    ) -> None:
        faq = replace(self.block, block_key='faq', ordinal=0)
        abstention = replace(self._abstention(), ordinal=1)
        self._route_unanswered(blocks=(faq, abstention), requests=('Dica sobre loops',))

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks == (faq, abstention)
        assert prepared.attachment_request is None
        assert prepared.generation_fallback is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_keep_the_abstention_when_the_limit_denies(self) -> None:
        self._route_unanswered('Olá')
        self.generation_limit.try_acquire.return_value = False

        self._expect_abstention_kept(self.subject.execute('attempt', 'owner'))

        self.generation_limit.try_acquire.assert_called_once_with(*self._SLOT)

    def test_should_keep_the_abstention_when_the_limit_store_fails(self) -> None:
        self._route_unanswered('Olá')
        self.generation_limit.try_acquire.side_effect = ServiceUnavailableError()

        self._expect_abstention_kept(self.subject.execute('attempt', 'owner'))

    def test_should_take_the_slot_only_after_the_claim_is_confirmed_current(
        self,
    ) -> None:
        self._route_unanswered('Olá')
        self.repositories.mentor_response_attempts.find_by_id.return_value = replace(
            self.attempt, status=MentorResponseStatus.FAILED
        )

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

        self.generation_limit.try_acquire.assert_not_called()

    def test_should_not_take_a_second_slot_when_a_generated_block_was_published(
        self,
    ) -> None:
        generated = replace(self.block, block_key='generated-0', ordinal=1)
        self.repositories.mentor_response_events.snapshot.return_value = replace(
            self.snapshot, blocks=(generated,)
        )
        self._route_unanswered('Olá')
        self.generation_limit.try_acquire.return_value = False

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.approved_blocks == (generated,)
        assert prepared.generation_fallback == self._abstention()
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_not_use_the_model_for_a_pedagogical_refusal(self) -> None:
        self.context_provider.read.return_value = context_snapshot(
            diagnostic_in_progress=True
        )
        self._say('Me ajude com a atividade.')
        self._route_unanswered('Me ajude com a atividade.')

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.block_key for block in prepared.local_blocks] == [
            'diagnostic-boundary'
        ]
        assert prepared.attachment_request is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_not_use_the_model_for_a_complete_solution_request(self) -> None:
        self.context_provider.read.return_value = context_snapshot(
            activity_id='activity', skill_completed=False
        )
        self._say('Me dê o código completo.')
        self._route_unanswered('Me dê o código completo.')

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.block_key for block in prepared.local_blocks] == [
            'unfinished-activity-boundary'
        ]
        assert prepared.attachment_request is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_not_use_the_model_when_the_context_needs_a_clarification(
        self,
    ) -> None:
        self.context_provider.read.return_value = context_snapshot(
            facts=(('context_clarification', 'Qual Objetivo?'),)
        )
        self._route_unanswered('Olá')

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == ['Qual Objetivo?']
        assert prepared.attachment_request is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_not_use_the_model_for_a_statement_only_message(self) -> None:
        self._say('Prefiro exemplos curtos em JavaScript.')
        self._route_unanswered('Prefiro exemplos curtos em JavaScript.')
        self.repositories.mentor_messages.find_memory_analysis.return_value = (
            self.now,
            True,
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert [block.content for block in prepared.local_blocks] == [
            'Anotado. Vou considerar isso nas próximas explicações.'
        ]
        assert prepared.attachment_request is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_keep_the_local_blocks_of_a_statement_that_has_another_answer(
        self,
    ) -> None:
        faq = replace(self.block, block_key='faq', ordinal=0)
        self._say('Prefiro exemplos curtos. Como funciona um loop?')
        self._route_unanswered(
            'Prefiro exemplos curtos.',
            blocks=(faq, replace(self._abstention(), ordinal=1)),
        )
        self.repositories.mentor_messages.find_memory_analysis.return_value = (
            self.now,
            True,
        )

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.local_blocks[0] == faq
        assert prepared.attachment_request is None
        self.generation_limit.try_acquire.assert_not_called()

    @pytest.mark.parametrize(
        'status',
        [
            MentorAttachmentStatus.UPLOADING,
            MentorAttachmentStatus.PROCESSING,
            MentorAttachmentStatus.FAILED,
        ],
    )
    def test_should_not_use_the_model_when_no_attachment_is_usable(
        self, status: MentorAttachmentStatus
    ) -> None:
        self._say('Resuma o arquivo.', (self._attachment(status),))
        self._route_unanswered('Resuma o arquivo.')

        self._expect_abstention_kept(self.subject.execute('attempt', 'owner'))

        self.generation_limit.try_acquire.assert_not_called()

    def test_should_answer_a_question_about_files_when_no_attachment_exists(
        self,
    ) -> None:
        self._say('Como ler um arquivo em Python?')
        self._route_unanswered('Como ler um arquivo em Python?')

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.attachment_context is None
        self.generation_limit.try_acquire.assert_called_once_with(*self._SLOT)

    def test_should_answer_a_general_question_when_the_attachment_is_usable_but_unmentioned(
        self,
    ) -> None:
        self._say('Olá', (self._attachment(MentorAttachmentStatus.READY),))
        self._route_unanswered('Olá')

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.attachment_context is None
        self.generation_limit.try_acquire.assert_called_once_with(*self._SLOT)

    def test_should_not_take_a_slot_for_an_attachment_backed_request(self) -> None:
        self._say(
            'Explique este trecho do documento.',
            (self._attachment(MentorAttachmentStatus.READY),),
        )
        self._route_unanswered('Explique este trecho do documento.')

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        assert prepared.attachment_request.attachment_context == self.attachment_context
        assert prepared.generation_fallback is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_treat_a_pure_statement_without_a_receipt_as_a_question(
        self,
    ) -> None:
        self._say('Prefiro exemplos curtos em JavaScript.')
        self._route_unanswered('Prefiro exemplos curtos em JavaScript.')
        self.repositories.mentor_messages.find_memory_analysis.return_value = None

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None and prepared.attachment_request is not None
        self.generation_limit.try_acquire.assert_called_once_with(*self._SLOT)

    def test_should_not_build_a_request_without_an_abstention_to_fall_back_to(
        self,
    ) -> None:
        self._route_unanswered('Olá', blocks=(self.block,))

        prepared = self.subject.execute('attempt', 'owner')

        assert prepared is not None
        assert prepared.attachment_request is None
        assert prepared.local_blocks == (self.block,)
        self.generation_limit.try_acquire.assert_not_called()

    def _remember_preference(self) -> None:
        self.repositories.learner_memories.find_many_by_account.return_value = (
            LearnerMemoryFaker.fake(
                id='memory',
                account_id='account',
                category=LearnerMemoryCategory.EXPLANATION_PREFERENCE,
                content='Prefiro curtas.',
                updated_at=self.now,
            ),
        )


class _PrepareActionSetup(_PrepareSubjectSetup):
    """Helpers to script an add/remove request."""

    _ADD = 'Adicione Funções em Python ao meu Objetivo'

    def _skill(
        self,
        reference: str = 'skill',
        title: str = 'Funções em Python',
        description: str | None = 'Funções, parâmetros e retornos em Python.',
    ) -> MentorCatalogEntry:
        return MentorCatalogEntry(
            reference_id=reference,
            kind='skill',
            skill_id=reference,
            competency_id=None,
            title=title,
            description=description,
            concept_ids=(),
            source_version='v1',
        )

    def _goal(
        self,
        goal_id: str = 'goal',
        title: str = 'Aprender a programar',
        experience_id: str | None = None,
    ) -> MentorGoalDestination:
        return MentorGoalDestination(
            goal_id=goal_id, title=title, skill_experience_id=experience_id
        )

    def _request(
        self,
        content: str,
        *goals: MentorGoalDestination,
        intents: tuple[MentorIntent, ...] = (MentorIntent.ADD_SKILL,),
        skills: tuple[MentorCatalogEntry, ...] | None = None,
        blocks: tuple[MentorResponseBlock, ...] = (),
        **route_changes: object,
    ) -> None:
        self.repositories.mentor_messages.find_all.return_value = (
            replace(self.message, content=content),
        )
        self.catalog_provider.search.return_value = (
            skills if skills is not None else (self._skill(),)
        )
        self.goal_destinations.read.return_value = MentorGoalDestinations(goals=goals)
        route = MentorRouteResult(
            intents=tuple(
                MentorIntentMatch(intent=intent, similarity=0.9) for intent in intents
            ),
            local_blocks=blocks,
            generation_requests=(),
            clarification=None,
        )
        self.route_provider.route.return_value = replace(route, **route_changes)

    def _routed(self, *intents: MentorIntent) -> MentorRouteResult:
        return MentorRouteResult(
            intents=tuple(
                MentorIntentMatch(intent=intent, similarity=0.9) for intent in intents
            ),
            local_blocks=(),
            generation_requests=(),
            clarification=None,
        )

    def _hint_goal(self, goal_id: str) -> None:
        self.repositories.mentor_response_attempts.find_by_id_for_update.return_value = replace(
            self.attempt, context_hint=MentorContextHint(goal_id=goal_id)
        )

    def _prepare(self) -> PreparedMentorResponse:
        prepared = self.subject.execute('attempt', 'owner')
        assert prepared is not None
        return prepared

    def _expect_text_only(self, prepared: PreparedMentorResponse) -> str:
        assert prepared.action_proposal is None
        assert len(prepared.local_blocks) == 1
        assert prepared.local_blocks[0].intent is None
        return prepared.local_blocks[0].content


class TestPrepareMentorActions(_PrepareActionSetup):
    """RF-01 to RF-04: an explicit add/remove request becomes a proposal or a text."""

    def test_should_propose_the_addition_with_the_only_objective_fixed(self) -> None:
        self._request(self._ADD, self._goal())

        prepared = self._prepare()

        assert prepared.action_proposal == MentorActionProposalDraft(
            kind=MentorActionKind.ADD_SKILL,
            skill_id='skill',
            skill_name='Funções em Python',
            goal_id='goal',
            goal_title='Aprender a programar',
            skill_experience_id=None,
            candidate_goals=(),
            justification=(
                'Você pediu ao Mentor para adicionar esta Habilidade. '
                'Funções, parâmetros e retornos em Python.'
            ),
        )
        assert prepared.local_blocks == (
            MentorResponseBlock(
                block_key='action-proposal',
                ordinal=0,
                intent=MentorIntent.ADD_SKILL,
                content='Preparei uma proposta para você confirmar.',
            ),
        )
        assert prepared.attachment_request is None
        self.goal_destinations.read.assert_called_once_with('account', 'skill')
        self.route_provider.route.assert_called_once()
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_propose_a_named_skill_that_the_objective_does_not_have_yet(
        self,
    ) -> None:
        # Learning cannot open a Skill outside the Objective as context; the
        # request still becomes a proposal instead of failing the answer.
        self._request(self._ADD, self._goal())
        context = self.context_provider.read.return_value

        def read(
            _account_id: str, references: tuple[str, ...], **_hints: object
        ) -> object:
            if 'skill' in references:
                raise NotFoundError
            return context

        self.context_provider.read.side_effect = read

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert prepared.action_proposal.skill_id == 'skill'
        assert prepared.context == context

    def test_should_not_repeat_the_description_when_the_skill_has_none(self) -> None:
        self._request(self._ADD, self._goal(), skills=(self._skill(description=None),))

        draft = self._prepare().action_proposal

        assert draft is not None
        assert (
            draft.justification
            == 'Você pediu ao Mentor para adicionar esta Habilidade.'
        )

    def test_should_bound_the_justification_to_the_learning_limit(self) -> None:
        self._request(
            self._ADD, self._goal(), skills=(self._skill(description='x' * 5000),)
        )

        draft = self._prepare().action_proposal

        assert draft is not None and draft.justification is not None
        assert len(draft.justification) <= 2000
        assert draft.justification.startswith(
            'Você pediu ao Mentor para adicionar esta Habilidade. xxx'
        )

    def test_should_fix_the_objective_named_in_the_message(self) -> None:
        self._request(
            'Adicione Funções em Python ao Objetivo Dados e análise',
            self._goal('goal-a', 'Aprender a programar'),
            self._goal('goal-b', 'Dados e análise'),
        )

        draft = self._prepare().action_proposal

        assert draft is not None
        assert (draft.goal_id, draft.goal_title) == ('goal-b', 'Dados e análise')
        assert draft.candidate_goals == ()

    def test_should_prefer_the_longest_objective_title_that_matches(self) -> None:
        self._request(
            'Adicione Funções em Python ao Objetivo Python avançado',
            self._goal('goal-a', 'Python'),
            self._goal('goal-b', 'Python avançado'),
        )

        draft = self._prepare().action_proposal

        assert draft is not None and draft.goal_id == 'goal-b'

    def test_should_fix_the_objective_of_the_context_hint(self) -> None:
        self._request(self._ADD, self._goal('goal-a', 'A'), self._goal('goal-b', 'B'))
        self._hint_goal('goal-b')

        draft = self._prepare().action_proposal

        assert draft is not None
        assert (draft.goal_id, draft.goal_title) == ('goal-b', 'B')

    def test_should_ignore_a_hint_that_is_not_one_of_the_objectives(self) -> None:
        self._request(self._ADD, self._goal('goal-a', 'A'), self._goal('goal-b', 'B'))
        self._hint_goal('foreign')

        draft = self._prepare().action_proposal

        assert draft is not None and draft.goal_id is None
        assert [item.goal_id for item in draft.candidate_goals] == ['goal-a', 'goal-b']

    def test_should_let_a_named_objective_win_over_the_hint(self) -> None:
        self._request(
            'Adicione Funções em Python ao Objetivo A',
            self._goal('goal-a', 'A'),
            self._goal('goal-b', 'B'),
        )
        self._hint_goal('goal-b')

        draft = self._prepare().action_proposal

        assert draft is not None and draft.goal_id == 'goal-a'

    def test_should_offer_every_objective_and_flag_the_ones_that_hold_the_skill(
        self,
    ) -> None:
        self._request(
            self._ADD,
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-b', 'B'),
        )

        draft = self._prepare().action_proposal

        assert draft is not None
        assert (draft.goal_id, draft.goal_title) == (None, None)
        assert draft.candidate_goals == (
            MentorActionCandidateGoal(
                goal_id='goal-a',
                title='A',
                contains_skill=True,
                skill_experience_id='experience-a',
            ),
            MentorActionCandidateGoal(
                goal_id='goal-b',
                title='B',
                contains_skill=False,
                skill_experience_id=None,
            ),
        )

    def test_should_answer_with_a_shortcut_when_there_is_no_objective(self) -> None:
        self._request(self._ADD)

        text = self._expect_text_only(self._prepare())

        assert text == (
            'Ainda não encontrei Objetivos seus. O Mentor não cria Objetivos; '
            'você pode [criar um Objetivo](/learning/goals/new).'
        )

    def test_should_answer_with_a_shortcut_when_the_fixed_objective_holds_the_skill(
        self,
    ) -> None:
        self._request(
            self._ADD, self._goal('goal', 'Aprender a programar', 'experience')
        )

        text = self._expect_text_only(self._prepare())

        assert text == (
            'Funções em Python já está no Objetivo Aprender a programar. '
            '[Ver Habilidade](/learning/goals/goal/skills/skill).'
        )

    def test_should_escape_markdown_taken_from_titles(self) -> None:
        self._request(self._ADD, self._goal('goal', 'Meu [plano](/x)', 'experience'))

        text = self._expect_text_only(self._prepare())

        assert 'Objetivo Meu \\[plano\\]\\(/x\\). ' in text

    def test_should_answer_when_every_objective_already_holds_the_skill(self) -> None:
        self._request(
            self._ADD,
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-b', 'B', 'experience-b'),
        )

        text = self._expect_text_only(self._prepare())

        assert text == 'Funções em Python já está em todos os seus Objetivos.'

    def test_should_ask_which_skill_when_the_message_matches_several(self) -> None:
        self._request(
            'Adicione funções ao meu Objetivo',
            self._goal(),
            skills=(
                self._skill('skill-a', 'Funções em Python'),
                self._skill('skill-b', 'Funções em JavaScript'),
            ),
        )

        text = self._expect_text_only(self._prepare())

        assert text == (
            'Encontrei mais de uma Habilidade parecida: Funções em Python, '
            'Funções em JavaScript. Qual delas você quer?'
        )
        self.goal_destinations.read.assert_not_called()

    def test_should_say_the_skill_is_unknown_when_nothing_matches(self) -> None:
        self._request('Adicione Haskell ao meu Objetivo', self._goal(), skills=())

        text = self._expect_text_only(self._prepare())

        assert text == 'Não encontrei essa Habilidade no Currículo.'
        self.goal_destinations.read.assert_not_called()

    def test_should_ignore_catalog_entries_that_are_not_skills(self) -> None:
        competency = replace(self._skill('competency', 'Funções'), kind='competency')
        self._request(self._ADD, self._goal(), skills=(competency, self._skill()))

        draft = self._prepare().action_proposal

        assert draft is not None and draft.skill_id == 'skill'

    def test_should_resolve_the_skill_whose_title_occurs_in_the_message(self) -> None:
        self._request(
            self._ADD,
            self._goal(),
            skills=(
                self._skill('skill-a', 'Funções'),
                self._skill('skill-b', 'Funções em Python'),
                self._skill('skill-c', 'Variáveis em Python'),
            ),
        )

        draft = self._prepare().action_proposal

        assert draft is not None and draft.skill_id == 'skill-b'

    def test_should_propose_a_removal_for_the_only_objective_that_holds_the_skill(
        self,
    ) -> None:
        self._request(
            'Remova Funções em Python do meu Objetivo',
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-b', 'B'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )

        prepared = self._prepare()

        assert prepared.action_proposal == MentorActionProposalDraft(
            kind=MentorActionKind.REMOVE_SKILL,
            skill_id='skill',
            skill_name='Funções em Python',
            goal_id='goal-a',
            goal_title='A',
            skill_experience_id='experience-a',
            candidate_goals=(),
            justification=None,
        )
        assert prepared.local_blocks[0].intent is MentorIntent.REMOVE_SKILL
        assert (
            prepared.local_blocks[0].content
            == 'Preparei uma proposta para você confirmar.'
        )

    def test_should_offer_only_the_objectives_that_hold_the_skill_for_a_removal(
        self,
    ) -> None:
        self._request(
            'Remova Funções em Python do meu Objetivo',
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-b', 'B'),
            self._goal('goal-c', 'C', 'experience-c'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )

        draft = self._prepare().action_proposal

        assert draft is not None and draft.goal_id is None
        assert draft.candidate_goals == (
            MentorActionCandidateGoal(
                goal_id='goal-a',
                title='A',
                contains_skill=True,
                skill_experience_id='experience-a',
            ),
            MentorActionCandidateGoal(
                goal_id='goal-c',
                title='C',
                contains_skill=True,
                skill_experience_id='experience-c',
            ),
        )

    def test_should_fix_the_removal_with_the_named_objective(self) -> None:
        self._request(
            'Remova Funções em Python do Objetivo C',
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-c', 'C', 'experience-c'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )

        draft = self._prepare().action_proposal

        assert draft is not None
        assert (draft.goal_id, draft.skill_experience_id) == ('goal-c', 'experience-c')

    def test_should_not_remove_from_a_named_objective_that_lacks_the_skill(
        self,
    ) -> None:
        self._request(
            'Remova Funções em Python do Objetivo B',
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-b', 'B'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )

        text = self._expect_text_only(self._prepare())

        assert text == 'Funções em Python não está no Objetivo B.'

    def test_should_use_the_holders_when_the_hinted_objective_lacks_the_skill(
        self,
    ) -> None:
        self._request(
            'Remova Funções em Python do meu Objetivo',
            self._goal('goal-a', 'A', 'experience-a'),
            self._goal('goal-b', 'B'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )
        self._hint_goal('goal-b')

        draft = self._prepare().action_proposal

        assert draft is not None and draft.goal_id == 'goal-a'

    def test_should_not_propose_a_removal_for_a_skill_in_no_objective(self) -> None:
        self._request(
            'Remova Funções em Python do meu Objetivo',
            self._goal('goal-a', 'A'),
            self._goal('goal-b', 'B'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )

        text = self._expect_text_only(self._prepare())

        assert text == 'Funções em Python não está em nenhum dos seus Objetivos.'

    def test_should_not_propose_a_removal_without_objectives(self) -> None:
        self._request(
            'Remova Funções em Python do meu Objetivo',
            intents=(MentorIntent.REMOVE_SKILL,),
        )

        text = self._expect_text_only(self._prepare())

        assert text == 'Funções em Python não está em nenhum dos seus Objetivos.'

    def test_should_keep_one_proposal_and_ask_to_repeat_the_other_action(self) -> None:
        self._request(
            'Adicione Funções em Python ao meu Objetivo; '
            'remova Variáveis do meu Objetivo',
            self._goal(),
            intents=(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL),
        )
        self.route_provider.route.side_effect = [
            self._routed(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL),
            self._routed(MentorIntent.ADD_SKILL),
            self._routed(MentorIntent.REMOVE_SKILL),
        ]

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert prepared.action_proposal.kind is MentorActionKind.ADD_SKILL
        assert prepared.action_proposal.skill_id == 'skill'
        assert [block.block_key for block in prepared.local_blocks] == [
            'action-proposal',
            'action-repeat',
        ]
        assert [block.ordinal for block in prepared.local_blocks] == [0, 1]
        assert prepared.local_blocks[1].content == (
            'Para a outra ação, envie o pedido de novo depois de responder a esta proposta.'
        )
        assert prepared.local_blocks[1].intent is None
        self.goal_destinations.read.assert_called_once_with('account', 'skill')

    @pytest.mark.parametrize(
        'content',
        [
            'Adicione Funções em Python ao meu Objetivo e remova Variáveis do meu Objetivo',
            'Adicione Funções em Python ao meu Objetivo e também remova Variáveis do meu Objetivo',
        ],
    )
    def test_should_split_one_sentence_at_a_conjunction_before_a_second_action(
        self, content: str
    ) -> None:
        self._request(
            content,
            self._goal(),
            intents=(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL),
        )
        self.route_provider.route.side_effect = [
            self._routed(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL),
            self._routed(MentorIntent.ADD_SKILL),
            self._routed(MentorIntent.REMOVE_SKILL),
        ]

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert prepared.action_proposal.kind is MentorActionKind.ADD_SKILL
        assert [block.block_key for block in prepared.local_blocks] == [
            'action-proposal',
            'action-repeat',
        ]
        routed_parts = [
            call.args[0] for call in self.route_provider.route.call_args_list
        ]
        assert routed_parts[1] == 'Adicione Funções em Python ao meu Objetivo'
        assert routed_parts[2].startswith('remova Variáveis')
        queries = [call.args[1] for call in self.catalog_provider.search.call_args_list]
        assert queries[-1] == 'Adicione Funções em Python ao meu Objetivo'
        self.goal_destinations.read.assert_called_once_with('account', 'skill')

    def test_should_keep_the_question_mark_so_a_question_is_not_taken_as_the_request(
        self,
    ) -> None:
        question = 'Eu posso remover Funções em Python do Objetivo'
        request = 'Adicione React ao meu Objetivo'
        self._request(
            f'{question}? {request}',
            self._goal(),
            skills=(self._skill('skill-react', 'React'),),
        )

        def route(
            content: str, _context: object, *_topics: object
        ) -> MentorRouteResult:
            # Like the real provider, a part that ends in a question mark is vetoed.
            if content.endswith('?'):
                return self._routed()
            if content == request:
                return self._routed(MentorIntent.ADD_SKILL)
            return self._routed(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL)

        self.route_provider.route.side_effect = route

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert prepared.action_proposal.kind is MentorActionKind.ADD_SKILL
        assert prepared.action_proposal.skill_id == 'skill-react'
        assert [block.block_key for block in prepared.local_blocks] == [
            'action-proposal'
        ]
        routed = [call.args[0] for call in self.route_provider.route.call_args_list]
        assert f'{question}?' in routed
        assert request in routed
        queries = [call.args[1] for call in self.catalog_provider.search.call_args_list]
        assert queries[-1] == request

    def test_should_not_split_a_skill_title_that_contains_a_conjunction(self) -> None:
        self._request(
            'Adicione Entrada e saída ao meu Objetivo',
            self._goal(),
            skills=(self._skill('skill', 'Entrada e saída'),),
        )

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert [block.block_key for block in prepared.local_blocks] == [
            'action-proposal'
        ]
        self.route_provider.route.assert_called_once()

    def test_should_ask_to_repeat_a_second_request_of_the_same_kind(self) -> None:
        self._request(
            'Adicione Funções em Python ao meu Objetivo. Adicione Variáveis também',
            self._goal(),
        )

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert [block.block_key for block in prepared.local_blocks] == [
            'action-proposal',
            'action-repeat',
        ]

    def test_should_not_ask_to_repeat_when_the_first_action_has_no_proposal(
        self,
    ) -> None:
        self._request(
            'Adicione Haskell ao meu Objetivo; remova Variáveis',
            self._goal(),
            skills=(),
            intents=(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL),
        )
        self.route_provider.route.side_effect = [
            self._routed(MentorIntent.ADD_SKILL, MentorIntent.REMOVE_SKILL),
            self._routed(MentorIntent.ADD_SKILL),
            self._routed(MentorIntent.REMOVE_SKILL),
        ]

        text = self._expect_text_only(self._prepare())

        assert text == 'Não encontrei essa Habilidade no Currículo.'

    def test_should_resolve_the_skill_only_in_the_part_that_asks_for_the_action(
        self,
    ) -> None:
        self._request(
            'Qual é o meu progresso? Adicione Funções em Python ao meu Objetivo',
            self._goal(),
        )
        self.route_provider.route.side_effect = [
            self._routed(MentorIntent.ADD_SKILL),
            self._routed(),
            self._routed(MentorIntent.ADD_SKILL),
        ]

        draft = self._prepare().action_proposal

        assert draft is not None
        queries = [call.args[1] for call in self.catalog_provider.search.call_args_list]
        assert queries[-1] == 'Adicione Funções em Python ao meu Objetivo'

    def test_should_not_plan_an_action_without_an_action_intent(self) -> None:
        self._request(
            'Quero estudar Funções em Python',
            self._goal(),
            intents=(MentorIntent.SEARCH_CURRICULUM,),
            blocks=(self.block,),
        )

        prepared = self._prepare()

        assert prepared.action_proposal is None
        assert prepared.local_blocks == (self.block,)
        self.goal_destinations.read.assert_not_called()

    def test_should_not_plan_an_action_when_the_context_needs_a_clarification(
        self,
    ) -> None:
        self._request(self._ADD, self._goal(), clarification='Qual Objetivo?')

        prepared = self._prepare()

        assert prepared.action_proposal is None
        assert [block.content for block in prepared.local_blocks] == ['Qual Objetivo?']
        self.goal_destinations.read.assert_not_called()

    def test_should_drop_the_abstention_that_only_the_action_part_caused(self) -> None:
        abstention = MentorResponseBlock(
            block_key=PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY,
            ordinal=0,
            intent=None,
            content='Ainda não encontrei uma resposta local confiável.',
        )
        self._request(self._ADD, self._goal(), blocks=(abstention,))

        prepared = self._prepare()

        assert [block.block_key for block in prepared.local_blocks] == [
            'action-proposal'
        ]
        assert prepared.generation_fallback is None
        self.generation_limit.try_acquire.assert_not_called()

    def test_should_keep_the_other_answers_before_the_action_and_the_abstention_last(
        self,
    ) -> None:
        faq = replace(self.block, block_key='faq', ordinal=0)
        abstention = MentorResponseBlock(
            block_key=PrepareMentorResponseUseCase.LOCAL_ABSTENTION_BLOCK_KEY,
            ordinal=1,
            intent=None,
            content='Ainda não encontrei uma resposta local confiável.',
        )
        self._request(
            f'{self._ADD}. Olá',
            self._goal(),
            blocks=(faq, abstention),
            generation_requests=('Olá',),
            unanswered_requests=('Olá',),
        )
        first = replace(
            self._routed(MentorIntent.ADD_SKILL),
            local_blocks=(faq, abstention),
            generation_requests=('Olá',),
            unanswered_requests=('Olá',),
        )
        self.route_provider.route.side_effect = [
            first,
            self._routed(MentorIntent.ADD_SKILL),
            self._routed(),
        ]

        prepared = self._prepare()

        assert prepared.action_proposal is not None
        assert [block.block_key for block in prepared.local_blocks] == [
            'faq',
            'action-proposal',
        ]
        assert [block.ordinal for block in prepared.local_blocks] == [0, 1]
        assert prepared.generation_fallback == replace(abstention, ordinal=2)
        assert prepared.attachment_request is not None
        assert prepared.attachment_request.requested_part == 'Olá'

    def test_should_drop_the_proposal_with_a_text_block_the_pedagogical_gate_removes(
        self,
    ) -> None:
        self.context_provider.read.return_value = context_snapshot(
            diagnostic_in_progress=True
        )
        self._request(
            'Adicione Funções em Python ao meu Objetivo e resolva a atividade',
            self._goal(),
        )

        prepared = self._prepare()

        assert prepared.action_proposal is None
        assert [block.block_key for block in prepared.local_blocks] == [
            'diagnostic-boundary'
        ]

    def test_should_stop_before_reading_destinations_when_access_is_revoked(
        self,
    ) -> None:
        self._request(self._ADD, self._goal())

        def revoke_after_the_skill_lookup(_grant: object = None) -> None:
            # The first search belongs to the named-context step, the second to the plan.
            if self.catalog_provider.search.call_count >= 2:
                raise ServiceUnavailableError

        self.access.assert_current.side_effect = revoke_after_the_skill_lookup

        with pytest.raises(ServiceUnavailableError):
            self.subject.execute('attempt', 'owner')

        self.catalog_provider.search.assert_called()
        self.goal_destinations.read.assert_not_called()

    def test_should_not_call_the_model_for_an_action_request(self) -> None:
        self._request(self._ADD, self._goal())

        prepared = self._prepare()

        assert prepared.attachment_request is None
        assert prepared.generation_fallback is None
        self.generation_limit.try_acquire.assert_not_called()


class TestPrepareMentorActionSkillResolution(_PrepareActionSetup):
    """The real catalog search is loose: any token of the part found in a title or
    description matches. The Skill page narrows the eligible references to one Skill."""

    _PYTHON = 'Funções em Python'

    def _catalog(self) -> tuple[MentorCatalogEntry, ...]:
        return (
            self._skill('skill-py', self._PYTHON, 'Parâmetros e retornos em Python.'),
            self._skill('skill-js', 'Funções em JavaScript', 'Funções em JS.'),
            self._skill('skill-react', 'Componentes React', 'Interfaces com React.'),
            self._skill('skill-sql', 'Consultas SQL', 'Dados em tabelas.'),
        )

    def _use_real_like_search(self, *, page_skill: str | None = None) -> None:
        catalog = self._catalog()

        def search(
            _account_id: str, query: str, eligible: tuple[str, ...]
        ) -> tuple[MentorCatalogEntry, ...]:
            terms = tuple(query.casefold().split())
            return tuple(
                entry
                for entry in catalog
                if entry.reference_id in eligible
                and any(
                    term in f'{entry.title} {entry.description or ""}'.casefold()
                    for term in terms
                )
            )

        eligible = (
            (page_skill,) if page_skill else tuple(e.reference_id for e in catalog)
        )
        self.context_provider.read.return_value = context_snapshot(
            eligible_references=eligible
        )
        self.catalog_provider.search.side_effect = search

    def _ask(
        self, content: str, *, page_skill: str | None = None
    ) -> PreparedMentorResponse:
        self._request(
            content,
            self._goal('goal', 'A', 'experience'),
            intents=(MentorIntent.REMOVE_SKILL,),
        )
        self._use_real_like_search(page_skill=page_skill)
        return self._prepare()

    def test_should_accept_a_full_name_request_on_the_skill_page(self) -> None:
        prepared = self._ask(
            'Remova Funções em Python do meu Objetivo', page_skill='skill-py'
        )

        assert prepared.action_proposal is not None
        assert prepared.action_proposal.skill_id == 'skill-py'

    @pytest.mark.parametrize(
        'content',
        [
            'Remova a Habilidade de React do Objetivo atual',
            'Remova React em Python do meu Objetivo',
        ],
    )
    def test_should_not_propose_the_page_skill_when_the_message_names_another(
        self, content: str
    ) -> None:
        prepared = self._ask(content, page_skill='skill-py')

        assert self._expect_text_only(prepared) == (
            'Não encontrei essa Habilidade no Currículo.'
        )
        self.goal_destinations.read.assert_not_called()

    @pytest.mark.parametrize(
        'content',
        [
            'Remova funções de Python do meu Objetivo',
            'Remova python funções do meu Objetivo',
            'Remova Funções  Python do meu Objetivo',
        ],
    )
    def test_should_accept_a_word_order_or_inflection_tolerant_mention(
        self, content: str
    ) -> None:
        prepared = self._ask(content, page_skill='skill-py')

        assert prepared.action_proposal is not None
        assert prepared.action_proposal.skill_id == 'skill-py'

    def test_should_list_only_skills_that_share_a_word_with_the_message(self) -> None:
        prepared = self._ask('Remova funções do meu Objetivo')

        assert self._expect_text_only(prepared) == (
            'Encontrei mais de uma Habilidade parecida: Funções em Python, '
            'Funções em JavaScript. Qual delas você quer?'
        )

    def test_should_not_list_arbitrary_skills_when_none_is_related(self) -> None:
        prepared = self._ask('Remova a Habilidade de Haskell do meu Objetivo')

        assert self._expect_text_only(prepared) == (
            'Não encontrei essa Habilidade no Currículo.'
        )
