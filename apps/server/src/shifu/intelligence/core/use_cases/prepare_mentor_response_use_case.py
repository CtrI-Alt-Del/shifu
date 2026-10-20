import re
import unicodedata
from dataclasses import asdict, replace

from shifu.intelligence.core.domain.entities import MentorMessage, MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorIntent,
    MentorMessageRole,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentContext,
    MentorConversationSummaryContext,
    MentorGenerationRequest,
    MentorResponseBlock,
    MentorRouteResult,
    PreparedMentorResponse,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorRouteProvider,
)
from shifu.intelligence.core.use_cases.get_mentor_attachment_context_use_case import (
    GetMentorAttachmentContextUseCase,
)
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
    start_response_attempt,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.interfaces import (
    ClockProvider,
    MentorAccessProvider,
    MentorCatalogProvider,
    MentorContextProvider,
)


class PrepareMentorResponseUseCase:
    """Claim a response and prepare its authorized local/AI generation inputs."""

    _ATTACHMENT_TERMS = (
        'anexo',
        'arquivo',
        'documento',
        'pdf',
        'imagem',
        'foto',
        'página',
        'pagina',
    )

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        context_provider: MentorContextProvider,
        route_provider: MentorRouteProvider,
        catalog_provider: MentorCatalogProvider,
        attachment_context_use_case: GetMentorAttachmentContextUseCase,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider
        self._context_provider = context_provider
        self._route_provider = route_provider
        self._catalog_provider = catalog_provider
        self._attachment_context_use_case = attachment_context_use_case

    def execute(
        self, attempt_id: str, execution_owner: str
    ) -> PreparedMentorResponse | None:
        attempt = self._start(attempt_id, execution_owner)
        if attempt is None:
            return None
        assert_response_access(self._access_provider, attempt)
        with self._database.transaction() as repositories:
            ready = repositories.mentor_session_summaries.find_ready(
                attempt.account_id, attempt.session_id
            )
            if ready is None:
                history = repositories.mentor_messages.find_all(
                    attempt.account_id, attempt.session_id
                )
                summary = None
            else:
                history = repositories.mentor_messages.find_range(
                    attempt.account_id, attempt.session_id, ready.boundary
                )
                try:
                    summary = MentorConversationSummaryContext.from_summary(
                        ready,
                        repositories.mentor_messages.find_by_ids(
                            attempt.account_id,
                            attempt.session_id,
                            tuple(
                                dict.fromkeys(
                                    span.message_id for span in ready.excerpts
                                )
                            ),
                        ),
                    )
                except ValueError as error:
                    raise ServiceUnavailableError from error
            snapshot = repositories.mentor_response_events.snapshot(
                attempt.account_id, attempt.session_id
            )
            continuity = repositories.mentor_response_attempts.find_continuity(
                attempt.account_id, attempt.session_id
            )
        learner = next(
            (
                message
                for message in history
                if message.id == attempt.learner_message_id
                and message.role is MentorMessageRole.LEARNER
            ),
            None,
        )
        if learner is None:
            raise ServiceUnavailableError

        hints = asdict(attempt.context_hint) if attempt.context_hint else {}
        explicit = tuple(
            dict.fromkeys(
                re.findall(r'\b[0-7][0-9A-HJKMNP-TV-Z]{25}\b', learner.content)
            )
        )
        references, ordinal_clarification = self._continuity_references(
            learner.content, explicit, continuity
        )
        context = self._context_provider.read(attempt.account_id, references, **hints)
        context, named_clarification = self._resolve_named_context(
            attempt, learner.content, context, hints
        )
        with self._database.transaction() as repositories:
            self._assert_claim(repositories, attempt, execution_owner)
            assert_response_access(self._access_provider, attempt)
            if not repositories.mentor_response_attempts.update_references(
                attempt.id, context.resolved_references, attempt.access_revision
            ):
                raise ServiceUnavailableError
        assert_response_access(self._access_provider, attempt)
        clarification = (
            self._revalidate_proposal(references, continuity, context)
            or ordinal_clarification
            or named_clarification
        )
        route = self._route(
            learner.content,
            context,
            clarification,
            summary.topics if summary is not None else (),
        )
        route = self._propose_catalog(
            attempt, learner.content, context, route, execution_owner
        )
        route = replace(
            route, local_blocks=self._clarify(route.local_blocks, route.clarification)
        )
        local_blocks, requests = self._pedagogical_gate(
            learner.content, context, route.local_blocks, route.generation_requests
        )
        approved = (
            tuple(snapshot.blocks)
            if snapshot is not None and snapshot.attempt_id == attempt.id
            else ()
        )
        attachment_context = self._attachment_context(
            learner,
            requests,
            attempt.account_id,
            attempt.session_id,
        )
        request = None
        # General responses stay on the local route. Only attachment-backed
        # requests cross the inference boundary into the registered workflow.
        if requests and attachment_context is not None:
            request = MentorGenerationRequest(
                session_id=attempt.session_id,
                learner_message_id=attempt.learner_message_id,
                attempt_id=attempt.id,
                requested_part='\n\n'.join(requests),
                history=tuple(history),
                context=context,
                approved_blocks=approved,
                correction=None,
                attachment_context=attachment_context,
                summary=summary,
            )
        self._assert_claim_current(attempt, execution_owner)
        return PreparedMentorResponse(
            attempt_id=attempt.id,
            execution_owner=execution_owner,
            account_id=attempt.account_id,
            session_id=attempt.session_id,
            learner_message_id=attempt.learner_message_id,
            context=context,
            local_blocks=local_blocks,
            attachment_request=request,
        )

    def _start(
        self, attempt_id: str, execution_owner: str
    ) -> MentorResponseAttempt | None:
        return start_response_attempt(
            self._database,
            self._clock_provider,
            self._access_provider,
            attempt_id,
            execution_owner,
        )

    def _assert_claim(
        self,
        repositories: IntelligenceDatabaseRepositories,
        attempt: MentorResponseAttempt,
        execution_owner: str,
    ) -> None:
        if not repositories.mentor_response_attempts.has_claim(
            attempt.id, execution_owner, self._clock_provider.now()
        ):
            raise ServiceUnavailableError

    def _assert_claim_current(
        self, attempt: MentorResponseAttempt, execution_owner: str
    ) -> None:
        with self._database.transaction() as repositories:
            current = repositories.mentor_response_attempts.find_by_id(attempt.id)
            latest = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if (
                current is None
                or current.status is not MentorResponseStatus.PROCESSING
                or latest is None
                or latest.id != attempt.id
            ):
                raise ServiceUnavailableError
            self._assert_claim(repositories, attempt, execution_owner)
            assert_response_access(self._access_provider, attempt)

    def _attachment_context(
        self,
        learner: MentorMessage,
        requests: tuple[str, ...],
        account_id: str,
        session_id: str,
    ) -> MentorAttachmentContext | None:
        if not requests or not self._asks_about_attachments(learner.content):
            return None
        attachment_ids = tuple(
            attachment.attachment_id
            for attachment in learner.attachments
            if attachment.status
            in (MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL)
        )
        if not attachment_ids:
            return None
        pages = tuple(
            dict.fromkeys(
                int(value)
                for value in re.findall(
                    r'\bp(?:á|a)ginas?\s+(\d+)\b', learner.content.casefold()
                )
            )
        )
        return self._attachment_context_use_case.execute(
            account_id=account_id,
            session_id=session_id,
            attachment_ids=attachment_ids,
            page_numbers=pages,
        )

    @classmethod
    def _asks_about_attachments(cls, content: str) -> bool:
        lowered = content.casefold()
        return any(term in lowered for term in cls._ATTACHMENT_TERMS)

    @staticmethod
    def _continuity_references(
        content: str, explicit: tuple[str, ...], continuity: tuple[str, ...]
    ) -> tuple[tuple[str, ...], str | None]:
        if explicit:
            return explicit, None
        proposed = tuple(
            value.removeprefix('proposal:')
            for value in continuity
            if value.startswith('proposal:')
        )
        words = set(re.findall(r'\w+', content.casefold()))
        ordinals = words.intersection(
            (
                'primeiro',
                'primeira',
                'segundo',
                'segunda',
                'último',
                'última',
                'ultimo',
                'ultima',
            )
        )
        if not ordinals:
            return tuple(
                value for value in continuity if not value.startswith('proposal:')
            ), None
        indexes = {
            0
            if word.startswith('primeir')
            else 1
            if word.startswith('segund')
            else len(proposed) - 1
            for word in ordinals
        }
        if (
            len(indexes) != 1
            or not proposed
            or not 0 <= next(iter(indexes)) < len(proposed)
        ):
            return (
                (),
                'Qual item da lista você quer consultar? Informe o nome completo.',
            )
        return (proposed[next(iter(indexes))],), None

    @staticmethod
    def _revalidate_proposal(
        references: tuple[str, ...],
        continuity: tuple[str, ...],
        context: MentorContextSnapshot,
    ) -> str | None:
        selected = set(references).intersection(
            value.removeprefix('proposal:')
            for value in continuity
            if value.startswith('proposal:')
        )
        if selected and not selected.issubset(
            set(context.eligible_references) | set(context.resolved_references)
        ):
            return 'Esse item não está disponível no seu contexto atual. Qual item você quer consultar?'
        return None

    def _resolve_named_context(
        self,
        attempt: MentorResponseAttempt,
        content: str,
        context: MentorContextSnapshot,
        hints: dict[str, str | None],
    ) -> tuple[MentorContextSnapshot, str | None]:
        goals = self._named_goals(content, context)
        if len(goals) > 1:
            return (
                context,
                'Encontrei mais de um Objetivo com esse nome. Qual Objetivo você quer consultar?',
            )
        if goals:
            assert_response_access(self._access_provider, attempt)
            context = self._context_provider.read(attempt.account_id, goals, **hints)
        matches = self._catalog_provider.search(
            attempt.account_id, content, context.eligible_references
        )
        explicit = tuple(
            entry.reference_id
            for entry in matches
            if self._contains_title(content, entry.title)
        )
        if explicit:
            assert_response_access(self._access_provider, attempt)
            context = self._context_provider.read(
                attempt.account_id, (*goals, *explicit), **hints
            )
        return context, None

    @classmethod
    def _named_goals(
        cls, content: str, context: MentorContextSnapshot
    ) -> tuple[str, ...]:
        values: list[str] = []
        for key, value in context.facts:
            if key != 'goals' or ': ' not in value:
                continue
            reference, title = value.split(': ', 1)
            if re.fullmatch(
                r'[0-7][0-9A-HJKMNP-TV-Z]{25}', reference
            ) and cls._contains_title(content, title):
                values.append(reference)
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _contains_title(content: str, title: str) -> bool:
        def normalize(value: str) -> str:
            decomposed = unicodedata.normalize('NFKD', value.casefold())
            return ' '.join(
                ''.join(
                    char for char in decomposed if not unicodedata.combining(char)
                ).split()
            )

        normalized_title = normalize(title)
        return bool(
            normalized_title
            and re.search(
                r'(?<!\w)' + re.escape(normalized_title) + r'(?!\w)',
                normalize(content),
            )
        )

    def _route(
        self,
        content: str,
        context: MentorContextSnapshot,
        clarification: str | None,
        topics: tuple[str, ...],
    ) -> MentorRouteResult:
        if not content.strip():
            return MentorRouteResult(
                intents=(),
                local_blocks=(),
                generation_requests=(),
                clarification='Como posso ajudar com os anexos?',
            )
        clarification = next(
            (value for key, value in context.facts if key == 'context_clarification'),
            clarification,
        )
        route = (
            self._route_provider.route(content, context, topics)
            if topics
            else self._route_provider.route(content, context)
        )
        if clarification is not None:
            return replace(route, clarification=clarification, generation_requests=())
        return route

    def _propose_catalog(
        self,
        attempt: MentorResponseAttempt,
        content: str,
        context: MentorContextSnapshot,
        route: MentorRouteResult,
        execution_owner: str,
    ) -> MentorRouteResult:
        del content
        if route.clarification or not any(
            block.intent is MentorIntent.SEARCH_CURRICULUM
            for block in route.local_blocks
        ):
            return route
        projection = self._catalog_provider.read_projection()
        by_reference = {entry.reference_id: entry for entry in projection}
        entries = tuple(
            by_reference[reference]
            for reference in route.proposed_reference_ids
            if reference in by_reference and reference in context.eligible_references
        )
        if not entries:
            return route
        entries = tuple({entry.reference_id: entry for entry in entries}.values())
        references = tuple(entry.reference_id for entry in entries)
        with self._database.transaction() as repositories:
            self._assert_claim(repositories, attempt, execution_owner)
            assert_response_access(self._access_provider, attempt)
            if not repositories.mentor_response_attempts.update_references(
                attempt.id,
                (
                    *context.resolved_references,
                    *(f'proposal:{reference}' for reference in references),
                ),
                attempt.access_revision,
            ):
                raise ServiceUnavailableError
        text = '\n'.join(
            f'{index + 1}. {entry.title}' for index, entry in enumerate(entries)
        )
        return replace(
            route,
            local_blocks=tuple(
                replace(block, content=text)
                if block.intent is MentorIntent.SEARCH_CURRICULUM
                else block
                for block in route.local_blocks
            ),
        )

    @staticmethod
    def _pedagogical_gate(
        content: str,
        context: MentorContextSnapshot,
        blocks: tuple[MentorResponseBlock, ...],
        requests: tuple[str, ...],
    ) -> tuple[tuple[MentorResponseBlock, ...], tuple[str, ...]]:
        lowered = content.casefold()
        targets_activity = any(
            term in lowered
            for term in (
                'atividade',
                'exercício',
                'exercicio',
                'resposta',
                'solução',
                'solucao',
            )
        ) or (context.activity_id is not None and context.activity_id in content)
        if context.diagnostic_in_progress and targets_activity:
            independent = tuple(
                block
                for block in blocks
                if block.intent
                in (
                    MentorIntent.CONSULT_PROGRESS,
                    MentorIntent.CONSULT_GAMIFICATION,
                    MentorIntent.SEARCH_CURRICULUM,
                )
            )
            independent = tuple(
                replace(block, ordinal=index) for index, block in enumerate(independent)
            )
            refusal = MentorResponseBlock(
                block_key='diagnostic-boundary',
                ordinal=len(independent),
                intent=None,
                content='Não posso ajudar com a Atividade diagnóstica em andamento. Posso ajudar com outros assuntos de aprendizagem.',
            )
            return (*independent, refusal), ()
        complete_solution = any(
            term in lowered
            for term in (
                'solução completa',
                'resposta pronta',
                'código completo',
                'resposta final',
                'resolva',
            )
        )
        if (
            context.activity_id is not None
            and context.skill_completed is not True
            and complete_solution
        ):
            independent = tuple(
                block
                for block in blocks
                if block.intent
                in (
                    MentorIntent.CONSULT_PROGRESS,
                    MentorIntent.CONSULT_GAMIFICATION,
                    MentorIntent.SEARCH_CURRICULUM,
                )
            )
            refusal = MentorResponseBlock(
                block_key='unfinished-activity-boundary',
                ordinal=len(independent),
                intent=None,
                content=(
                    'Posso oferecer uma dica, mas não uma solução completa antes '
                    'de você concluir a Habilidade.'
                ),
            )
            return (*independent, refusal), ()
        return blocks, requests

    @staticmethod
    def _clarify(
        blocks: tuple[MentorResponseBlock, ...], clarification: str | None
    ) -> tuple[MentorResponseBlock, ...]:
        if clarification is None:
            return blocks
        return (
            MentorResponseBlock(
                block_key='clarification',
                ordinal=0,
                intent=None,
                content=clarification,
            ),
        )
