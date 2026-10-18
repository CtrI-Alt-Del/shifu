from dataclasses import replace
from datetime import timedelta

import pytest
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorIntent,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentView,
    MentorRouteResult,
)
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


class TestPrepareMentorResponseUseCase(MentorResponsePhaseTestSetup):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.prepare_phase(MentorResponseStatus.QUEUED)
        self.subject = PrepareMentorResponseUseCase(
            self.database,
            self.clock,
            self.access,
            self.context_provider,
            self.route_provider,
            self.catalog_provider,
            self.attachment_context_use_case,
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
