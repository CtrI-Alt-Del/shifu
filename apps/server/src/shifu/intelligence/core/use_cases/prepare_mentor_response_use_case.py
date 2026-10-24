import hashlib
import re
import unicodedata
from dataclasses import asdict, replace
from typing import ClassVar

from shifu.intelligence.core.domain.entities import (
    LearnerMemory,
    MentorMessage,
    MentorResponseAttempt,
)
from shifu.intelligence.core.domain.enums import (
    LearnerMemoryCategory,
    MentorAttachmentStatus,
    MentorIntent,
    MentorMessageRole,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    LearnerMemoryContext,
    MentorActionProposalDraft,
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
    LearnerMemorySimilarityProvider,
    MentorGenerationLimitProvider,
    MentorRouteProvider,
)
from shifu.intelligence.core.use_cases.get_mentor_attachment_context_use_case import (
    GetMentorAttachmentContextUseCase,
)
from shifu.intelligence.core.use_cases.mentor_action_planner import (
    MentorActionPlan,
    MentorActionPlanner,
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
    MentorGoalDestinationsProvider,
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

    # The route provider names its abstention block by this key; the policy only
    # recognizes it, so the provider stays unchanged (RF-07).
    LOCAL_ABSTENTION_BLOCK_KEY: ClassVar[str] = hashlib.sha256(
        b'local-abstention'
    ).hexdigest()[:32]
    MEMORY_ACKNOWLEDGEMENT_BLOCK_KEY: ClassVar[str] = 'memory-acknowledged'
    MEMORY_ACKNOWLEDGEMENT: ClassVar[str] = (
        'Anotado. Vou considerar isso nas próximas explicações.'
    )
    MAX_PREFERENCE_MEMORIES: ClassVar[int] = 3
    MAX_RELEVANT_MEMORIES: ClassVar[int] = 5

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        context_provider: MentorContextProvider,
        route_provider: MentorRouteProvider,
        catalog_provider: MentorCatalogProvider,
        attachment_context_use_case: GetMentorAttachmentContextUseCase,
        memory_similarity: LearnerMemorySimilarityProvider,
        memory_relevance_threshold: float,
        generation_limit_provider: MentorGenerationLimitProvider,
        goal_destinations_provider: MentorGoalDestinationsProvider,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider
        self._context_provider = context_provider
        self._route_provider = route_provider
        self._catalog_provider = catalog_provider
        self._attachment_context_use_case = attachment_context_use_case
        self._memory_similarity = memory_similarity
        self._memory_relevance_threshold = memory_relevance_threshold
        self._generation_limit = generation_limit_provider
        self._action_planner = MentorActionPlanner(
            catalog_provider, goal_destinations_provider, route_provider
        )

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
            analysis = repositories.mentor_messages.find_memory_analysis(
                attempt.learner_message_id
            )
        statement_only = analysis is not None and analysis[1] is True
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
        action = self._plan_action(attempt, learner.content, context, hints, route)
        if action is not None:
            route = self._with_action(route, action)
        if statement_only and not self._attachment_ids(
            learner, route.generation_requests
        ):
            route = self._acknowledge_statement(route)
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
        action_proposal = self._retained_draft(action, local_blocks)
        attachment_context = self._attachment_context(
            learner,
            requests,
            attempt.account_id,
            attempt.session_id,
        )
        request = None
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
                memories=self._relevant_memories(attempt.account_id, learner),
            )
        self._assert_claim_current(attempt, execution_owner)
        fallback = None
        unanswered = tuple(
            part for part in route.unanswered_requests if part in requests
        )
        if (
            request is None
            and self._may_generate(unanswered, statement_only, learner, local_blocks)
            and self._take_slot(attempt, approved)
        ):
            request = MentorGenerationRequest(
                session_id=attempt.session_id,
                learner_message_id=attempt.learner_message_id,
                attempt_id=attempt.id,
                requested_part='\n\n'.join(unanswered),
                history=tuple(history),
                context=context,
                approved_blocks=approved,
                correction=None,
                attachment_context=None,
                summary=summary,
                memories=self._relevant_memories(attempt.account_id, learner),
            )
            fallback = next(
                block
                for block in local_blocks
                if block.block_key == self.LOCAL_ABSTENTION_BLOCK_KEY
            )
            local_blocks = tuple(
                block for block in local_blocks if block is not fallback
            )
        return PreparedMentorResponse(
            attempt_id=attempt.id,
            execution_owner=execution_owner,
            account_id=attempt.account_id,
            session_id=attempt.session_id,
            learner_message_id=attempt.learner_message_id,
            context=context,
            local_blocks=local_blocks,
            attachment_request=request,
            generation_fallback=fallback,
            action_proposal=action_proposal,
        )

    def _plan_action(
        self,
        attempt: MentorResponseAttempt,
        content: str,
        context: MentorContextSnapshot,
        hints: dict[str, str | None],
        route: MentorRouteResult,
    ) -> MentorActionPlan | None:
        """RF-01 to RF-04: an explicit add/remove request becomes a proposal or a text."""
        if route.clarification is not None:
            return None
        return self._action_planner.plan(
            attempt.account_id,
            content,
            context,
            hints.get('goal_id'),
            route,
            lambda: assert_response_access(self._access_provider, attempt),
        )

    def _with_action(
        self, route: MentorRouteResult, action: MentorActionPlan
    ) -> MentorRouteResult:
        """Add the action answer; the abstention stays last as the generation fallback."""
        keep_abstention = bool(route.generation_requests)
        others = tuple(
            block
            for block in route.local_blocks
            if block.block_key != self.LOCAL_ABSTENTION_BLOCK_KEY
        )
        abstention = (
            tuple(
                block
                for block in route.local_blocks
                if block.block_key == self.LOCAL_ABSTENTION_BLOCK_KEY
            )
            if keep_abstention
            else ()
        )
        return replace(
            route,
            local_blocks=tuple(
                replace(block, ordinal=ordinal)
                for ordinal, block in enumerate((*others, *action.blocks, *abstention))
            ),
        )

    @staticmethod
    def _retained_draft(
        action: MentorActionPlan | None, blocks: tuple[MentorResponseBlock, ...]
    ) -> MentorActionProposalDraft | None:
        """The draft survives only while its proposal text block is still published."""
        if action is None or action.draft is None:
            return None
        intent = MentorIntent(action.draft.kind.value)
        return action.draft if any(block.intent is intent for block in blocks) else None

    def _may_generate(
        self,
        unanswered: tuple[str, ...],
        statement_only: bool,
        learner: MentorMessage,
        local_blocks: tuple[MentorResponseBlock, ...],
    ) -> bool:
        """A general answer needs an unanswered part and none of the RF-06 exclusions.

        The abstention must be among the local blocks: it is the safe fallback.
        """
        usable = (MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL)
        return (
            bool(unanswered)
            and not statement_only
            and (
                not learner.attachments
                or any(
                    attachment.status in usable for attachment in learner.attachments
                )
            )
            and any(
                block.block_key == self.LOCAL_ABSTENTION_BLOCK_KEY
                for block in local_blocks
            )
        )

    def _take_slot(
        self, attempt: MentorResponseAttempt, approved: tuple[MentorResponseBlock, ...]
    ) -> bool:
        """Take the attempt's slot once; a denial or a store failure keeps the abstention."""
        if any(block.block_key.startswith('generated-') for block in approved):
            return True
        try:
            return self._generation_limit.try_acquire(attempt.account_id, attempt.id)
        except ServiceUnavailableError:
            return False

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
        attachment_ids = self._attachment_ids(learner, requests)
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
    def _attachment_ids(
        cls, learner: MentorMessage, requests: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Ready attachments an attachment-backed request would read (else empty)."""
        if not requests or not cls._asks_about_attachments(learner.content):
            return ()
        return tuple(
            attachment.attachment_id
            for attachment in learner.attachments
            if attachment.status
            in (MentorAttachmentStatus.READY, MentorAttachmentStatus.PARTIAL)
        )

    @classmethod
    def _acknowledge_statement(cls, route: MentorRouteResult) -> MentorRouteResult:
        """RF-07: a statement-only message gets "Anotado" instead of the abstention."""
        if (
            route.clarification is not None
            or len(route.local_blocks) != 1
            or route.local_blocks[0].block_key != cls.LOCAL_ABSTENTION_BLOCK_KEY
        ):
            return route
        return replace(
            route,
            local_blocks=(
                MentorResponseBlock(
                    block_key=cls.MEMORY_ACKNOWLEDGEMENT_BLOCK_KEY,
                    ordinal=route.local_blocks[0].ordinal,
                    intent=None,
                    content=cls.MEMORY_ACKNOWLEDGEMENT,
                ),
            ),
        )

    def _relevant_memories(
        self, account_id: str, learner: MentorMessage
    ) -> tuple[LearnerMemoryContext, ...]:
        """Up to three recent preferences plus up to five memories relevant to the message.

        Memory selection only enriches a generated answer, so any failure here
        leaves the request without memories instead of failing the answer.
        """
        try:
            with self._database.transaction() as repositories:
                memories = repositories.learner_memories.find_many_by_account(
                    account_id
                )
            preferences = self._most_recent(
                tuple(
                    memory
                    for memory in memories
                    if memory.category is LearnerMemoryCategory.EXPLANATION_PREFERENCE
                )
            )[: self.MAX_PREFERENCE_MEMORIES]
            chosen = {memory.id for memory in preferences}
            scored = [
                (
                    self._memory_similarity.similarity(learner.content, memory.content),
                    memory,
                )
                for memory in memories
                if memory.id not in chosen
            ]
            relevant = [
                (score, memory)
                for score, memory in self._most_recent_scored(scored)
                if score >= self._memory_relevance_threshold
            ]
            relevant.sort(key=lambda item: item[0], reverse=True)
        except Exception:  # noqa: BLE001 - memories never fail an attachment answer.
            return ()
        return tuple(
            LearnerMemoryContext(category=memory.category, content=memory.content)
            for memory in (
                *preferences,
                *(memory for _, memory in relevant[: self.MAX_RELEVANT_MEMORIES]),
            )
        )

    @staticmethod
    def _most_recent(memories: tuple[LearnerMemory, ...]) -> tuple[LearnerMemory, ...]:
        by_id = sorted(memories, key=lambda memory: memory.id)
        return tuple(sorted(by_id, key=lambda memory: memory.updated_at, reverse=True))

    @staticmethod
    def _most_recent_scored(
        scored: list[tuple[float, LearnerMemory]],
    ) -> list[tuple[float, LearnerMemory]]:
        by_id = sorted(scored, key=lambda item: item[1].id)
        return sorted(by_id, key=lambda item: item[1].updated_at, reverse=True)

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
            return replace(
                route,
                clarification=clarification,
                generation_requests=(),
                unanswered_requests=(),
            )
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
