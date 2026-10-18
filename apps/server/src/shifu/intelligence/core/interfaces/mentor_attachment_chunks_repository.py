from typing import Protocol

from shifu.intelligence.core.domain.structures import MentorAttachmentChunk


class MentorAttachmentChunksRepository(Protocol):
    def add_many(self, chunks: tuple[MentorAttachmentChunk, ...]) -> None: ...

    def find_by_attachment_id(
        self, attachment_id: str, generation: int
    ) -> tuple[MentorAttachmentChunk, ...]: ...

    def find_many_eligible(
        self,
        account_id: str,
        session_id: str,
        attachment_ids: tuple[str, ...],
        page_numbers: tuple[int, ...],
    ) -> tuple[MentorAttachmentChunk, ...]: ...

    def remove_by_attachment_id(self, attachment_id: str) -> None: ...
