from uuid import UUID

from shifu.intelligence.core.domain.entities import MentorMessage, MentorResponseAttempt
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorResponseEventKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.errors import (
    MentorInputInvalidError,
    MentorResponseConflictError,
    MentorSessionNotFoundError,
    MentorSubmissionConflictError,
)
from shifu.intelligence.core.domain.events import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseEvent,
    MentorSessionDetail,
    MentorSubmission,
)
from shifu.intelligence.core.domain.structures.mentor_submission_fingerprint import (
    mentor_submission_fingerprint,
    mentor_submission_fingerprint_v2,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.intelligence.core.use_cases.mentor_attachment_helpers import (
    attachment_fingerprint_values,
    selected_attachments,
)
from shifu.intelligence.core.use_cases.mentor_detail import (
    load_mentor_summary_state,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    IdentifierProvider,
    MentorAccessProvider,
)


class SubmitMentorMessageUseCase:
    def __init__(
        self,
        database: IntelligenceDatabase,
        identifier_provider: IdentifierProvider,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
    ) -> None:
        self.replayed: bool = False
        self._database: IntelligenceDatabase = database
        self._identifier_provider: IdentifierProvider = identifier_provider
        self._clock_provider: ClockProvider = clock_provider
        self._access_provider: MentorAccessProvider = access_provider

    def execute(
        self, account_id: str, session_id: str, submission: MentorSubmission
    ) -> MentorSessionDetail:
        self._validate(submission)
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id_for_update(
                account_id, session_id
            )
            if session is None:
                raise MentorSessionNotFoundError
            fingerprint_values = attachment_fingerprint_values(
                repositories,
                account_id,
                submission.attachment_batch_id,
                submission.attachment_ids,
            )
            fingerprint = mentor_submission_fingerprint_v2(
                submission.content, submission.context_hint, fingerprint_values
            )
            replay = repositories.mentor_response_attempts.find_submission(
                account_id, session_id, submission.submission_key
            )
            if replay is not None:
                self.replayed = True
                attached = repositories.mentor_attachments.find_by_message_id(
                    replay[0].learner_message_id
                )
                replay_attachment_ids = {attachment.id for attachment in attached}
                requested_attachment_ids = set(submission.attachment_ids)
                if (
                    replay[1] != fingerprint
                    and not (
                        not submission.attachment_ids
                        and not attached
                        and replay[1]
                        == mentor_submission_fingerprint(
                            submission.content, submission.context_hint
                        )
                    )
                ) or replay_attachment_ids != requested_attachment_ids:
                    raise MentorSubmissionConflictError
                self._access_provider.assert_current(
                    self._access_provider.authorize(account_id, replay[0].operation_key)
                )
            else:
                if (
                    repositories.mentor_messages.find_pending_learner_message_id(
                        account_id, session_id
                    )
                    is not None
                ):
                    raise MentorResponseConflictError
                selected = selected_attachments(
                    repositories,
                    account_id=account_id,
                    batch_id=submission.attachment_batch_id,
                    session_id=session_id,
                    attachment_ids=submission.attachment_ids,
                    now=self._clock_provider.now(),
                )
                grant = self._access_provider.authorize(
                    account_id, submission.submission_key
                )
                self._access_provider.assert_current(grant)
                now = self._clock_provider.now()
                message = MentorMessage(
                    id=self._identifier_provider.generate(),
                    session_id=session_id,
                    role=MentorMessageRole.LEARNER,
                    content=submission.content,
                    created_at=now,
                    in_reply_to_message_id=None,
                )
                attempt = MentorResponseAttempt.create(
                    id=self._identifier_provider.generate(),
                    account_id=account_id,
                    session_id=session_id,
                    learner_message_id=message.id,
                    status=MentorResponseStatus.QUEUED,
                    context_hint=submission.context_hint,
                    access_revision=grant.access_revision,
                    operation_key=grant.operation_key,
                    created_at=now,
                    updated_at=now,
                )
                repositories.mentor_messages.add(message)
                if selected:
                    batch = repositories.mentor_attachment_batches.find_by_id(
                        submission.attachment_batch_id or '', for_update=True
                    )
                    if batch is None:
                        raise MentorSubmissionConflictError
                    batch.consume(message.id)
                    for attachment in selected:
                        attachment.bind(session_id, message.id)
                        repositories.mentor_attachments.update(attachment)
                    repositories.mentor_attachment_batches.update(batch)
                repositories.mentor_response_attempts.add(attempt)
                repositories.mentor_response_attempts.add_submission(
                    account_id,
                    session_id,
                    submission.submission_key,
                    attempt.id,
                    fingerprint,
                )
                repositories.mentor_response_events.append(
                    MentorResponseEvent(
                        session_id=session_id,
                        attempt_id=attempt.id,
                        sequence=repositories.mentor_response_events.next_sequence(
                            session_id
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
                session.updated_at = now
                session.last_activity_at = now
                repositories.mentor_sessions.record_activity(session)
            return MentorSessionDetail(
                session=session,
                messages=repositories.mentor_messages.find_many(
                    account_id, session_id, None
                ),
                pending_learner_message_id=repositories.mentor_messages.find_pending_learner_message_id(
                    account_id, session_id
                ),
                response=repositories.mentor_response_events.snapshot(
                    account_id, session_id
                ),
                summary=load_mentor_summary_state(repositories, account_id, session_id),
                memory_items=repositories.learner_memory_changes.find_items_by_session(
                    account_id, session_id
                ),
            )

    @staticmethod
    def _validate(submission: MentorSubmission) -> None:
        if not submission.content.strip() and not submission.attachment_ids:
            raise MentorInputInvalidError
        try:
            parsed = UUID(submission.submission_key)
        except ValueError as error:
            raise MentorInputInvalidError from error
        if parsed.version != 4 or str(parsed) != submission.submission_key.lower():
            raise MentorInputInvalidError
