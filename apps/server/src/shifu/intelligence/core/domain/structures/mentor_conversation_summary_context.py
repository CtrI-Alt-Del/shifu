from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from shifu.intelligence.core.domain.enums import (
    MentorSummaryExcerptKind,
    MentorSummaryStatus,
)
from shifu.intelligence.core.domain.structures.mentor_summary_excerpt import (
    MentorSummaryExcerpt,
)
from shifu.shared.core.domain.structures import structure

if TYPE_CHECKING:
    from shifu.intelligence.core.domain.entities.mentor_message import MentorMessage
    from shifu.intelligence.core.domain.entities.mentor_session_summary import (
        MentorSessionSummary,
    )
    from shifu.intelligence.core.domain.structures.mentor_summary_boundary import (
        MentorSummaryBoundary,
    )


@structure
class MentorConversationSummaryContext:
    """The summary as consumers see it: topics, verbatim excerpts and template text."""

    EXCERPT_MAX_CODE_POINTS: ClassVar[int] = 280
    ELLIPSIS: ClassVar[str] = '…'
    TOPICS_TEMPLATE: ClassVar[str] = 'Nesta conversa, os assuntos foram {topics}.'
    TOPIC_TEMPLATE: ClassVar[str] = 'Nesta conversa, o assunto foi {topics}.'
    TOPICS_LAST_SEPARATOR: ClassVar[str] = ' e '
    DOUBT_TEMPLATES: ClassVar[tuple[str, str]] = (
        'Você perguntou: “{excerpt}”',
        'Você também perguntou: “{excerpt}”',
    )
    GUIDANCE_TEMPLATES: ClassVar[tuple[str, str]] = (
        'O Mentor orientou: “{excerpt}”',
        'O Mentor também orientou: “{excerpt}”',
    )

    version: int
    boundary: MentorSummaryBoundary
    covered_message_count: int
    first_message_id: str
    topics: tuple[str, ...]
    excerpts: tuple[MentorSummaryExcerpt, ...]
    text: str  # deterministic pt-BR template over topics/excerpts

    @classmethod
    def from_summary(
        cls, summary: MentorSessionSummary, messages: tuple[MentorMessage, ...]
    ) -> MentorConversationSummaryContext:
        """Render a ready summary from its source messages (pure, deterministic).

        Raises ``ValueError`` when the summary is not ready or when a span points to
        a message that is missing or no longer contains the span.
        """
        if summary.status is not MentorSummaryStatus.READY:
            raise ValueError('Only a ready summary can be rendered')
        by_id = {message.id: message for message in messages}
        ordered: list[tuple[tuple[object, ...], MentorSummaryExcerpt, bool]] = []
        for span in summary.excerpts:
            message = by_id.get(span.message_id)
            if message is None or not 0 <= span.start < span.end <= len(
                message.content
            ):
                raise ValueError('Summary excerpt is outside its source message')
            excerpt = MentorSummaryExcerpt(
                message_id=span.message_id,
                kind=span.kind,
                text=message.content[span.start : span.end],
            )
            cut = (
                span.end - span.start >= cls.EXCERPT_MAX_CODE_POINTS
                and message.content[span.end :].strip() != ''
            )
            ordered.append(
                ((message.created_at, message.id, span.start, span.end), excerpt, cut)
            )
        ordered.sort(key=lambda item: item[0])
        excerpts = tuple(excerpt for _, excerpt, _ in ordered)
        return cls(
            version=summary.version,
            boundary=summary.boundary,
            covered_message_count=summary.covered_message_count,
            first_message_id=summary.first_message_id,
            topics=summary.topics,
            excerpts=excerpts,
            text=cls._render(
                summary.topics, tuple((item[1], item[2]) for item in ordered)
            ),
        )

    @classmethod
    def _render(
        cls,
        topics: tuple[str, ...],
        excerpts: tuple[tuple[MentorSummaryExcerpt, bool], ...],
    ) -> str:
        sentences: list[str] = []
        if topics:
            template = cls.TOPIC_TEMPLATE if len(topics) == 1 else cls.TOPICS_TEMPLATE
            sentences.append(template.format(topics=cls._join_topics(topics)))
        for kind, templates in (
            (MentorSummaryExcerptKind.DOUBT, cls.DOUBT_TEMPLATES),
            (MentorSummaryExcerptKind.GUIDANCE, cls.GUIDANCE_TEMPLATES),
        ):
            of_kind = [item for item in excerpts if item[0].kind is kind]
            for index, (excerpt, cut) in enumerate(of_kind):
                text = excerpt.text + (cls.ELLIPSIS if cut else '')
                sentences.append(templates[min(index, 1)].format(excerpt=text))
        return ' '.join(sentences)

    @classmethod
    def _join_topics(cls, topics: tuple[str, ...]) -> str:
        if len(topics) == 1:
            return topics[0]
        return ', '.join(topics[:-1]) + cls.TOPICS_LAST_SEPARATOR + topics[-1]
