from dataclasses import replace
from datetime import timedelta

from unittest.mock import create_autospec

import pytest
from datetime import UTC, datetime

from shifu.fakers.intelligence.entities import LearnerMemoryFaker
from shifu.intelligence.core.domain.entities import MentorMessage, MentorSessionSummary
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    MentorSummaryExcerptKind,
    MentorAttachmentStatus,
    MentorIntent,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
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
from shifu.intelligence.core.interfaces import LearnerMemorySimilarityProvider
from shifu.intelligence.core.domain.structures.prepared_mentor_response import (
    PreparedMentorResponse,
)
from shifu.intelligence.core.use_cases.prepare_mentor_response_use_case import (
    PrepareMentorResponseUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
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
        self.repositories.mentor_messages.find_memory_analysis.return_value = None
        self.repositories.learner_memories.find_many_by_account.return_value = ()
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

    def test_should_keep_general_generation_local(self) -> None:
        approved = replace(self.block, block_key='approved', ordinal=0)
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

        assert prepared is not None
        assert prepared.local_blocks == (self.block,)
        assert prepared.attachment_request is None
        self.attachment_context_use_case.execute.assert_not_called()

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
