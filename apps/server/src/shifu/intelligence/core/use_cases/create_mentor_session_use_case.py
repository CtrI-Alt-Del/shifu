import hashlib
import re
import unicodedata
from uuid import UUID

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSession
from shifu.intelligence.core.domain.enums import MentorMessageRole
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
from shifu.shared.core.interfaces import ClockProvider, IdentifierProvider


class CreateMentorSessionUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        title_workflow: GenerateMentorTitleWorkflow,
    ) -> None:
        self._database = database
        self._identifier_provider = identifier_provider
        self._clock_provider = clock_provider
        self._title_workflow = title_workflow

    def execute(
        self, account_id: str, submission_key: str, first_message: str
    ) -> CreateMentorSessionResult:
        if not first_message.strip():
            raise MentorInputInvalidError
        try:
            parsed_key = UUID(submission_key)
        except ValueError as error:
            raise MentorInputInvalidError from error
        if parsed_key.version != 4 or str(parsed_key) != submission_key.lower():
            raise MentorInputInvalidError

        fingerprint = hashlib.sha256(first_message.encode('utf-8')).hexdigest()
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
            detail = MentorSessionDetail(
                session=session,
                messages=MentorMessagesPage(items=[message], next_cursor=None),
                pending_learner_message_id=message.id,
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
            raise MentorSubmissionConflictError
        session = repositories.mentor_sessions.find_by_id(
            account_id, existing.session_id
        )
        if session is None:
            raise MentorSessionNotFoundError
        return CreateMentorSessionResult(
            detail=MentorSessionDetail(
                session=session,
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
