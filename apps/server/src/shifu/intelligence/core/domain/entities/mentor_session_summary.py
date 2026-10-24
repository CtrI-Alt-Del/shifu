from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar

from shifu.intelligence.core.domain.enums import (
    MentorSummaryExcerptKind,
    MentorSummaryFailureCode,
    MentorSummaryStatus,
)
from shifu.shared.core.domain.entities import frozen_entity

if TYPE_CHECKING:
    from datetime import datetime

    from shifu.intelligence.core.domain.structures.mentor_conversation_summary_draft import (
        MentorConversationSummaryDraft,
    )
    from shifu.intelligence.core.domain.structures.mentor_summary_boundary import (
        MentorSummaryBoundary,
    )
    from shifu.intelligence.core.domain.structures.mentor_summary_excerpt_span import (
        MentorSummaryExcerptSpan,
    )


@frozen_entity
class MentorSessionSummary:
    """One versioned extractive summary of the older part of a Mentor conversation."""

    MAX_TOPICS: ClassVar[int] = 8
    MAX_TOPIC_CODE_POINTS: ClassVar[int] = 80
    MAX_EXCERPTS_PER_KIND: ClassVar[int] = 5
    MAX_ALGORITHM_VERSION_CODE_POINTS: ClassVar[int] = 64

    id: str
    account_id: str
    session_id: str
    attempt_id: str | None  # required while PROCESSING
    version: int  # >= 1, unique per session
    status: MentorSummaryStatus
    boundary: MentorSummaryBoundary
    covered_message_count: int  # > 0
    first_message_id: str
    topics: tuple[str, ...]  # non-empty only when READY
    excerpts: tuple[MentorSummaryExcerptSpan, ...]  # only when READY
    algorithm_version: str | None  # only when READY
    failure_code: MentorSummaryFailureCode | None  # only when FAILED
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None  # only when READY

    def __post_init__(self) -> None:
        if not all(
            (
                self.id,
                self.account_id,
                self.session_id,
                self.first_message_id,
                self.boundary.message_id,
            )
        ):
            raise ValueError('Incomplete session summary')
        if self.version < 1 or self.covered_message_count < 1:
            raise ValueError('Invalid session summary counters')
        if (
            self.created_at.tzinfo is None
            or self.updated_at.tzinfo is None
            or self.boundary.created_at.tzinfo is None
            or self.updated_at < self.created_at
        ):
            raise ValueError('Invalid session summary timestamps')
        ready = self.status is MentorSummaryStatus.READY
        if (
            (self.status is MentorSummaryStatus.PROCESSING and not self.attempt_id)
            or ready != (self.completed_at is not None)
            or ready != (self.algorithm_version is not None)
            or (self.status is MentorSummaryStatus.FAILED)
            != (self.failure_code is not None)
            or (not ready and (self.topics or self.excerpts))
        ):
            raise ValueError('Inconsistent session summary state')

    @classmethod
    def start(
        cls,
        *,
        id: str,
        account_id: str,
        session_id: str,
        attempt_id: str,
        version: int,
        boundary: MentorSummaryBoundary,
        covered_message_count: int,
        first_message_id: str,
        now: datetime,
    ) -> MentorSessionSummary:
        if not attempt_id:
            raise ValueError('Incomplete session summary')
        return cls(
            id=id,
            account_id=account_id,
            session_id=session_id,
            attempt_id=attempt_id,
            version=version,
            status=MentorSummaryStatus.PROCESSING,
            boundary=boundary,
            covered_message_count=covered_message_count,
            first_message_id=first_message_id,
            topics=(),
            excerpts=(),
            algorithm_version=None,
            failure_code=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )

    def complete(
        self, draft: MentorConversationSummaryDraft, now: datetime
    ) -> MentorSessionSummary:
        self._require_processing()
        self._validate_draft(draft)
        return replace(
            self,
            status=MentorSummaryStatus.READY,
            topics=draft.topics,
            excerpts=draft.excerpts,
            algorithm_version=draft.algorithm_version,
            failure_code=None,
            updated_at=now,
            completed_at=now,
        )

    def fail(
        self, code: MentorSummaryFailureCode, now: datetime
    ) -> MentorSessionSummary:
        self._require_processing()
        return replace(
            self,
            status=MentorSummaryStatus.FAILED,
            topics=(),
            excerpts=(),
            algorithm_version=None,
            failure_code=code,
            updated_at=now,
            completed_at=None,
        )

    def _require_processing(self) -> None:
        if self.status is not MentorSummaryStatus.PROCESSING:
            raise ValueError('Only a processing summary can change state')

    @classmethod
    def _validate_draft(cls, draft: MentorConversationSummaryDraft) -> None:
        version = draft.algorithm_version
        if (
            not version.strip()
            or len(version) > cls.MAX_ALGORITHM_VERSION_CODE_POINTS
            or len(draft.topics) > cls.MAX_TOPICS
            or any(
                not topic.strip() or len(topic) > cls.MAX_TOPIC_CODE_POINTS
                for topic in draft.topics
            )
            or not (draft.topics or draft.excerpts)
        ):
            raise ValueError('Invalid summary draft')
        for kind in MentorSummaryExcerptKind:
            if (
                sum(1 for excerpt in draft.excerpts if excerpt.kind is kind)
                > cls.MAX_EXCERPTS_PER_KIND
            ):
                raise ValueError('Invalid summary draft')
