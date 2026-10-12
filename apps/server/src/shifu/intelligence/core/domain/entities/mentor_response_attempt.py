from datetime import datetime
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures.mentor_context_hint import (
    MentorContextHint,
)
from shifu.shared.core.domain.entities import frozen_entity


@frozen_entity
class MentorResponseAttempt:
    id: str
    account_id: str
    session_id: str
    learner_message_id: str
    status: MentorResponseStatus
    context_hint: MentorContextHint | None
    access_revision: str
    operation_key: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        id: str,
        account_id: str,
        session_id: str,
        learner_message_id: str,
        status: MentorResponseStatus,
        context_hint: MentorContextHint | None,
        access_revision: str,
        operation_key: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> 'MentorResponseAttempt':
        if not all(
            (
                id,
                account_id,
                session_id,
                learner_message_id,
                access_revision,
                operation_key,
            )
        ):
            raise ValueError('Incomplete response attempt')
        if (
            created_at.tzinfo is None
            or updated_at.tzinfo is None
            or updated_at < created_at
        ):
            raise ValueError('Invalid response attempt timestamps')
        return cls(
            id=id,
            account_id=account_id,
            session_id=session_id,
            learner_message_id=learner_message_id,
            status=status,
            context_hint=context_hint,
            access_revision=access_revision,
            operation_key=operation_key,
            created_at=created_at,
            updated_at=updated_at,
        )
