from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import MentorSessionSummary
from shifu.intelligence.core.domain.enums import MentorSummaryStatus
from shifu.intelligence.database.sqlalchemy.mappers import MentorSessionSummaryMapper
from shifu.intelligence.database.sqlalchemy.models import (
    MentorSessionModel,
    MentorSessionSummaryModel,
)
from shifu.shared.core.domain.errors import ConflictError


class SqlalchemyMentorSessionSummariesRepository:
    def __init__(self, session: Session) -> None:
        self._session: Session = session

    def find_ready(
        self, account_id: str, session_id: str
    ) -> MentorSessionSummary | None:
        return self._find_one(account_id, session_id, MentorSummaryStatus.READY)

    def find_processing_for_update(
        self, account_id: str, session_id: str
    ) -> MentorSessionSummary | None:
        return self._find_one(
            account_id, session_id, MentorSummaryStatus.PROCESSING, for_update=True
        )

    def find_failed(
        self, account_id: str, session_id: str
    ) -> MentorSessionSummary | None:
        return self._find_one(account_id, session_id, MentorSummaryStatus.FAILED)

    def next_version(self, session_id: str) -> int:
        highest = self._session.scalar(
            select(func.max(MentorSessionSummaryModel.version)).where(
                MentorSessionSummaryModel.session_id == session_id
            )
        )
        return (highest or 0) + 1

    def add(self, summary: MentorSessionSummary) -> None:
        self._session.add(MentorSessionSummaryMapper.to_model(summary))
        try:
            self._session.flush()
        except IntegrityError as error:
            raise ConflictError(
                'Já existe um resumo ativo para esta conversa.'
            ) from error

    def update(self, summary: MentorSessionSummary) -> None:
        model = self._session.get(MentorSessionSummaryModel, summary.id)
        if model is None:
            raise ConflictError('O resumo da conversa não está mais disponível.')
        MentorSessionSummaryMapper.apply(model, summary)
        self._session.flush()

    def remove_superseded(self, session_id: str, keep_id: str) -> None:
        self._session.execute(
            delete(MentorSessionSummaryModel).where(
                MentorSessionSummaryModel.session_id == session_id,
                MentorSessionSummaryModel.id != keep_id,
                MentorSessionSummaryModel.status.in_(
                    [MentorSummaryStatus.READY.value, MentorSummaryStatus.FAILED.value]
                ),
            )
        )

    def remove_superseded_failures(self, session_id: str, keep_id: str) -> None:
        self._session.execute(
            delete(MentorSessionSummaryModel).where(
                MentorSessionSummaryModel.session_id == session_id,
                MentorSessionSummaryModel.id != keep_id,
                MentorSessionSummaryModel.status == MentorSummaryStatus.FAILED.value,
            )
        )

    def remove(self, summary_id: str) -> None:
        self._session.execute(
            delete(MentorSessionSummaryModel).where(
                MentorSessionSummaryModel.id == summary_id
            )
        )

    def remove_by_session_id(self, session_id: str) -> None:
        self._session.execute(
            delete(MentorSessionSummaryModel).where(
                MentorSessionSummaryModel.session_id == session_id
            )
        )

    def remove_by_account_id(self, account_id: str) -> int:
        removed = self._session.scalars(
            delete(MentorSessionSummaryModel)
            .where(MentorSessionSummaryModel.account_id == account_id)
            .returning(MentorSessionSummaryModel.id)
        ).all()
        return len(removed)

    def remove_all(self) -> None:
        self._session.execute(delete(MentorSessionSummaryModel))

    def _find_one(
        self,
        account_id: str,
        session_id: str,
        status: MentorSummaryStatus,
        *,
        for_update: bool = False,
    ) -> MentorSessionSummary | None:
        query = (
            select(MentorSessionSummaryModel)
            .join(
                MentorSessionModel,
                and_(
                    MentorSessionModel.id == MentorSessionSummaryModel.session_id,
                    MentorSessionModel.account_id
                    == MentorSessionSummaryModel.account_id,
                ),
            )
            .where(
                MentorSessionSummaryModel.account_id == account_id,
                MentorSessionSummaryModel.session_id == session_id,
                MentorSessionSummaryModel.status == status.value,
                MentorSessionModel.deleted_at.is_(None),
            )
            .order_by(MentorSessionSummaryModel.version.desc())
            .limit(1)
        )
        if for_update:
            query = query.with_for_update(of=MentorSessionSummaryModel)
        model = self._session.scalar(query)
        return MentorSessionSummaryMapper.to_entity(model) if model else None
