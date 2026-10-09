from shifu.intelligence.core.domain.structures import MentorSessionDetail
from shifu.intelligence.core.interfaces import IntelligenceDatabase


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
            messages=repositories.mentor_messages.find_many(
                account_id, session_id, cursor
            ),
            pending_learner_message_id=(
                repositories.mentor_messages.find_pending_learner_message_id(
                    account_id, session_id
                )
            ),
        )
