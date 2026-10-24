from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shifu.gamification.core.domain.entities import ActivityXpRecognition
from shifu.gamification.database.sqlalchemy.mappers import ActivityXpRecognitionMapper
from shifu.gamification.database.sqlalchemy.models import ActivityXpRecognitionModel


class SqlalchemyActivityXpRecognitionsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def try_add(self, recognition: ActivityXpRecognition) -> bool:
        try:
            with self._session.begin_nested():
                self._session.add(ActivityXpRecognitionMapper.to_model(recognition))
                self._session.flush()
        except IntegrityError:
            return False
        return True

    def find_by_account_id_and_attempt_id(
        self, account_id: str, attempt_id: str
    ) -> ActivityXpRecognition | None:
        model = self._session.scalar(
            select(ActivityXpRecognitionModel).where(
                ActivityXpRecognitionModel.account_id == account_id,
                ActivityXpRecognitionModel.attempt_id == attempt_id,
            )
        )
        return (
            ActivityXpRecognitionMapper.to_domain(model) if model is not None else None
        )

    def remove_many_by_account_id(self, account_id: str) -> None:
        self._session.execute(
            delete(ActivityXpRecognitionModel).where(
                ActivityXpRecognitionModel.account_id == account_id
            )
        )
