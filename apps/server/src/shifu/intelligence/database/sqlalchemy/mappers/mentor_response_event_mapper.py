from shifu.intelligence.core.domain.enums import (
    MentorIntent,
    MentorResponseEventKind,
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorResponseBlock,
    MentorResponseEvent,
)
from shifu.intelligence.database.sqlalchemy.models import MentorResponseEventModel


class MentorResponseEventMapper:
    @staticmethod
    def to_structure(model: MentorResponseEventModel) -> MentorResponseEvent:
        block = None
        if (
            model.block_key is not None
            and model.ordinal is not None
            and model.content is not None
        ):
            block = MentorResponseBlock(
                block_key=model.block_key,
                ordinal=model.ordinal,
                intent=MentorIntent(model.intent) if model.intent else None,
                content=model.content,
            )
        return MentorResponseEvent(
            session_id=model.session_id,
            attempt_id=model.attempt_id,
            sequence=model.sequence,
            kind=MentorResponseEventKind(model.kind),
            status=MentorResponseStatus(model.status),
            block=block,
            progress=MentorWorkflowStep(model.progress) if model.progress else None,
            consultation=model.consultation,
            failure_code=model.failure_code,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(event: MentorResponseEvent) -> MentorResponseEventModel:
        block = event.block
        return MentorResponseEventModel(
            session_id=event.session_id,
            attempt_id=event.attempt_id,
            sequence=event.sequence,
            kind=event.kind.value,
            status=event.status.value,
            block_key=block.block_key if block else None,
            ordinal=block.ordinal if block else None,
            intent=block.intent.value if block and block.intent else None,
            content=block.content if block else None,
            progress=event.progress.value if event.progress else None,
            consultation=event.consultation,
            failure_code=event.failure_code,
            created_at=event.created_at,
        )
