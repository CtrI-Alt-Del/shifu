import unicodedata

from shifu.intelligence.core.domain.entities import MentorSession
from shifu.intelligence.database.sqlalchemy.models import MentorSessionModel


class MentorSessionMapper:
    @staticmethod
    def to_domain(model: MentorSessionModel) -> MentorSession:
        if (
            model.title is None
            or model.created_at is None
            or model.updated_at is None
            or model.last_activity_at is None
        ):
            raise ValueError('A deleted Mentor session cannot be mapped as active')
        return MentorSession(
            id=model.id,
            account_id=model.account_id,
            title=model.title,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_activity_at=model.last_activity_at,
        )

    @staticmethod
    def to_model(
        session: MentorSession, submission_key: str, content_fingerprint: str
    ) -> MentorSessionModel:
        return MentorSessionModel(
            id=session.id,
            account_id=session.account_id,
            submission_key=submission_key,
            content_fingerprint=content_fingerprint,
            title=session.title,
            title_search=MentorSessionMapper.to_search_title(session.title),
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_activity_at=session.last_activity_at,
        )

    @staticmethod
    def to_search_title(title: str) -> str:
        decomposed = unicodedata.normalize('NFKD', title.casefold())
        return ''.join(char for char in decomposed if not unicodedata.combining(char))
