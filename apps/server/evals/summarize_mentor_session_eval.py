from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from importlib.resources import files
import json
import re
from time import monotonic
from typing import Any, ClassVar
import unicodedata

from shifu.intelligence.core.domain.entities import MentorMessage, MentorSessionSummary
from shifu.intelligence.core.domain.enums import (
    MentorMessageRole,
    MentorSummaryExcerptKind,
)
from shifu.intelligence.core.domain.structures import (
    MentorConversationSummaryContext,
    MentorConversationSummaryDraft,
    MentorSummaryBoundary,
)
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.summarization.textrank.textrank_mentor_conversation_summarizer_provider import (
    TextrankMentorConversationSummarizerProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)

from evals.eval import Eval


class SummarizeMentorSessionEval(Eval):
    """Gate the local extractive summary on a versioned synthetic pt-BR dataset.

    Local NLP only: identical in double and real modes, no model calls.
    """

    selector = 'summarize-mentor-session'
    workflow_id = 'intelligence-summarize-mentor-session'
    prompt_revision = 'textrank-mmr-e5-v1'
    unavailable_failure_code = 'summarizer_unavailable'
    DOUBT_RECALL: ClassVar[float] = 0.80
    GUIDANCE_RECALL: ClassVar[float] = 0.80
    TOPIC_RECALL: ClassVar[float] = 0.70
    DATASET: ClassVar[str] = 'mentor-summary-evaluation.json'
    BASE_TIME: ClassVar[datetime] = datetime(2026, 1, 1, tzinfo=UTC)
    EXCERPT_LIMIT: ClassVar[int] = 280
    FENCE: ClassVar[re.Pattern[str]] = re.compile(r'^ {0,3}(`{3,}|~{3,})')

    @dataclass(frozen=True)
    class Conversation:
        name: str
        messages: tuple[MentorMessage, ...]
        split_after: int | None
        expected: dict[str, Any]

    def __init__(self, *, mode: str) -> None:
        super().__init__(mode=mode)
        self.summarizer = TextrankMentorConversationSummarizerProvider(
            SpacyMentorTextPreprocessorProvider(),
            SentenceTransformersEmbeddingsProvider(),
        )
        self.model_profile = 'local-textrank'

    @property
    def dataset_revision(self) -> str:
        return str(self.dataset()['dataset_revision'])

    def cases(self) -> tuple[Eval.LocalCase, ...]:
        return tuple(
            Eval.LocalCase(
                name=str(entry['name']),
                tags=tuple(entry['tags']),
                input=f'{len(entry["messages"])} synthetic pt-BR messages',
                expected=entry['expected'],
            )
            for entry in self.dataset()['cases']
        )

    def run_local_cases(self, selected: tuple[Any, ...]) -> list[dict[str, Any]]:
        entries = {str(entry['name']): entry for entry in self.dataset()['cases']}
        conversations = [self.conversation(entries[case.name]) for case in selected]
        reports: list[dict[str, Any]] = []
        drafts: dict[str, MentorConversationSummaryDraft] = {}
        for conversation in conversations:
            started = monotonic()
            try:
                drafts[conversation.name] = self.summarize(conversation)
                report = self.score(conversation, drafts[conversation.name])
                # RF-02: the same input yields the same draft and rendered text.
                repeated = self.summarize(conversation)
                mismatch = int(
                    repeated != drafts[conversation.name]
                    or self.rendered(conversation, repeated)
                    != self.rendered(conversation, drafts[conversation.name])
                )
                report['nondeterministic'] = mismatch
                if mismatch:
                    report['passed'] = False
                    report['failure_code'] = 'nondeterministic_output'
            except Exception:  # noqa: BLE001 - provider errors can contain conversation text.
                report = {
                    'passed': False,
                    'failure_code': self.unavailable_failure_code,
                }
            report['case_id'] = conversation.name
            report['duration_seconds'] = round(max(monotonic() - started, 0.0), 3)
            reports.append(report)

        # Leakage and independence: replaying the cases in reverse order, after every
        # other conversation went through the same instance, must change nothing.
        for conversation in reversed(conversations):
            report = next(
                item for item in reports if item['case_id'] == conversation.name
            )
            if conversation.name not in drafts:
                continue
            try:
                replay = self.summarize(conversation)
            except Exception:  # noqa: BLE001 - see above.
                replay = None
            if replay != drafts[conversation.name]:
                report['leakage'] = report.get('leakage', 0) + 1
                report['passed'] = False
                report['failure_code'] = 'cross_case_leakage'

        return [self.case_report(report) for report in reports]

    # --- execution -----------------------------------------------------------

    @classmethod
    @cache
    def dataset(cls) -> dict[str, Any]:
        raw = (
            files('shifu.intelligence.ai.data').joinpath(cls.DATASET).read_text('utf-8')
        )
        return json.loads(raw)

    @classmethod
    def conversation(cls, entry: dict[str, Any]) -> Conversation:
        name = str(entry['name'])
        messages = tuple(
            MentorMessage(
                id=f'{name}:{index:03d}',
                session_id=name,
                role=MentorMessageRole(message['role']),
                content=message['content'],
                created_at=cls.BASE_TIME + timedelta(minutes=index),
                in_reply_to_message_id=None,
            )
            for index, message in enumerate(entry['messages'])
        )
        return cls.Conversation(
            name, messages, entry.get('split_after'), entry['expected']
        )

    def summarize(self, conversation: Conversation) -> MentorConversationSummaryDraft:
        if conversation.split_after is None:
            return self.summarizer.summarize(conversation.messages, None)
        first, rest = (
            conversation.messages[: conversation.split_after],
            conversation.messages[conversation.split_after :],
        )
        draft = self.summarizer.summarize(first, None)
        summary = self.ready(conversation, first, draft)
        previous = MentorConversationSummaryContext.from_summary(summary, first)
        sources = tuple(
            message
            for message in first
            if message.id in {span.message_id for span in draft.excerpts}
        )
        return self.summarizer.summarize((*sources, *rest), previous)

    @classmethod
    def ready(
        cls,
        conversation: Conversation,
        covered: tuple[MentorMessage, ...],
        draft: MentorConversationSummaryDraft,
    ) -> MentorSessionSummary:
        last = covered[-1]
        started = MentorSessionSummary.start(
            id=f'{conversation.name}:summary',
            account_id='eval-account',
            session_id=conversation.name,
            attempt_id='eval-attempt',
            version=1,
            boundary=MentorSummaryBoundary(
                message_id=last.id, created_at=last.created_at
            ),
            covered_message_count=len(covered),
            first_message_id=covered[0].id,
            now=cls.BASE_TIME,
        )
        return started.complete(draft, cls.BASE_TIME)

    # --- scoring -------------------------------------------------------------

    def score(
        self, conversation: Conversation, draft: MentorConversationSummaryDraft
    ) -> dict[str, Any]:
        by_id = {message.id: message for message in conversation.messages}
        fidelity_errors = 0
        fenced = 0
        for span in draft.excerpts:
            message = by_id.get(span.message_id)
            if (
                message is None
                or not 0 <= span.start < span.end <= len(message.content)
                or span.end - span.start > self.EXCERPT_LIMIT
                or not message.content[span.start : span.end].strip()
            ):
                fidelity_errors += 1
                continue
            if any(
                span.start < end and span.end > start
                for start, end in self.fenced(message.content)
            ):
                fenced += 1
        fidelity_errors += self.render_errors(conversation, draft, by_id)

        text = self.normalize(
            ' '.join(message.content for message in conversation.messages)
        )
        leakage = sum(1 for topic in draft.topics if self.normalize(topic) not in text)
        recalls = {
            'doubt_recall': self.excerpt_recall(
                conversation, draft, 'doubts', MentorSummaryExcerptKind.DOUBT
            ),
            'guidance_recall': self.excerpt_recall(
                conversation, draft, 'guidance', MentorSummaryExcerptKind.GUIDANCE
            ),
            'topic_recall': self.topic_recall(conversation, draft),
        }
        passed = (
            recalls['doubt_recall'] >= self.DOUBT_RECALL
            and recalls['guidance_recall'] >= self.GUIDANCE_RECALL
            and recalls['topic_recall'] >= self.TOPIC_RECALL
            and fidelity_errors == 0
            and leakage == 0
            and fenced == 0
        )
        return {
            'passed': passed,
            'failure_code': None if passed else 'summary_expectation_mismatch',
            'span_fidelity': 1.0 if fidelity_errors == 0 else 0.0,
            'leakage': leakage,
            'fenced_excerpts': fenced,
            'excerpts': len(draft.excerpts),
            'topics': len(draft.topics),
            **{key: round(value, 3) for key, value in recalls.items()},
        }

    def rendered(
        self, conversation: Conversation, draft: MentorConversationSummaryDraft
    ) -> str | None:
        try:
            summary = self.ready(conversation, conversation.messages, draft)
            return MentorConversationSummaryContext.from_summary(
                summary, conversation.messages
            ).text
        except ValueError:
            return None

    def render_errors(
        self,
        conversation: Conversation,
        draft: MentorConversationSummaryDraft,
        by_id: dict[str, MentorMessage],
    ) -> int:
        if not draft.topics and not draft.excerpts:
            return 1
        try:
            summary = self.ready(conversation, conversation.messages, draft)
            context = MentorConversationSummaryContext.from_summary(
                summary, conversation.messages
            )
        except ValueError:
            return 1
        return sum(
            1
            for span in draft.excerpts
            if by_id[span.message_id].content[span.start : span.end] not in context.text
        )

    @staticmethod
    def excerpt_recall(
        conversation: Conversation,
        draft: MentorConversationSummaryDraft,
        key: str,
        kind: MentorSummaryExcerptKind,
    ) -> float:
        wanted = conversation.expected[key]
        if not wanted:
            return 1.0
        kept = 0
        for item in wanted:
            message = conversation.messages[item['message']]
            for alternative in item['any_of']:
                start = message.content.find(alternative)
                end = start + len(alternative)
                if any(
                    span.kind is kind
                    and span.message_id == message.id
                    and min(span.end, end) - max(span.start, start)
                    >= len(alternative) / 2
                    for span in draft.excerpts
                ):
                    kept += 1
                    break
        return kept / len(wanted)

    @classmethod
    def topic_recall(
        cls, conversation: Conversation, draft: MentorConversationSummaryDraft
    ) -> float:
        wanted = conversation.expected['topics']
        if not wanted:
            return 1.0
        produced = [f' {cls.normalize(topic)} ' for topic in draft.topics]
        kept = sum(
            1
            for aliases in wanted
            if any(
                f' {cls.normalize(alias)} ' in topic
                for alias in aliases
                for topic in produced
            )
        )
        return kept / len(wanted)

    @staticmethod
    def normalize(text: str) -> str:
        decomposed = unicodedata.normalize('NFD', text.casefold())
        stripped = ''.join(c for c in decomposed if not unicodedata.combining(c))
        return ' '.join(re.sub(r'[^\w]+', ' ', stripped).split())

    @classmethod
    def fenced(cls, content: str) -> list[tuple[int, int]]:
        """Independent fence scan used only to judge the summarizer's output."""
        ranges: list[tuple[int, int]] = []
        opened: tuple[int, str] | None = None
        offset = 0
        for line in content.split('\n'):
            match = cls.FENCE.match(line)
            if match is not None:
                if opened is None:
                    opened = (offset, match.group(1)[0])
                elif match.group(1)[0] == opened[1]:
                    ranges.append((opened[0], offset + len(line)))
                    opened = None
            offset += len(line) + 1
        if opened is not None:
            ranges.append((opened[0], len(content)))
        return ranges

    @staticmethod
    def case_report(report: dict[str, Any]) -> dict[str, Any]:
        passed = bool(report.pop('passed'))
        metrics = {
            key: report.pop(key)
            for key in tuple(report)
            if key not in {'case_id', 'duration_seconds', 'failure_code'}
        }
        return {
            'case_id': report['case_id'],
            'outcome': 'passed' if passed else 'failed',
            'duration_seconds': report['duration_seconds'],
            'skipped': False,
            'scorer_passed': passed,
            'failure_code': None if passed else report['failure_code'],
            'metrics': metrics,
        }
