from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from importlib.resources import files
from time import monotonic
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

from evals.common import CaseDefinition, select_definitions
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

if TYPE_CHECKING:
    from collections.abc import Callable


class _Summarizer(Protocol):
    def summarize(
        self,
        messages: tuple[MentorMessage, ...],
        previous: MentorConversationSummaryContext | None,
    ) -> MentorConversationSummaryDraft: ...


_DATASET = 'mentor-summary-evaluation.json'
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_EXCERPT_LIMIT = 280
_FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')


@cache
def _dataset() -> dict[str, Any]:
    raw = files('shifu.intelligence.ai.data').joinpath(_DATASET).read_text('utf-8')
    return json.loads(raw)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize('NFD', text.casefold())
    stripped = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^\w]+', ' ', stripped).split())


def _fenced(content: str) -> list[tuple[int, int]]:
    """Independent fence scan used only to judge the summarizer's output."""
    ranges: list[tuple[int, int]] = []
    opened: tuple[int, str] | None = None
    offset = 0
    for line in content.split('\n'):
        match = _FENCE.match(line)
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


@dataclass(frozen=True)
class _Case:
    name: str
    messages: tuple[MentorMessage, ...]
    split_after: int | None
    expected: dict[str, Any]


def _build_case(entry: dict[str, Any]) -> _Case:
    name = str(entry['name'])
    messages = tuple(
        MentorMessage(
            id=f'{name}:{index:03d}',
            session_id=name,
            role=MentorMessageRole(message['role']),
            content=message['content'],
            created_at=_BASE_TIME + timedelta(minutes=index),
            in_reply_to_message_id=None,
        )
        for index, message in enumerate(entry['messages'])
    )
    return _Case(name, messages, entry.get('split_after'), entry['expected'])


class SummarizeMentorSessionEval:
    """Gate the local extractive summary on a versioned synthetic pt-BR dataset."""

    selector = 'summarize-mentor-session'
    workflow_id = 'intelligence-summarize-mentor-session'
    prompt_revision = 'textrank-mmr-e5-v1'
    DOUBT_RECALL: ClassVar[float] = 0.80
    GUIDANCE_RECALL: ClassVar[float] = 0.80
    TOPIC_RECALL: ClassVar[float] = 0.70

    def __init__(
        self,
        summarizer: _Summarizer,
        *,
        mode: str,
        model_profile: str,
        close_resources: Callable[[], None] | None = None,
    ) -> None:
        self._summarizer = summarizer
        self._mode = mode
        self._model_profile = model_profile
        self._close_resources = close_resources

    @property
    def dataset_revision(self) -> str:
        return str(_dataset()['dataset_revision'])

    @classmethod
    def definitions(cls) -> tuple[CaseDefinition, ...]:
        return tuple(
            CaseDefinition(
                name=str(entry['name']),
                tags=tuple(entry['tags']),
                input=f'{len(entry["messages"])} synthetic pt-BR messages',
                expected=entry['expected'],
            )
            for entry in _dataset()['cases']
        )

    def run(self, name: str | None = None, tag: str | None = None) -> dict[str, Any]:
        definitions = self.definitions()
        selected = select_definitions(definitions, name=name, tag=tag)
        entries = {str(entry['name']): entry for entry in _dataset()['cases']}
        cases = [_build_case(entries[definition.name]) for definition in selected]
        reports: list[dict[str, Any]] = []
        drafts: dict[str, MentorConversationSummaryDraft] = {}
        for case in cases:
            started = monotonic()
            try:
                drafts[case.name] = self._summarize(case)
                report = self._score(case, drafts[case.name])
                # RF-02: the same input yields the same draft and rendered text.
                repeated = self._summarize(case)
                mismatch = int(
                    repeated != drafts[case.name]
                    or self._rendered(case, repeated)
                    != self._rendered(case, drafts[case.name])
                )
                report['nondeterministic'] = mismatch
                if mismatch:
                    report['passed'] = False
                    report['failure_code'] = 'nondeterministic_output'
            except Exception:  # noqa: BLE001 - provider errors can contain conversation text.
                report = {'passed': False, 'failure_code': 'summarizer_unavailable'}
            report['case_id'] = case.name
            report['duration_seconds'] = round(max(monotonic() - started, 0.0), 3)
            reports.append(report)

        # Leakage and independence: replaying the cases in reverse order, after every
        # other conversation went through the same instance, must change nothing.
        for case in reversed(cases):
            report = next(item for item in reports if item['case_id'] == case.name)
            if case.name not in drafts:
                continue
            try:
                replay = self._summarize(case)
            except Exception:  # noqa: BLE001 - see above.
                replay = None
            if replay != drafts[case.name]:
                report['leakage'] = report.get('leakage', 0) + 1
                report['passed'] = False
                report['failure_code'] = 'cross_case_leakage'

        case_reports = [self._case_report(report) for report in reports]
        successful = bool(case_reports) and all(
            item['outcome'] == 'passed' for item in case_reports
        )
        return {
            'workflow': self.selector,
            'status': 'passed' if successful else 'failed',
            'partial': len(selected) < len(definitions),
            'mode': self._mode,
            'model_profile': self._model_profile,
            'dataset_revision': self.dataset_revision,
            'prompt_revision': self.prompt_revision,
            'selected_case_ids': [definition.name for definition in selected],
            'counts': {
                'selected': len(case_reports),
                'passed': sum(item['outcome'] == 'passed' for item in case_reports),
                'failed': sum(item['outcome'] == 'failed' for item in case_reports),
                'skipped': 0,
            },
            'cases': case_reports,
        }

    def close(self) -> None:
        if self._close_resources is not None:
            self._close_resources()

    # --- execution -----------------------------------------------------------

    def _summarize(self, case: _Case) -> MentorConversationSummaryDraft:
        if case.split_after is None:
            return self._summarizer.summarize(case.messages, None)
        first, rest = (
            case.messages[: case.split_after],
            case.messages[case.split_after :],
        )
        draft = self._summarizer.summarize(first, None)
        summary = self._ready(case, first, draft)
        previous = MentorConversationSummaryContext.from_summary(summary, first)
        sources = tuple(
            message
            for message in first
            if message.id in {span.message_id for span in draft.excerpts}
        )
        return self._summarizer.summarize((*sources, *rest), previous)

    @staticmethod
    def _ready(
        case: _Case,
        covered: tuple[MentorMessage, ...],
        draft: MentorConversationSummaryDraft,
    ) -> MentorSessionSummary:
        last = covered[-1]
        started = MentorSessionSummary.start(
            id=f'{case.name}:summary',
            account_id='eval-account',
            session_id=case.name,
            attempt_id='eval-attempt',
            version=1,
            boundary=MentorSummaryBoundary(
                message_id=last.id, created_at=last.created_at
            ),
            covered_message_count=len(covered),
            first_message_id=covered[0].id,
            now=_BASE_TIME,
        )
        return started.complete(draft, _BASE_TIME)

    # --- scoring -------------------------------------------------------------

    def _score(
        self, case: _Case, draft: MentorConversationSummaryDraft
    ) -> dict[str, Any]:
        by_id = {message.id: message for message in case.messages}
        fidelity_errors = 0
        fenced = 0
        for span in draft.excerpts:
            message = by_id.get(span.message_id)
            if (
                message is None
                or not 0 <= span.start < span.end <= len(message.content)
                or span.end - span.start > _EXCERPT_LIMIT
                or not message.content[span.start : span.end].strip()
            ):
                fidelity_errors += 1
                continue
            if any(
                span.start < end and span.end > start
                for start, end in _fenced(message.content)
            ):
                fenced += 1
        fidelity_errors += self._render_errors(case, draft, by_id)

        text = _normalize(' '.join(message.content for message in case.messages))
        leakage = sum(1 for topic in draft.topics if _normalize(topic) not in text)
        recalls = {
            'doubt_recall': self._excerpt_recall(
                case, draft, by_id, 'doubts', MentorSummaryExcerptKind.DOUBT
            ),
            'guidance_recall': self._excerpt_recall(
                case, draft, by_id, 'guidance', MentorSummaryExcerptKind.GUIDANCE
            ),
            'topic_recall': self._topic_recall(case, draft),
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

    def _rendered(
        self, case: _Case, draft: MentorConversationSummaryDraft
    ) -> str | None:
        try:
            summary = self._ready(case, case.messages, draft)
            return MentorConversationSummaryContext.from_summary(
                summary, case.messages
            ).text
        except ValueError:
            return None

    def _render_errors(
        self,
        case: _Case,
        draft: MentorConversationSummaryDraft,
        by_id: dict[str, MentorMessage],
    ) -> int:
        if not draft.topics and not draft.excerpts:
            return 1
        try:
            summary = self._ready(case, case.messages, draft)
            context = MentorConversationSummaryContext.from_summary(
                summary, case.messages
            )
        except ValueError:
            return 1
        return sum(
            1
            for span in draft.excerpts
            if by_id[span.message_id].content[span.start : span.end] not in context.text
        )

    @staticmethod
    def _excerpt_recall(
        case: _Case,
        draft: MentorConversationSummaryDraft,
        by_id: dict[str, MentorMessage],
        key: str,
        kind: MentorSummaryExcerptKind,
    ) -> float:
        wanted = case.expected[key]
        if not wanted:
            return 1.0
        kept = 0
        for item in wanted:
            message = case.messages[item['message']]
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

    @staticmethod
    def _topic_recall(case: _Case, draft: MentorConversationSummaryDraft) -> float:
        wanted = case.expected['topics']
        if not wanted:
            return 1.0
        produced = [f' {_normalize(topic)} ' for topic in draft.topics]
        kept = sum(
            1
            for aliases in wanted
            if any(
                f' {_normalize(alias)} ' in topic
                for alias in aliases
                for topic in produced
            )
        )
        return kept / len(wanted)

    @staticmethod
    def _case_report(report: dict[str, Any]) -> dict[str, Any]:
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
