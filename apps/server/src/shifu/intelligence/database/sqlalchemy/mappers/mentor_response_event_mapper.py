from typing import cast

from shifu.intelligence.core.domain.enums import (
    MentorIntent,
    MentorResponseEventKind,
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.intelligence.core.domain.structures import (
    MentorActionProposalItem,
    MentorResponseBlock,
    MentorResponseEvent,
)
from shifu.intelligence.core.domain.structures.mentor_attachment_source import (
    MentorAttachmentSource,
)
from shifu.intelligence.database.sqlalchemy.models import MentorResponseEventModel


class MentorResponseEventMapper:
    @staticmethod
    def to_structure(
        model: MentorResponseEventModel,
        action_proposal: MentorActionProposalItem | None = None,
    ) -> MentorResponseEvent:
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
                sources=tuple(
                    MentorAttachmentSource(
                        attachment_id=cast('str', source['attachment_id']),
                        chunk_id=cast('str', source['chunk_id']),
                        page_number=cast('int | None', source['page_number']),
                        locator=cast('str', source['locator']),
                    )
                    for source in model.sources
                ),
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
            action_proposal=action_proposal,
        )

    @staticmethod
    def to_model(event: MentorResponseEvent) -> MentorResponseEventModel:
        block = event.block
        return MentorResponseEventModel(
            session_id=event.session_id,
            attempt_id=event.attempt_id,
            sequence=event.sequence,
            kind=event.kind.value,
            action_proposal_id=(
                event.action_proposal.id if event.action_proposal else None
            ),
            status=event.status.value,
            block_key=block.block_key if block else None,
            ordinal=block.ordinal if block else None,
            intent=block.intent.value if block and block.intent else None,
            content=block.content if block else None,
            sources=(
                [
                    {
                        'attachment_id': source.attachment_id,
                        'chunk_id': source.chunk_id,
                        'page_number': source.page_number,
                        'locator': source.locator,
                    }
                    for source in block.sources
                ]
                if block
                else []
            ),
            progress=event.progress.value if event.progress else None,
            consultation=event.consultation,
            failure_code=event.failure_code,
            created_at=event.created_at,
        )
