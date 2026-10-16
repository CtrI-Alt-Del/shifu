from shifu.intelligence.core.domain.structures import MentorAttachmentChunk
from shifu.intelligence.database.sqlalchemy.models import MentorAttachmentChunkModel


class MentorAttachmentChunkMapper:
    @staticmethod
    def to_structure(model: MentorAttachmentChunkModel) -> MentorAttachmentChunk:
        return MentorAttachmentChunk(
            chunk_id=model.chunk_id,
            attachment_id=model.attachment_id,
            generation=model.generation,
            page_number=model.page_number,
            locator=model.locator,
            content=model.content,
        )

    @staticmethod
    def to_model(chunk: MentorAttachmentChunk) -> MentorAttachmentChunkModel:
        return MentorAttachmentChunkModel(
            chunk_id=chunk.chunk_id,
            attachment_id=chunk.attachment_id,
            generation=chunk.generation,
            page_number=chunk.page_number,
            locator=chunk.locator,
            content=chunk.content,
        )
