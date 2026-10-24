from shifu.gamification.core.domain.entities import ActivityXpRecognition
from shifu.gamification.database.sqlalchemy.models import ActivityXpRecognitionModel


class ActivityXpRecognitionMapper:
    @staticmethod
    def to_domain(model: ActivityXpRecognitionModel) -> ActivityXpRecognition:
        return ActivityXpRecognition(
            id=model.id,
            account_id=model.account_id,
            activity_id=model.activity_id,
            attempt_id=model.attempt_id,
            granted_xp=model.granted_xp,
            xp_grant_id=model.xp_grant_id,
            occurred_at=model.occurred_at,
            recognized_at=model.recognized_at,
        )

    @staticmethod
    def to_model(
        recognition: ActivityXpRecognition,
    ) -> ActivityXpRecognitionModel:
        return ActivityXpRecognitionModel(
            id=recognition.id,
            account_id=recognition.account_id,
            activity_id=recognition.activity_id,
            attempt_id=recognition.attempt_id,
            granted_xp=recognition.granted_xp,
            xp_grant_id=recognition.xp_grant_id,
            occurred_at=recognition.occurred_at,
            recognized_at=recognition.recognized_at,
        )
