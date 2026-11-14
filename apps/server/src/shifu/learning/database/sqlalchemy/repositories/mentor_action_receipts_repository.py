from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.learning.core.domain.entities import MentorActionReceipt
from shifu.learning.database.sqlalchemy.mappers import MentorActionReceiptMapper
from shifu.learning.database.sqlalchemy.models import MentorActionReceiptModel


_CONFIRMATION_CONSTRAINT = 'uq_learning_mentor_action_receipt_confirmation'


def _violated_constraint(error: IntegrityError) -> str | None:
    diagnostics: object = getattr(error.orig, 'diag', None)
    name: object = getattr(diagnostics, 'constraint_name', None)
    return name if isinstance(name, str) else None


class SqlalchemyMentorActionReceiptsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_confirmation_id(
        self,
        account_id: str,
        confirmation_id: str,
    ) -> MentorActionReceipt | None:
        model = self._session.scalar(
            select(MentorActionReceiptModel).where(
                MentorActionReceiptModel.account_id == account_id,
                MentorActionReceiptModel.confirmation_id == confirmation_id,
            )
        )
        return MentorActionReceiptMapper.to_domain(model) if model is not None else None

    def try_add(self, receipt: MentorActionReceipt) -> bool:
        # Surface errors of earlier pending writes before the savepoint, so only
        # a violation of the receipt's own unique key is read as a lost race.
        self._session.flush()
        try:
            with self._session.begin_nested():
                self._session.add(MentorActionReceiptMapper.to_model(receipt))
                self._session.flush()
        except IntegrityError as error:
            if _violated_constraint(error) != _CONFIRMATION_CONSTRAINT:
                raise
            return False
        return True
