from typing import Protocol

from shifu.intelligence.core.domain.structures import MentorAttachmentExtraction


class MentorAttachmentExtractorProvider(Protocol):
    def validate(self, content: bytes, media_type: str) -> None: ...

    def extract(
        self, content: bytes, media_type: str, attachment_id: str, generation: int
    ) -> MentorAttachmentExtraction: ...

    def render_visual_pages(
        self,
        content: bytes,
        media_type: str,
        page_numbers: tuple[int, ...],
    ) -> tuple[tuple[int, bytes], ...]: ...
