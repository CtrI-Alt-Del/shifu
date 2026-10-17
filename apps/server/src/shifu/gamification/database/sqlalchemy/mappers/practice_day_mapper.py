from shifu.gamification.core.domain.entities import PracticeDay
from shifu.gamification.database.sqlalchemy.models import PracticeDayModel


class PracticeDayMapper:
    @staticmethod
    def to_domain(model: PracticeDayModel) -> PracticeDay:
        return PracticeDay(
            id=model.id,
            account_id=model.account_id,
            practice_date=model.practice_date,
            time_zone=model.time_zone,
            practiced_at=model.practiced_at,
            recognized_at=model.recognized_at,
        )

    @staticmethod
    def to_model(practice_day: PracticeDay) -> PracticeDayModel:
        return PracticeDayModel(
            id=practice_day.id,
            account_id=practice_day.account_id,
            practice_date=practice_day.practice_date,
            time_zone=practice_day.time_zone,
            practiced_at=practice_day.practiced_at,
            recognized_at=practice_day.recognized_at,
        )
