from shifu.intelligence.core.domain.entities import MentorSessionSummary
from shifu.intelligence.core.domain.enums import (
    MentorSummaryExcerptKind,
    MentorSummaryFailureCode,
    MentorSummaryStatus,
)
from shifu.intelligence.core.domain.structures import (
    MentorSummaryBoundary,
    MentorSummaryExcerptSpan,
)
from shifu.intelligence.database.sqlalchemy.models import MentorSessionSummaryModel


class MentorSessionSummaryMapper:
    @staticmethod
    def to_entity(model: MentorSessionSummaryModel) -> MentorSessionSummary:
        return MentorSessionSummary(
            id=model.id,
            account_id=model.account_id,
            session_id=model.session_id,
            attempt_id=model.attempt_id,
            version=model.version,
            status=MentorSummaryStatus(model.status),
            boundary=MentorSummaryBoundary(
                message_id=model.boundary_message_id,
                created_at=model.boundary_created_at,
            ),
            covered_message_count=model.covered_message_count,
            first_message_id=model.first_message_id,
            topics=tuple(model.topics or ()),
            excerpts=tuple(
                MentorSummaryExcerptSpan(
                    message_id=str(excerpt['message_id']),
                    start=int(excerpt['start']),
                    end=int(excerpt['end']),
                    kind=MentorSummaryExcerptKind(str(excerpt['kind'])),
                )
                for excerpt in model.excerpts or ()
            ),
            algorithm_version=model.algorithm_version,
            failure_code=(
                MentorSummaryFailureCode(model.failure_code)
                if model.failure_code is not None
                else None
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
        )

    @staticmethod
    def to_model(summary: MentorSessionSummary) -> MentorSessionSummaryModel:
        model = MentorSessionSummaryModel(
            id=summary.id,
            account_id=summary.account_id,
            session_id=summary.session_id,
            attempt_id=summary.attempt_id,
            version=summary.version,
            boundary_message_id=summary.boundary.message_id,
            boundary_created_at=summary.boundary.created_at,
            first_message_id=summary.first_message_id,
            covered_message_count=summary.covered_message_count,
            created_at=summary.created_at,
        )
        MentorSessionSummaryMapper.apply(model, summary)
        return model

    @staticmethod
    def apply(model: MentorSessionSummaryModel, summary: MentorSessionSummary) -> None:
        """Copy the mutable state of ``summary`` (never raw text) onto ``model``."""
        ready = summary.status is MentorSummaryStatus.READY
        model.status = summary.status.value
        model.attempt_id = summary.attempt_id
        model.topics = list(summary.topics) if ready else None
        model.excerpts = (
            [
                {
                    'message_id': span.message_id,
                    'start': span.start,
                    'end': span.end,
                    'kind': span.kind.value,
                }
                for span in summary.excerpts
            ]
            if ready
            else None
        )
        model.algorithm_version = summary.algorithm_version
        model.failure_code = (
            summary.failure_code.value if summary.failure_code is not None else None
        )
        model.updated_at = summary.updated_at
        model.completed_at = summary.completed_at
