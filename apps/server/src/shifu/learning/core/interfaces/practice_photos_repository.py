from typing import Protocol

from shifu.learning.core.domain.entities import PracticePhoto


class PracticePhotosRepository(Protocol):
    def find_by_id(self, photo_id: str) -> PracticePhoto | None: ...

    def list_live_for_draft(self, draft_id: str) -> tuple[PracticePhoto, ...]:
        """Return uploading, ready and failed photos of a draft."""
        ...

    def list_ready_for_draft(self, draft_id: str) -> tuple[PracticePhoto, ...]: ...

    def list_for_attempt(self, attempt_id: str) -> tuple[PracticePhoto, ...]:
        """Return the photos a submitted attempt owns."""
        ...

    def find_live_for_record(
        self, draft_id: str, record_key: str
    ) -> PracticePhoto | None: ...

    def find_by_upload_key(
        self, draft_id: str, upload_key: str
    ) -> PracticePhoto | None: ...

    def list_for_skill_experience(
        self, skill_experience_id: str
    ) -> tuple[PracticePhoto, ...]:
        """Return every photo owned by the experience's drafts and attempts."""
        ...

    def add(self, photo: PracticePhoto) -> None: ...

    def update(self, photo: PracticePhoto) -> None: ...

    def remove(self, photo_id: str) -> None: ...

    def reassign_to_attempt(self, draft_id: str, attempt_id: str) -> None:
        """Move the draft's ready photos to the attempt without copying files."""
        ...
