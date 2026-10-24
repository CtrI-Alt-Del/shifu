from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import MentorActionProposal
from shifu.intelligence.database.sqlalchemy.mappers import MentorActionProposalMapper
from shifu.intelligence.database.sqlalchemy.models import MentorActionProposalModel


class SqlalchemyMentorActionProposalsRepository:
    def __init__(self, session: Session) -> None:
        self._session: Session = session

    def add(self, proposal: MentorActionProposal) -> None:
        self._session.add(MentorActionProposalMapper.to_model(proposal))
        self._session.flush()

    def find_by_id_for_update(
        self, account_id: str, proposal_id: str
    ) -> MentorActionProposal | None:
        model = self._session.scalar(
            select(MentorActionProposalModel)
            .where(
                MentorActionProposalModel.account_id == account_id,
                MentorActionProposalModel.id == proposal_id,
            )
            .with_for_update()
        )
        return MentorActionProposalMapper.to_entity(model) if model else None

    def find_many_by_session(
        self, account_id: str, session_id: str
    ) -> list[MentorActionProposal]:
        models = self._session.scalars(
            select(MentorActionProposalModel)
            .where(
                MentorActionProposalModel.account_id == account_id,
                MentorActionProposalModel.session_id == session_id,
            )
            .order_by(
                MentorActionProposalModel.created_at, MentorActionProposalModel.id
            )
        )
        return [MentorActionProposalMapper.to_entity(model) for model in models]

    def exists_pending(self, account_id: str, session_id: str) -> bool:
        return bool(
            self._session.scalar(
                select(
                    exists().where(
                        MentorActionProposalModel.account_id == account_id,
                        MentorActionProposalModel.session_id == session_id,
                        MentorActionProposalModel.status == 'pending',
                    )
                )
            )
        )

    def update(self, proposal: MentorActionProposal) -> None:
        model = self._session.get(MentorActionProposalModel, proposal.id)
        if model is None:
            raise ValueError('Missing action proposal')
        MentorActionProposalMapper.apply(model, proposal)
        self._session.flush()

    def remove_pending_by_attempt_id(self, account_id: str, attempt_id: str) -> int:
        removed = self._session.scalars(
            delete(MentorActionProposalModel)
            .where(
                MentorActionProposalModel.account_id == account_id,
                MentorActionProposalModel.attempt_id == attempt_id,
                MentorActionProposalModel.status == 'pending',
            )
            .returning(MentorActionProposalModel.id)
        ).all()
        return len(removed)

    def remove_by_session_id(self, account_id: str, session_id: str) -> int:
        removed = self._session.scalars(
            delete(MentorActionProposalModel)
            .where(
                MentorActionProposalModel.account_id == account_id,
                MentorActionProposalModel.session_id == session_id,
            )
            .returning(MentorActionProposalModel.id)
        ).all()
        return len(removed)

    def remove_by_account_id(self, account_id: str) -> int:
        removed = self._session.scalars(
            delete(MentorActionProposalModel)
            .where(MentorActionProposalModel.account_id == account_id)
            .returning(MentorActionProposalModel.id)
        ).all()
        return len(removed)
