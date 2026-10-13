from dataclasses import asdict
from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import MentorContextHint
from shifu.intelligence.database.sqlalchemy.models import MentorResponseAttemptModel


class MentorResponseAttemptMapper:
    @staticmethod
    def to_entity(model: MentorResponseAttemptModel) -> MentorResponseAttempt:
        hint = (
            MentorContextHint(**model.context_hint)
            if model.context_hint is not None
            else None
        )
        return MentorResponseAttempt.create(
            id=model.id,
            account_id=model.account_id,
            session_id=model.session_id,
            learner_message_id=model.learner_message_id,
            status=MentorResponseStatus(model.status),
            context_hint=hint,
            access_revision=model.access_revision,
            operation_key=model.operation_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def to_model(attempt: MentorResponseAttempt) -> MentorResponseAttemptModel:
        return MentorResponseAttemptModel(
            id=attempt.id,
            account_id=attempt.account_id,
            session_id=attempt.session_id,
            learner_message_id=attempt.learner_message_id,
            status=attempt.status.value,
            context_hint=asdict(attempt.context_hint) if attempt.context_hint else None,
            access_revision=attempt.access_revision,
            operation_key=attempt.operation_key,
            created_at=attempt.created_at,
            updated_at=attempt.updated_at,
        )
