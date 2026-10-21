from collections.abc import Generator, Callable
from contextlib import contextmanager, suppress
from contextvars import ContextVar, copy_context
from math import isfinite
from threading import Event, Thread
from shifu.intelligence.core.interfaces import MentorTelemetryProvider
from dataclasses import asdict, replace
import re
import unicodedata
from datetime import timedelta

from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorResponseStatus,
    MentorResponseEventKind,
    MentorIntent,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseEvent,
    MentorResponseBlock,
    MentorGenerationRequest,
    MentorRouteResult,
    MentorInferenceUsage,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
    MentorRouteProvider,
    AnswerMentorMessageWorkflow,
)
from shifu.intelligence.core.use_cases.finalize_mentor_response_use_case import (
    FinalizeMentorResponseUseCase,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import (
    MentorAccessGrant,
    MentorContextSnapshot,
    MentorUsage,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
    MentorContextProvider,
    MentorCatalogProvider,
)


class ProcessMentorResponseUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        context_provider: MentorContextProvider,
        route_provider: MentorRouteProvider,
        answer_workflow: AnswerMentorMessageWorkflow,
        catalog_provider: MentorCatalogProvider,
        telemetry: MentorTelemetryProvider | None = None,
    ) -> None:
        self._telemetry: MentorTelemetryProvider | None = telemetry
        self._execution_owner_context: ContextVar[str | None] = ContextVar(
            'mentor_execution_owner', default=None
        )
        self._catalog_provider: MentorCatalogProvider = catalog_provider
        self._database: IntelligenceDatabase = database
        self._identifier_provider: IdentifierProvider = identifier_provider
        self._clock_provider: ClockProvider = clock_provider
        self._access_provider: MentorAccessProvider = access_provider
        self._context_provider: MentorContextProvider = context_provider
        self._route_provider: MentorRouteProvider = route_provider
        self._answer_workflow: AnswerMentorMessageWorkflow = answer_workflow

    @property
    def _execution_owner(self) -> str | None:
        return self._execution_owner_context.get()

    def execute(self, attempt_id: str) -> MentorResponseStatus:
        with self._database.transaction() as repositories:
            found = repositories.mentor_response_attempts.find_by_id(attempt_id)
        if found is None:
            return MentorResponseStatus.CANCELLED
        owner = self._identifier_provider.generate()
        token = self._execution_owner_context.set(owner)
        try:
            attempt = self._start(attempt_id)
            if attempt is None:
                return self._current_status(attempt_id)
            with self._lease_heartbeat(attempt):
                return self._process(attempt)
        except Exception:  # noqa: BLE001 - terminal boundary must fail closed for adapter failures
            status = self._fail(found)
            with suppress(Exception):
                self._report_usage(found)
            return status
        finally:
            with suppress(Exception):
                self._report_usage(found)
            try:
                with self._database.transaction() as repositories:
                    repositories.mentor_response_attempts.release_claim(
                        attempt_id, owner
                    )
            finally:
                self._execution_owner_context.reset(token)

    def _usage_recorder(
        self, attempt: MentorResponseAttempt, block_key: str
    ) -> Callable[[MentorInferenceUsage], None]:
        def record(usage: MentorInferenceUsage) -> None:
            if (
                not usage.call_key
                or not usage.profile
                or (
                    usage.used_tokens is not None
                    and (isinstance(usage.used_tokens, bool) or usage.used_tokens < 0)
                )
                or any(
                    value is not None and (isinstance(value, bool) or value < 0)
                    for value in (usage.input_tokens, usage.output_tokens)
                )
                or (
                    usage.cost_usd is not None
                    and (
                        isinstance(usage.cost_usd, bool)
                        or not isfinite(usage.cost_usd)
                        or usage.cost_usd < 0
                    )
                )
            ):
                raise ServiceUnavailableError
            owner = self._execution_owner
            if owner is None:
                raise ServiceUnavailableError
            with self._database.transaction() as repositories:
                if not repositories.mentor_response_attempts.journal_usage(
                    attempt.id,
                    owner,
                    attempt.access_revision,
                    replace(usage, call_key=f'{block_key}:{usage.call_key}'),
                ):
                    raise ServiceUnavailableError
            if self._telemetry is not None:
                with suppress(Exception):
                    self._telemetry.record_inference(
                        usage.profile,
                        usage.used_tokens,
                        usage.input_tokens,
                        usage.output_tokens,
                        usage.cost_usd,
                    )
            self._report_usage(attempt, require_inference=True, allow_unknown=True)

        return record

    def _report_usage(
        self,
        attempt: MentorResponseAttempt,
        require_inference: bool = False,
        allow_unknown: bool = False,
    ) -> None:
        with self._database.transaction() as repositories:
            current = repositories.mentor_response_attempts.find_by_id(attempt.id)
            calls = repositories.mentor_response_attempts.read_usage(attempt.id)
            started = repositories.mentor_response_attempts.inference_started(
                attempt.id
            )
        if current is None:
            raise ServiceUnavailableError
        if calls is None or ((require_inference or started) and not calls):
            raise ServiceUnavailableError
        if any(call.used_tokens is None for call in calls):
            if allow_unknown:
                return
            raise ServiceUnavailableError
        tokens = sum(call.used_tokens for call in calls if call.used_tokens is not None)
        self._access_provider.record_usage(
            MentorAccessGrant(
                account_id=attempt.account_id,
                access_revision=attempt.access_revision,
                operation_key=attempt.operation_key,
            ),
            MentorUsage(
                operation_key=attempt.operation_key,
                attempt_id=attempt.id,
                used_tokens=tokens,
                cancelled=current.status is MentorResponseStatus.CANCELLED,
            ),
        )

    def _current_status(self, attempt_id: str) -> MentorResponseStatus:
        with self._database.transaction() as repositories:
            current = repositories.mentor_response_attempts.find_by_id(attempt_id)
        return current.status if current is not None else MentorResponseStatus.CANCELLED

    def _start(self, attempt_id: str) -> MentorResponseAttempt | None:
        with self._database.transaction() as repositories:
            found = repositories.mentor_response_attempts.find_by_id(attempt_id)
        if found is None:
            return None
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                found.account_id, found.session_id
            )
            attempt = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt_id
            )
            if attempt is None or attempt.status not in (
                MentorResponseStatus.QUEUED,
                MentorResponseStatus.PROCESSING,
            ):
                return None
            session = repositories.mentor_sessions.find_by_id_for_update(
                attempt.account_id, attempt.session_id
            )
            current = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if session is None or current is None or current.id != attempt.id:
                return None
            owner = self._execution_owner
            if owner is None or not repositories.mentor_response_attempts.claim(
                attempt.id,
                owner,
                self._clock_provider.now(),
                self._clock_provider.now() + timedelta(minutes=5),
                attempt.access_revision,
            ):
                return None
        # Commit the exclusive claim before checking access: revocation must not
        # roll back the ownership needed to durably fail this attempt.
        self._assert_access(attempt)
        with self._database.transaction() as repositories:
            self._assert_claim(repositories, attempt)
            self._assert_access(attempt)
            if attempt.status is MentorResponseStatus.QUEUED:
                if not repositories.mentor_response_attempts.transition(
                    attempt.id,
                    MentorResponseStatus.QUEUED,
                    MentorResponseStatus.PROCESSING,
                    attempt.access_revision,
                ):
                    return None
                repositories.mentor_response_events.append(
                    self._event(
                        attempt,
                        repositories.mentor_response_events.next_sequence(
                            attempt.session_id
                        ),
                        MentorResponseEventKind.STATUS,
                        MentorResponseStatus.PROCESSING,
                    )
                )
            return replace(attempt, status=MentorResponseStatus.PROCESSING)

    @contextmanager
    def _lease_heartbeat(self, attempt: MentorResponseAttempt) -> Generator[None]:
        stopped = Event()
        owner = self._execution_owner
        if owner is None:
            raise ServiceUnavailableError

        def renew() -> None:
            while not stopped.wait(30):
                try:
                    self._assert_access(attempt)
                    with self._database.transaction() as repositories:
                        now = self._clock_provider.now()
                        if not repositories.mentor_response_attempts.renew_claim(
                            attempt.id,
                            owner,
                            now,
                            now + timedelta(minutes=5),
                            attempt.access_revision,
                        ):
                            return
                except Exception:  # noqa: BLE001 - terminal boundary must fail closed for adapter failures
                    self._fail(attempt)
                    return

        context = copy_context()
        worker = Thread(target=context.run, args=(renew,), daemon=True)
        worker.start()
        try:
            yield
        finally:
            stopped.set()
            worker.join(timeout=5)

    def _process(self, attempt: MentorResponseAttempt) -> MentorResponseStatus:
        self._assert_access(attempt)
        with self._database.transaction() as repositories:
            history = repositories.mentor_messages.find_all(
                attempt.account_id, attempt.session_id
            )
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
            ),
            None,
        )
        if learner is None:
            return self._fail(attempt)
        hints = asdict(attempt.context_hint) if attempt.context_hint else {}
        explicit = tuple(
            dict.fromkeys(
                re.findall(r'\b[0-7][0-9A-HJKMNP-TV-Z]{25}\b', learner.content)
            )
        )
        references, ordinal_clarification = self._continuity_references(
            learner.content, explicit, continuity
        )
        context = self._read_context(attempt.account_id, references, **hints)
        context, named_clarification = self._resolve_named_context(
            attempt, learner.content, context, hints
        )
        with self._database.transaction() as repositories:
            self._assert_claim(repositories, attempt)
            self._assert_access(attempt)
            if not repositories.mentor_response_attempts.update_references(
                attempt.id, context.resolved_references, attempt.access_revision
            ):
                return MentorResponseStatus.CANCELLED
        self._assert_access(attempt)
        route = self._route(
            learner.content,
            context,
            self._revalidate_proposal(references, continuity, context)
            or ordinal_clarification
            or named_clarification,
        )
        route = self._propose_catalog(attempt, learner.content, context, route)
        approved = (
            list(snapshot.blocks)
            if snapshot and snapshot.attempt_id == attempt.id
            else []
        )
        local = route.local_blocks
        local = self._clarify(local, route.clarification)
        with self._stage('local'):
            local, requests = self._pedagogical_gate(
                learner.content, context, local, route.generation_requests
            )
        for block in local:
            if not self._publish(attempt, block, approved, context):
                return self._fail(attempt)
        for index, requested in enumerate(requests):
            key = f'generated-{index}'
            if any(block.block_key == key for block in approved):
                continue
            self._assert_access(attempt)
            context = self._read_context(
                attempt.account_id, context.resolved_references, **hints
            )
            request = MentorGenerationRequest(
                session_id=attempt.session_id,
                learner_message_id=attempt.learner_message_id,
                attempt_id=attempt.id,
                requested_part=requested,
                history=history,
                context=context,
                approved_blocks=tuple(approved),
                correction=None,
            )
            if not self._reserve(attempt, key):
                return self._fail(attempt)
            with self._stage('generate'):
                block = self._answer_workflow.run(
                    request,
                    self._usage_recorder(attempt, key),
                    lambda: self._assert_inference_ready(attempt),
                    self._progress_recorder(attempt),
                )
            self._report_usage(attempt, require_inference=True)
            block = replace(block, block_key=key, ordinal=len(approved))
            if not self._publish(attempt, block, approved, context):
                return self._fail(attempt)
        if not approved:
            return self._fail(attempt)
        content = '\n\n'.join(
            block.content for block in sorted(approved, key=lambda block: block.ordinal)
        )
        self._report_usage(attempt)
        finalized = self._finalize(attempt, content)
        return MentorResponseStatus.COMPLETED if finalized else self._fail(attempt)

    def _publish(
        self,
        attempt: MentorResponseAttempt,
        block: MentorResponseBlock,
        approved: list[MentorResponseBlock],
        expected_context: MentorContextSnapshot,
    ) -> bool:
        if any(existing.block_key == block.block_key for existing in approved):
            return True
        hints = asdict(attempt.context_hint) if attempt.context_hint else {}
        self._assert_access(attempt)
        fresh_context = self._read_context(
            attempt.account_id, expected_context.resolved_references, **hints
        )
        if self._context_permissions(fresh_context) != self._context_permissions(
            expected_context
        ):
            raise ServiceUnavailableError
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                attempt.account_id, attempt.session_id
            )
            current = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt.id
            )
            latest = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if (
                session is None
                or current is None
                or latest is None
                or latest.id != attempt.id
                or current.status is not MentorResponseStatus.PROCESSING
                or self._execution_owner is None
                or not repositories.mentor_response_attempts.has_claim(
                    attempt.id, self._execution_owner, self._clock_provider.now()
                )
            ):
                return False
            self._assert_access(attempt)
            snapshot = repositories.mentor_response_events.snapshot(
                attempt.account_id, attempt.session_id
            )
            existing = (
                next(
                    (
                        item
                        for item in snapshot.blocks
                        if item.block_key == block.block_key
                    ),
                    None,
                )
                if snapshot
                else None
            )
            if existing is not None:
                approved.append(existing)
                return True
            event = self._event(
                attempt,
                repositories.mentor_response_events.next_sequence(attempt.session_id),
                MentorResponseEventKind.BLOCK,
                MentorResponseStatus.PROCESSING,
            )
            with self._stage('publish'):
                repositories.mentor_response_events.append(replace(event, block=block))
        approved.append(block)
        return True

    def _fail(self, attempt: MentorResponseAttempt) -> MentorResponseStatus:
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                attempt.account_id, attempt.session_id
            )
            if session is None:
                return MentorResponseStatus.CANCELLED
            current = repositories.mentor_response_attempts.find_by_id_for_update(
                attempt.id
            )
            if current is None or current.status not in (
                MentorResponseStatus.QUEUED,
                MentorResponseStatus.PROCESSING,
            ):
                return MentorResponseStatus.CANCELLED
            if not self._recover_failure_claim(repositories, attempt):
                return current.status
            if repositories.mentor_response_attempts.transition(
                attempt.id,
                current.status,
                MentorResponseStatus.FAILED,
                attempt.access_revision,
            ):
                event = self._event(
                    attempt,
                    repositories.mentor_response_events.next_sequence(
                        attempt.session_id
                    ),
                    MentorResponseEventKind.FAILED,
                    MentorResponseStatus.FAILED,
                )
                try:
                    self._assert_access(attempt)
                except Exception:  # noqa: BLE001 - fail closed without exposing adapter errors
                    return MentorResponseStatus.FAILED
                repositories.mentor_response_events.append(
                    replace(event, failure_code='service_unavailable')
                )
        return MentorResponseStatus.FAILED

    def _recover_failure_claim(
        self,
        repositories: IntelligenceDatabaseRepositories,
        attempt: MentorResponseAttempt,
    ) -> bool:
        owner = self._execution_owner
        if owner is None:
            return False
        now = self._clock_provider.now()
        return repositories.mentor_response_attempts.has_claim(
            attempt.id, owner, now
        ) or repositories.mentor_response_attempts.claim(
            attempt.id, owner, now, now + timedelta(minutes=5), attempt.access_revision
        )

    def _assert_claim(
        self,
        repositories: IntelligenceDatabaseRepositories,
        attempt: MentorResponseAttempt,
    ) -> None:
        owner = self._execution_owner
        if owner is None or not repositories.mentor_response_attempts.has_claim(
            attempt.id, owner, self._clock_provider.now()
        ):
            raise ServiceUnavailableError

    def _assert_inference_ready(self, attempt: MentorResponseAttempt) -> None:
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                attempt.account_id, attempt.session_id
            )
            current = repositories.mentor_response_attempts.find_by_id(attempt.id)
            latest = repositories.mentor_response_attempts.find_current(
                attempt.account_id, attempt.session_id
            )
            if (
                session is None
                or current is None
                or current.status is not MentorResponseStatus.PROCESSING
                or latest is None
                or latest.id != attempt.id
            ):
                raise ServiceUnavailableError
            self._assert_claim(repositories, attempt)
            self._assert_access(attempt)

    def _assert_access(self, attempt: MentorResponseAttempt) -> None:
        self._access_provider.assert_current(
            MentorAccessGrant(
                account_id=attempt.account_id,
                access_revision=attempt.access_revision,
                operation_key=attempt.operation_key,
            )
        )

    def _event(
        self,
        attempt: MentorResponseAttempt,
        sequence: int,
        kind: MentorResponseEventKind,
        status: MentorResponseStatus,
    ) -> MentorResponseEvent:
        return MentorResponseEvent(
            session_id=attempt.session_id,
            attempt_id=attempt.id,
            sequence=sequence,
            kind=kind,
            status=status,
            block=None,
            consultation=None,
            failure_code=None,
            created_at=self._clock_provider.now(),
        )

    def _reserve(self, attempt: MentorResponseAttempt, key: str) -> bool:
        with self._database.transaction() as repositories:
            self._assert_claim(repositories, attempt)
            self._assert_access(attempt)
            return repositories.mentor_response_attempts.reserve_generation(
                attempt.id, key, attempt.access_revision
            )

    def _progress_recorder(
        self, attempt: MentorResponseAttempt
    ) -> Callable[[MentorWorkflowStep], None]:
        def record(step: MentorWorkflowStep) -> None:
            if type(step) is not MentorWorkflowStep:
                raise ServiceUnavailableError
            with self._database.transaction() as repositories:
                session = repositories.mentor_sessions.find_by_id_for_update(
                    attempt.account_id, attempt.session_id
                )
                current = repositories.mentor_response_attempts.find_by_id_for_update(
                    attempt.id
                )
                latest = repositories.mentor_response_attempts.find_current(
                    attempt.account_id, attempt.session_id
                )
                if (
                    session is None
                    or current is None
                    or current.status is not MentorResponseStatus.PROCESSING
                    or latest is None
                    or latest.id != attempt.id
                ):
                    raise ServiceUnavailableError
                self._assert_claim(repositories, attempt)
                self._assert_access(attempt)
                event = self._event(
                    attempt,
                    repositories.mentor_response_events.next_sequence(
                        attempt.session_id
                    ),
                    MentorResponseEventKind.STATUS,
                    MentorResponseStatus.PROCESSING,
                )
                repositories.mentor_response_events.append(
                    replace(event, progress=step)
                )

        return record

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

    def _propose_catalog(
        self,
        attempt: MentorResponseAttempt,
        content: str,
        context: MentorContextSnapshot,
        route: MentorRouteResult,
    ) -> MentorRouteResult:
        if route.clarification or not any(
            block.intent is MentorIntent.SEARCH_CURRICULUM
            for block in route.local_blocks
        ):
            return route
        projected = self._catalog_provider.read_projection()
        by_reference = {entry.reference_id: entry for entry in projected}
        entries = tuple(
            by_reference[reference]
            for reference in route.proposed_reference_ids
            if reference in by_reference
        )
        entries = tuple(
            entry
            for entry in entries
            if entry.reference_id in context.eligible_references
        )
        if not entries:
            return route
        entries = tuple({entry.reference_id: entry for entry in entries}.values())
        references = tuple(entry.reference_id for entry in entries)
        with self._database.transaction() as repositories:
            self._assert_claim(repositories, attempt)
            self._assert_access(attempt)
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

    def _route(
        self, content: str, context: MentorContextSnapshot, clarification: str | None
    ) -> MentorRouteResult:
        clarification = next(
            (value for key, value in context.facts if key == 'context_clarification'),
            clarification,
        )
        with self._stage('route'):
            route = self._route_provider.route(content, context)
        if clarification is not None:
            return replace(route, clarification=clarification, generation_requests=())
        return route

    def _resolve_named_context(
        self,
        attempt: MentorResponseAttempt,
        content: str,
        context: MentorContextSnapshot,
        hints: dict[str, str | None],
    ) -> tuple[MentorContextSnapshot, str | None]:
        goal_matches = self._named_goals(content, context)
        if len(goal_matches) > 1:
            return (
                context,
                'Encontrei mais de um Objetivo com esse nome. Qual Objetivo você quer consultar?',
            )
        if goal_matches:
            self._assert_access(attempt)
            context = self._read_context(attempt.account_id, goal_matches, **hints)
        matches = self._catalog_provider.search(
            attempt.account_id, content, context.eligible_references
        )
        explicit = tuple(
            entry.reference_id
            for entry in matches
            if self._contains_title(content, entry.title)
        )
        if explicit:
            self._assert_access(attempt)
            context = self._read_context(
                attempt.account_id, (*goal_matches, *explicit), **hints
            )
        return context, None

    @classmethod
    def _named_goals(
        cls, content: str, context: MentorContextSnapshot
    ) -> tuple[str, ...]:
        matches: list[str] = []
        for key, value in context.facts:
            if key != 'goals' or ': ' not in value:
                continue
            reference, title = value.split(': ', 1)
            if re.fullmatch(
                r'[0-7][0-9A-HJKMNP-TV-Z]{25}', reference
            ) and cls._contains_title(content, title):
                matches.append(reference)
        return tuple(dict.fromkeys(matches))

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
                r'(?<!\w)' + re.escape(normalized_title) + r'(?!\w)', normalize(content)
            )
        )

    @staticmethod
    def _context_permissions(context: MentorContextSnapshot) -> tuple[object, ...]:
        return (
            context.goal_id,
            context.skill_experience_id,
            context.skill_id,
            context.activity_id,
            context.skill_completed,
            context.diagnostic_in_progress,
            context.eligible_references,
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
        )
        if context.activity_id is not None and context.activity_id in content:
            targets_activity = True
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
                block_key='clarification', ordinal=0, intent=None, content=clarification
            ),
        )

    def _read_context(
        self, account_id: str, reference_ids: tuple[str, ...], **hints: str | None
    ) -> MentorContextSnapshot:
        with self._stage('context'):
            return self._context_provider.read(account_id, reference_ids, **hints)

    def _finalize(self, attempt: MentorResponseAttempt, content: str) -> bool:
        with self._stage('persist'):
            return FinalizeMentorResponseUseCase(
                self._database,
                self._identifier_provider,
                self._clock_provider,
                self._access_provider,
            ).execute(
                attempt.account_id,
                attempt.session_id,
                attempt.learner_message_id,
                content,
                attempt.id,
                self._execution_owner,
            )

    @contextmanager
    def _stage(self, stage: str) -> Generator[None]:
        if self._telemetry is None:
            yield
            return
        entered = False
        manager = None
        with suppress(Exception):
            manager = self._telemetry.scope(stage)
            manager.__enter__()
            entered = True
        if not entered or manager is None:
            yield
            return
        try:
            yield
        except BaseException as error:
            with suppress(Exception):
                manager.__exit__(type(error), error, error.__traceback__)
            raise
        else:
            with suppress(Exception):
                manager.__exit__(None, None, None)
