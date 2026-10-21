from shifu.intelligence.core.domain.structures import (
    MentorSessionDetail,
    MentorSessionSummaryState,
    MentorSummaryMarker,
)
from shifu.intelligence.core.interfaces import (
    IntelligenceDatabase,
    IntelligenceDatabaseRepositories,
)


def _trigger_message_id(
    repositories: IntelligenceDatabaseRepositories,
    session_id: str,
    attempt_id: str | None,
) -> str | None:
    """The learner message whose answer run produced the summary, when still known."""
    if attempt_id is None:
        return None
    attempt = repositories.mentor_response_attempts.find_by_id(attempt_id)
    if attempt is None or attempt.session_id != session_id:
        return None
    return attempt.learner_message_id


def load_mentor_summary_state(
    repositories: IntelligenceDatabaseRepositories, account_id: str, session_id: str
) -> MentorSessionSummaryState:
    """Summary state for the timeline: the ready marker and a newer failure anchor."""
    ready = repositories.mentor_session_summaries.find_ready(account_id, session_id)
    failed = repositories.mentor_session_summaries.find_failed(account_id, session_id)
    current = (
        MentorSummaryMarker(
            version=ready.version,
            boundary_message_id=ready.boundary.message_id,
            covered_message_count=ready.covered_message_count,
            completed_at=ready.completed_at,
            after_message_id=_trigger_message_id(
                repositories, session_id, ready.attempt_id
            ),
        )
        if ready is not None and ready.completed_at is not None
        else None
    )
    failure_after_message_id = (
        _trigger_message_id(repositories, session_id, failed.attempt_id)
        if failed is not None and (ready is None or failed.version > ready.version)
        else None
    )
    return MentorSessionSummaryState(
        current=current, failure_after_message_id=failure_after_message_id
    )


def load_mentor_detail(
    database: IntelligenceDatabase,
    account_id: str,
    session_id: str,
    cursor: str | None = None,
) -> MentorSessionDetail | None:
    with database.transaction() as repositories:
        session = repositories.mentor_sessions.find_by_id(account_id, session_id)
        if session is None:
            return None

        return MentorSessionDetail(
            session=session,
            response=repositories.mentor_response_events.snapshot(
                account_id, session_id
            ),
            messages=repositories.mentor_messages.find_many(
                account_id, session_id, cursor
            ),
            pending_learner_message_id=(
                repositories.mentor_messages.find_pending_learner_message_id(
                    account_id, session_id
                )
            ),
            summary=load_mentor_summary_state(repositories, account_id, session_id),
            memory_items=repositories.learner_memory_changes.find_items_by_session(
                account_id, session_id
            ),
        )
