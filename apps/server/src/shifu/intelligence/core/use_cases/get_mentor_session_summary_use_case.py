from shifu.intelligence.core.domain.errors import MentorSessionSummaryNotFoundError
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorSessionSummaryContent,
)
from shifu.intelligence.core.interfaces import IntelligenceDatabase
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.interfaces import MentorAccessProvider


class GetMentorSessionSummaryUseCase:
    def __init__(
        self, database: IntelligenceDatabase, access_provider: MentorAccessProvider
    ) -> None:
        self._database = database
        self._access_provider: MentorAccessProvider = access_provider

    def execute(self, account_id: str, session_id: str) -> MentorSessionSummaryContent:
        grant = self._access_provider.authorize(account_id, f'read:{session_id}')
        self._access_provider.assert_current(grant)
        with self._database.transaction() as repositories:
            session = repositories.mentor_sessions.find_by_id(account_id, session_id)
            if session is None:
                raise MentorSessionSummaryNotFoundError
            summary = repositories.mentor_session_summaries.find_ready(
                account_id, session_id
            )
            if summary is None:
                raise MentorSessionSummaryNotFoundError
            messages = repositories.mentor_messages.find_by_ids(
                account_id,
                session_id,
                tuple(dict.fromkeys(span.message_id for span in summary.excerpts)),
            )
        try:
            context = MentorConversationSummaryContext.from_summary(summary, messages)
        except ValueError as error:
            raise ServiceUnavailableError from error
        return MentorSessionSummaryContent(
            version=context.version,
            text=context.text,
            covered_message_count=context.covered_message_count,
            first_message_id=context.first_message_id,
        )
