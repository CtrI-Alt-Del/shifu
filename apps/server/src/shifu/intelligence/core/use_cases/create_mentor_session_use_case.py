import hashlib
import re
import unicodedata
from uuid import UUID

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorResponseStatus,
    MentorResponseEventKind,
)
from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.events import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    MentorContextHint,
    MentorResponseEvent,
)
from shifu.intelligence.core.domain.structures.mentor_submission_fingerprint import (
    mentor_submission_fingerprint,
)
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorSessionNotFoundError,
    MentorSubmissionConflictError,
    MentorTitleOutputInvalidError,
    MentorTitleUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    CreateMentorSessionResult,
    MentorMessagesPage,
    MentorSessionDetail,
    MentorSubmissionRecord,
)
from shifu.intelligence.core.interfaces.intelligence_database import (
    IntelligenceDatabaseRepositories,
)
from shifu.intelligence.core.interfaces import (
    GenerateMentorTitleWorkflow,
    IntelligenceDatabase,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class CreateMentorSessionUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        title_workflow: GenerateMentorTitleWorkflow,
        access_provider: MentorAccessProvider,
    ) -> None:
        self._access_provider: MentorAccessProvider = access_provider
        self._database = database
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider
        self._title_workflow = title_workflow

    def execute(
        self,
        account_id: str,
        submission_key: str,
        first_message: str,
        context_hint: MentorContextHint | None = None,
    ) -> CreateMentorSessionResult:
        if not first_message.strip():
            raise MentorInputInvalidError
        try:
            parsed_key = UUID(submission_key)
        except ValueError as error:
            raise MentorInputInvalidError from error
        if parsed_key.version != 4 or str(parsed_key) != submission_key.lower():
            raise MentorInputInvalidError

        fingerprint = mentor_submission_fingerprint(first_message, context_hint)
        grant = self._access_provider.authorize(account_id, submission_key)
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            existing = repositories.mentor_sessions.find_submission(
                account_id, submission_key
            )
            if existing is not None:
                return self._existing_result(
                    repositories,
                    account_id,
                    submission_key,
                    existing,
                    fingerprint,
                )

        title = self._generate_title(first_message)
        now = self._clock_provider.now()
        with self._database.transaction() as repositories:
            repositories.mentor_sessions.lock_submission(account_id, submission_key)
            existing = repositories.mentor_sessions.find_submission(
                account_id, submission_key
            )
            if existing is not None:
                return self._existing_result(
                    repositories,
                    account_id,
                    submission_key,
                    existing,
                    fingerprint,
                )

            session = MentorSession(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                title=title,
                created_at=now,
                updated_at=now,
                last_activity_at=now,
            )
            message = MentorMessage(
                id=self._identifier_provider.generate(),
                session_id=session.id,
                role=MentorMessageRole.LEARNER,
                content=first_message,
                created_at=now,
                in_reply_to_message_id=None,
            )
            repositories.mentor_sessions.add(session, submission_key, fingerprint)
            repositories.mentor_messages.add(message)
            self._access_provider.assert_current(grant)
            attempt = MentorResponseAttempt.create(
                id=self._identifier_provider.generate(),
                account_id=account_id,
                session_id=session.id,
                learner_message_id=message.id,
                status=MentorResponseStatus.QUEUED,
                context_hint=context_hint,
                access_revision=grant.access_revision,
                operation_key=grant.operation_key,
                created_at=now,
                updated_at=now,
            )
            repositories.mentor_response_attempts.add(attempt)
            repositories.mentor_response_attempts.add_submission(
                account_id, session.id, submission_key, attempt.id, fingerprint
            )
            repositories.mentor_response_events.append(
                MentorResponseEvent(
                    session_id=session.id,
                    attempt_id=attempt.id,
                    sequence=repositories.mentor_response_events.next_sequence(
                        session.id
                    ),
                    kind=MentorResponseEventKind.STATUS,
                    status=MentorResponseStatus.QUEUED,
                    block=None,
                    consultation=None,
                    failure_code=None,
                    created_at=now,
                )
            )
            repositories.events.add(
                MentorResponseRequestedEvent(
                    payload=MentorResponseRequestedPayload(attempt_id=attempt.id)
                )
            )
            detail = MentorSessionDetail(
                session=session,
                messages=MentorMessagesPage(items=[message], next_cursor=None),
                pending_learner_message_id=message.id,
                response=repositories.mentor_response_events.snapshot(
                    account_id, session.id
                ),
            )
            return CreateMentorSessionResult(detail=detail, created=True)

    def _generate_title(self, first_message: str) -> str:
        try:
            title = self._title_workflow.generate(first_message[:1000]).strip()
        except (MentorTitleUnavailableError, MentorTitleOutputInvalidError):
            return self._fallback_title(first_message)

        if not title or len(title) > 120:
            return self._fallback_title(first_message)
        return title

    @staticmethod
    def _fallback_title(first_message: str) -> str:
        normalized = re.sub(
            r'\s+', ' ', unicodedata.normalize('NFKC', first_message)
        ).strip()
        return normalized[:120].rstrip() or 'Nova conversa'

    @staticmethod
    def _existing_result(
        repositories: IntelligenceDatabaseRepositories,
        account_id: str,
        submission_key: str,
        existing: MentorSubmissionRecord,
        fingerprint: str,
    ) -> CreateMentorSessionResult:
        repositories.mentor_sessions.lock_session(account_id, existing.session_id)
        current = repositories.mentor_sessions.find_submission(
            account_id, submission_key
        )
        if current is None or current.session_id != existing.session_id:
            raise MentorSessionNotFoundError
        if current.deleted_at is not None:
            raise MentorSessionNotFoundError
        if current.content_fingerprint != fingerprint:
            legacy = repositories.mentor_response_attempts.find_submission(
                account_id, existing.session_id, submission_key
            )
            if legacy is not None:
                raise MentorSubmissionConflictError
            messages = repositories.mentor_messages.find_all(
                account_id, existing.session_id
            )
            first = next(
                (
                    message
                    for message in messages
                    if message.role is MentorMessageRole.LEARNER
                ),
                None,
            )
            if (
                first is None
                or hashlib.sha256(first.content.encode('utf-8')).hexdigest()
                != current.content_fingerprint
                or mentor_submission_fingerprint(first.content, None) != fingerprint
            ):
                raise MentorSubmissionConflictError
        session = repositories.mentor_sessions.find_by_id(
            account_id, existing.session_id
        )
        if session is None:
            raise MentorSessionNotFoundError
        return CreateMentorSessionResult(
            detail=MentorSessionDetail(
                session=session,
                response=repositories.mentor_response_events.snapshot(
                    account_id, session.id
                ),
                messages=repositories.mentor_messages.find_many(
                    account_id, session.id, None
                ),
                pending_learner_message_id=(
                    repositories.mentor_messages.find_pending_learner_message_id(
                        account_id, session.id
                    )
                ),
            ),
            created=False,
        )
