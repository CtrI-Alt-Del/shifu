# pyright: reportPrivateUsage=false
# ruff: noqa: SLF001
"""Registered answer workflow with local conversation summarization (real spaCy/E5)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from threading import Event, Lock, Thread, get_ident
from time import monotonic, sleep
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
from sentence_transformers import SentenceTransformer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.use_cases import (
    CancelMentorResponseUseCase,
    RemoveMentorSessionUseCase,
)
from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorSessionSummaryModel,
)
from shifu.intelligence.providers.retrieval.sentence_transformers.sentence_transformers_mentor_faq_reranker_provider import (
    SentenceTransformersMentorFaqRerankerProvider,
)
from shifu.intelligence.providers.summarization.textrank.textrank_mentor_conversation_summarizer_provider import (
    TextrankMentorConversationSummarizerProvider,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.server.agentos.mentor_attachment_test_support import (
    create_goal,
    create_session,
    submit_message_with_attachment,
    upload_ready_text_attachment,
    wait_for_session_response,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from unittest.mock import MagicMock

    from fastapi import FastAPI
    from langfuse import Langfuse

    from shifu.intelligence.ai.intelligence_workflows_registry import (
        IntelligenceWorkflowsRegistry,
        _LazyEmbeddingsProvider,
    )
    from shifu.intelligence.providers.routing.lazy_mentor_route_provider import (
        LazyMentorRouteProvider,
    )
    from shifu.intelligence.providers.routing.local_mentor_route_provider import (
        LocalMentorRouteProvider,
    )
    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)

_QUESTIONS = (
    'Por que o laço da minha lista não mostra o último item?',
    'Como eu troco um item da lista usando o índice?',
    'Qual é a diferença entre remove e pop em uma lista?',
)
_GUIDANCE = (
    'Veja quais índices range produz e compare com o tamanho da lista.',
    'Use append para adicionar um item ao final da lista.',
    'Lembre que o último índice da lista é sempre o tamanho menos um.',
)


_ALLOWED_SPAN_ATTRIBUTES = frozenset(
    {
        'module',
        'stage',
        'outcome',
        'duration_ms',
        'model_profile',
        'tokens',
        'input_tokens',
        'output_tokens',
        'cost_usd',
        'failure_code',
        'blocks',
        'observations',
        'matches',
        'inference_requests',
        'criteria',
        'messages',
        'topics',
        'excerpts',
        'expanded',
    }
)
_PADDING = 'Preciso entender ção, índice e laço da lista \U0001f600. '
_FENCED_MESSAGE = (
    'Veja este trecho:\n```python\nfor i in range(len(lista)):\n'
    '    print(lista[i])\n```\nO laço mostra todos os itens da lista.'
)


def _text_of(length: int) -> str:
    """Multi-byte text with exactly ``length`` code points."""
    text_value = (_PADDING * (length // len(_PADDING) + 1))[:length]
    assert len(text_value) == length
    assert len(text_value.encode()) > length
    return text_value


class _SummarizerGate:
    """Wrap the registry's summarizer seam to pause, act during or observe the call.

    The summarize step runs the use case in a worker thread (``asyncio.to_thread``), so
    the AgentOS event loop and the API stay responsive while the gate holds the call.
    ``during`` executes inside the call, on that worker thread, and ``thread_id``
    identifies the thread so a test can tell the step's own calls from everyone else's.
    """

    def __init__(
        self,
        *,
        hold: bool = False,
        observe: Callable[[], object] | None = None,
        during: Callable[[], object] | None = None,
    ) -> None:
        self.hold = hold
        self.entered = Event()
        self.release = Event()
        self.finished = Event()
        self.thread_id: int | None = None
        self._observe = observe
        self._during = during
        self.observations: list[object] = []

    def install(
        self,
        monkeypatch: pytest.MonkeyPatch,
        registry: IntelligenceWorkflowsRegistry,
    ) -> None:
        original = cast('Callable[..., object]', registry.summarizer.summarize)

        def gated(*args: object, **kwargs: object) -> object:
            try:
                if self._observe is not None:
                    self.observations.append(self._observe())
                self.thread_id = get_ident()
                self.entered.set()
                if self._during is not None:
                    during, self._during = self._during, None
                    during()
                if self.hold and not self.release.wait(timeout=60):
                    raise TimeoutError
                return original(*args, **kwargs)
            finally:
                if self._observe is not None:
                    self.observations.append(self._observe())
                self.finished.set()

        monkeypatch.setattr(registry.summarizer, 'summarize', gated)

    def wait_entered(self) -> None:
        assert self.entered.wait(timeout=60), 'the summarizer was never reached'


class _ObservationRecorder:
    """Langfuse client double: keeps what the real telemetry provider exports."""

    def __init__(self) -> None:
        self.observations: list[dict[str, object]] = []

    def start_observation(self, **kwargs: object) -> _ObservationRecorder:
        self.observations.append(dict(kwargs))
        return self

    def end(self) -> None:
        return None

    def metadata(self, name: str) -> list[dict[str, object]]:
        return [
            cast('dict[str, object]', item['metadata'])
            for item in self.observations
            if item.get('name') == name
        ]


class TestProcessMentorResponseSummary:
    @staticmethod
    def _seed_pairs(
        postgres_database: PostgresDatabase,
        session_id: str,
        pairs: int,
        *,
        start: datetime,
    ) -> None:
        ids = SystemIdentifierProvider()
        with Session(postgres_database.engine) as session:
            for index in range(pairs):
                learner_id, mentor_id = ids.generate(), ids.generate()
                moment = start + timedelta(seconds=2 * index)
                session.add(
                    MentorMessageModel(
                        id=learner_id,
                        session_id=session_id,
                        role='learner',
                        content=_QUESTIONS[index % len(_QUESTIONS)],
                        created_at=moment,
                        in_reply_to_message_id=None,
                    )
                )
                session.flush()
                session.add(
                    MentorMessageModel(
                        id=mentor_id,
                        session_id=session_id,
                        role='mentor',
                        content=_GUIDANCE[index % len(_GUIDANCE)],
                        created_at=moment + timedelta(seconds=1),
                        in_reply_to_message_id=learner_id,
                    )
                )
                session.flush()
            session.commit()

    @staticmethod
    def _post(
        agentos_fixture: RegisteredAgentOSFixture,
        session_id: str,
        content: str = 'Como eu percorro a lista inteira?',
    ) -> str:
        response = agentos_fixture.client.post(
            f'/intelligence/mentor-sessions/{session_id}/messages',
            json={'submission_key': str(uuid4()), 'content': content},
        )
        assert response.status_code == 202, response.text
        return cast('str', response.json()['response']['attempt_id'])

    def _send(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        session_id: str,
        content: str = 'Como eu percorro a lista inteira?',
    ) -> None:
        wait_for_session_response(
            agentos_fixture.client,
            session_id,
            self._post(agentos_fixture, session_id, content),
        )

    @staticmethod
    def _registry(
        agentos_fixture: RegisteredAgentOSFixture,
    ) -> IntelligenceWorkflowsRegistry:
        application = cast('FastAPI', agentos_fixture.client.app)
        return cast(
            'IntelligenceWorkflowsRegistry',
            application.state.intelligence_workflows_registry,  # pyright: ignore[reportAny] - Starlette app state is dynamic.
        )

    @staticmethod
    def _seed_messages(
        postgres_database: PostgresDatabase,
        session_id: str,
        contents: list[str],
        *,
        start: datetime,
    ) -> list[str]:
        """Seed answered exchanges: even positions are learner, odd are mentor replies."""
        assert len(contents) % 2 == 0
        ids = SystemIdentifierProvider()
        created: list[str] = []
        with Session(postgres_database.engine) as session:
            for index in range(0, len(contents), 2):
                learner_id, mentor_id = ids.generate(), ids.generate()
                moment = start + timedelta(milliseconds=index)
                session.add(
                    MentorMessageModel(
                        id=learner_id,
                        session_id=session_id,
                        role='learner',
                        content=contents[index],
                        created_at=moment,
                        in_reply_to_message_id=None,
                    )
                )
                session.flush()
                session.add(
                    MentorMessageModel(
                        id=mentor_id,
                        session_id=session_id,
                        role='mentor',
                        content=contents[index + 1],
                        created_at=moment + timedelta(microseconds=500),
                        in_reply_to_message_id=learner_id,
                    )
                )
                session.flush()
                created.extend((learner_id, mentor_id))
            session.commit()
        return created

    @staticmethod
    def _messages(
        postgres_database: PostgresDatabase, session_id: str
    ) -> list[tuple[str, str, str, datetime]]:
        with Session(postgres_database.engine) as session:
            return [
                (row.id, row.role, row.content, row.created_at)
                for row in session.scalars(
                    select(MentorMessageModel)
                    .where(MentorMessageModel.session_id == session_id)
                    .order_by(MentorMessageModel.created_at, MentorMessageModel.id)
                )
            ]

    @staticmethod
    def _status_progress(
        postgres_database: PostgresDatabase, session_id: str
    ) -> list[str | None]:
        with postgres_database.engine.connect() as connection:
            return [
                row[0]
                for row in connection.execute(
                    text(
                        'SELECT progress FROM intelligence_mentor_response_events '
                        "WHERE session_id = :id AND kind = 'status' "
                        'ORDER BY sequence'
                    ),
                    {'id': session_id},
                ).all()
            ]

    @staticmethod
    def _wait_for(condition: Callable[[], bool], what: str) -> None:
        deadline = monotonic() + 45
        while monotonic() < deadline:
            if condition():
                return
            sleep(0.5)
        pytest.fail(f'Timed out waiting for {what}')

    def _runs_settled(self, postgres_database: PostgresDatabase) -> bool:
        with postgres_database.engine.connect() as connection:
            statuses = connection.execute(
                text(
                    'SELECT status FROM agentos_intelligence.agentos_workflow_runs '
                    'WHERE workflow_id = :workflow_id'
                ),
                {'workflow_id': 'intelligence-process-mentor-response'},
            ).scalars()
            return all(
                str(status).lower() in {'completed', 'error', 'failed', 'cancelled'}
                for status in statuses
            )

    @staticmethod
    def _summaries(
        postgres_database: PostgresDatabase, session_id: str
    ) -> list[MentorSessionSummaryModel]:
        with Session(postgres_database.engine) as session:
            rows = session.scalars(
                select(MentorSessionSummaryModel)
                .where(MentorSessionSummaryModel.session_id == session_id)
                .order_by(MentorSessionSummaryModel.version)
            ).all()
            session.expunge_all()
            return list(rows)

    @staticmethod
    def _seed_tied_messages(
        postgres_database: PostgresDatabase,
        session_id: str,
        pairs: int,
        *,
        at: datetime,
    ) -> None:
        """Answered pairs sharing one ``created_at``; ids descend as rows are inserted.

        Insertion order is therefore the opposite of ``(created_at, id)`` order, so only
        a real id tie-break (not heap order) yields the expected sequence.
        """
        total = 2 * pairs
        with Session(postgres_database.engine) as session:
            for index in range(0, total, 2):
                learner_id = f'{9_000_000 - index:08d}{uuid4().hex[:18]}'
                mentor_id = f'{9_000_000 - index - 1:08d}{uuid4().hex[:18]}'
                assert len(learner_id) == len(mentor_id) == 26
                session.add(
                    MentorMessageModel(
                        id=learner_id,
                        session_id=session_id,
                        role='learner',
                        content=_QUESTIONS[index % len(_QUESTIONS)],
                        created_at=at,
                        in_reply_to_message_id=None,
                    )
                )
                session.flush()
                session.add(
                    MentorMessageModel(
                        id=mentor_id,
                        session_id=session_id,
                        role='mentor',
                        content=_GUIDANCE[index % len(_GUIDANCE)],
                        created_at=at,
                        in_reply_to_message_id=learner_id,
                    )
                )
                session.flush()
            session.commit()

    @staticmethod
    def _seed_ready_summary(
        postgres_database: PostgresDatabase, session_id: str, topics: list[str]
    ) -> None:
        """A ready summary with chosen Assuntos, covering only the first message."""
        with Session(postgres_database.engine) as session:
            first = session.scalars(
                select(MentorMessageModel)
                .where(MentorMessageModel.session_id == session_id)
                .order_by(MentorMessageModel.created_at, MentorMessageModel.id)
            ).first()
            account_id = session.execute(
                text(
                    'SELECT account_id FROM intelligence_mentor_response_attempts '
                    'WHERE session_id = :id'
                ),
                {'id': session_id},
            ).scalar_one()
            assert first is not None
            now = datetime.now(UTC)
            session.add(
                MentorSessionSummaryModel(
                    id=SystemIdentifierProvider().generate(),
                    account_id=str(account_id),
                    session_id=session_id,
                    attempt_id=None,
                    version=1,
                    status='ready',
                    boundary_message_id=first.id,
                    boundary_created_at=first.created_at,
                    first_message_id=first.id,
                    covered_message_count=1,
                    topics=topics,
                    excerpts=[],
                    algorithm_version='test',
                    failure_code=None,
                    created_at=now,
                    updated_at=now,
                    completed_at=now,
                )
            )
            session.commit()

    @staticmethod
    def _latest_reply(
        postgres_database: PostgresDatabase, session_id: str
    ) -> tuple[str, str]:
        """(id, content) of the Mentor reply to the latest attempt's learner message.

        Not simply the newest message: a reply may share its ``created_at`` with the
        learner message it answers, and the id then decides the order.
        """
        with postgres_database.engine.connect() as connection:
            row = connection.execute(
                text(
                    'SELECT reply.id, reply.content '
                    'FROM intelligence_mentor_response_attempts AS attempt '
                    'JOIN intelligence_mentor_messages AS reply '
                    'ON reply.in_reply_to_message_id = attempt.learner_message_id '
                    'WHERE attempt.session_id = :id '
                    'ORDER BY attempt.created_at DESC, attempt.id DESC LIMIT 1'
                ),
                {'id': session_id},
            ).one()
        return str(row[0]), str(row[1])

    def _evaluated_messages(
        self, postgres_database: PostgresDatabase, session_id: str
    ) -> list[tuple[str, str, str, datetime]]:
        """Ordered messages as they were when the latest answer run started."""
        reply_id, _ = self._latest_reply(postgres_database, session_id)
        return [
            item
            for item in self._messages(postgres_database, session_id)
            if item[0] != reply_id
        ]

    @staticmethod
    def _diagnostics(postgres_database: PostgresDatabase, session_id: str) -> str:
        """Attempts, events, messages and AgentOS runs of one conversation."""
        queries = {
            'attempts': (
                'SELECT id, status, learner_message_id, execution_owner, '
                'created_at, updated_at FROM intelligence_mentor_response_attempts '
                'WHERE session_id = :id ORDER BY created_at, id'
            ),
            'events': (
                'SELECT attempt_id, sequence, kind, status, progress, created_at '
                'FROM intelligence_mentor_response_events '
                'WHERE session_id = :id ORDER BY created_at, sequence'
            ),
            'messages': (
                'SELECT id, role, in_reply_to_message_id, created_at '
                'FROM intelligence_mentor_messages '
                'WHERE session_id = :id ORDER BY created_at, id'
            ),
            'runs': (
                'SELECT run_id, status, created_at, updated_at '
                'FROM agentos_intelligence.agentos_workflow_runs '
                'ORDER BY created_at'
            ),
        }
        lines: list[str] = []
        with postgres_database.engine.connect() as connection:
            for name, query in queries.items():
                rows = connection.execute(text(query), {'id': session_id}).all()
                lines.append(f'{name}:')
                lines.extend(f'  {tuple(row)}' for row in rows)
        return '\n'.join(lines)

    def _routed(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        recorder: _ObservationRecorder,
        session_id: str,
        content: str,
    ) -> tuple[int, str, str]:
        """Send one message: (topic expansions, Mentor reply, resolved references)."""
        recorder.observations.clear()
        self._send(agentos_fixture, session_id, content)
        try:
            self._wait_for(
                lambda: bool(recorder.metadata('intelligence.route')),
                f'the route span of {content!r}',
            )
        except pytest.fail.Exception:
            pytest.fail(
                f'No route span for {content!r}: observed '
                f'{[item.get("name") for item in recorder.observations]}, '
                f'{self._diagnostics(postgres_database, session_id)}'
            )
        (route,) = recorder.metadata('intelligence.route')
        _, reply = self._latest_reply(postgres_database, session_id)
        with postgres_database.engine.connect() as connection:
            references = connection.execute(
                text(
                    'SELECT resolved_reference_ids::text FROM '
                    'intelligence_mentor_response_attempts '
                    'WHERE session_id = :id ORDER BY created_at DESC, id DESC LIMIT 1'
                ),
                {'id': session_id},
            ).scalar_one()
        return cast('int', route['expanded']), reply, str(references)

    def _long_session(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        pairs: int,
    ) -> str:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        self._seed_pairs(
            postgres_database,
            session_id,
            pairs,
            start=datetime(2020, 1, 1, tzinfo=UTC),
        )
        return session_id

    def test_should_not_summarize_below_the_threshold(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 5)

        self._send(agentos_fixture, session_id)

        assert self._summaries(postgres_database, session_id) == []
        with postgres_database.engine.connect() as connection:
            progress = connection.execute(
                text(
                    'SELECT progress FROM intelligence_mentor_response_events '
                    "WHERE session_id = :id AND progress = 'summarize-context'"
                ),
                {'id': session_id},
            ).all()
        assert progress == []

    def test_should_summarize_with_verbatim_spans_and_close_the_progress(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)

        self._send(agentos_fixture, session_id)

        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        assert summary.topics
        assert summary.excerpts
        with Session(postgres_database.engine) as session:
            contents = {
                message.id: message.content
                for message in session.scalars(
                    select(MentorMessageModel).where(
                        MentorMessageModel.session_id == session_id
                    )
                )
            }
        for span in summary.excerpts or []:
            content = contents[cast('str', span['message_id'])]
            piece = content[cast('int', span['start']) : cast('int', span['end'])]
            assert piece.strip()
            assert len(piece) <= 280
            assert piece in _QUESTIONS + _GUIDANCE
        with postgres_database.engine.connect() as connection:
            progress = [
                row[0]
                for row in connection.execute(
                    text(
                        'SELECT progress FROM intelligence_mentor_response_events '
                        "WHERE session_id = :id AND kind = 'status' "
                        'ORDER BY sequence'
                    ),
                    {'id': session_id},
                ).all()
            ]
        opened = progress.index('summarize-context')
        assert progress[opened + 1] is None

    def test_should_anchor_the_marker_after_the_learner_message_that_triggered_it(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        question = 'Como eu percorro a lista inteira?'

        self._send(agentos_fixture, session_id, question)

        current = agentos_fixture.client.get(
            f'/intelligence/mentor-sessions/{session_id}'
        ).json()['summary']['current']
        with Session(postgres_database.engine) as session:
            messages = {
                message.id: message
                for message in session.scalars(
                    select(MentorMessageModel).where(
                        MentorMessageModel.session_id == session_id
                    )
                )
            }
        trigger = messages[current['after_message_id']]
        boundary = messages[current['boundary_message_id']]
        assert (trigger.role, trigger.content) == ('learner', question)
        assert (trigger.created_at, trigger.id) > (boundary.created_at, boundary.id)

    def test_should_fold_the_previous_summary_into_the_next_version(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        self._send(agentos_fixture, session_id)
        self._seed_pairs(
            postgres_database,
            session_id,
            12,
            start=datetime.now(UTC) - timedelta(seconds=1),
        )

        self._send(agentos_fixture, session_id)

        rows = self._summaries(postgres_database, session_id)
        assert [row.version for row in rows] == [2]
        assert rows[0].status == 'ready'

    def test_should_keep_the_answer_when_the_summarizer_is_unavailable(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def unavailable(*_args: object, **_kwargs: object) -> None:
            raise OSError

        monkeypatch.setattr(
            TextrankMentorConversationSummarizerProvider,
            'summarize',
            cast('Callable[..., object]', unavailable),
        )
        session_id = self._long_session(agentos_fixture, postgres_database, 15)

        self._send(agentos_fixture, session_id)

        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'failed'
        assert summary.failure_code == 'nlp_unavailable'
        detail = agentos_fixture.client.get(
            f'/intelligence/mentor-sessions/{session_id}'
        )
        assert detail.json()['response']['status'] == 'completed'

    def test_should_not_share_excerpts_between_conversations(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        first = self._long_session(agentos_fixture, postgres_database, 15)
        second = self._long_session(agentos_fixture, postgres_database, 15)

        self._send(agentos_fixture, first)
        self._send(agentos_fixture, second)

        with Session(postgres_database.engine) as session:
            for session_id in (first, second):
                owned = set(
                    session.scalars(
                        select(MentorMessageModel.id).where(
                            MentorMessageModel.session_id == session_id
                        )
                    )
                )
                (summary,) = self._summaries(postgres_database, session_id)
                assert {span['message_id'] for span in summary.excerpts or []} <= owned

    @pytest.mark.parametrize(('seeded', 'summarizes'), [(26, False), (28, True)])
    def test_should_summarize_only_from_twenty_unsummarized_messages(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        seeded: int,
        summarizes: bool,
    ) -> None:
        # Total = 2 initial + seeded + 1 pending (always odd: every other learner
        # message is answered), so 19 and 21 bracket the 20-message threshold; the
        # previous-boundary case below reaches the even counts.
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        self._seed_messages(
            postgres_database,
            session_id,
            [_QUESTIONS[index % len(_QUESTIONS)] for index in range(seeded)],
            start=datetime(2020, 1, 1, tzinfo=UTC),
        )

        self._send(agentos_fixture, session_id)

        rows = self._summaries(postgres_database, session_id)
        if summarizes:
            (row,) = rows
            assert row.covered_message_count == 21
            assert (
                self._status_progress(postgres_database, session_id).count(
                    'summarize-context'
                )
                == 1
            )
        else:
            assert rows == []
            assert 'summarize-context' not in self._status_progress(
                postgres_database, session_id
            )

    @pytest.mark.parametrize(
        ('last_length', 'summarizes'), [(3199, False), (3200, True)]
    )
    def test_should_summarize_only_from_sixteen_thousand_code_points(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        last_length: int,
        summarizes: bool,
    ) -> None:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        # 12 seeded messages: the 5 oldest are the unsummarized range (7 stay recent).
        long_contents = [_text_of(3200) for _ in range(4)] + [_text_of(last_length)]
        short_contents = [_QUESTIONS[index % len(_QUESTIONS)] for index in range(7)]
        self._seed_messages(
            postgres_database,
            session_id,
            [*long_contents, *short_contents],
            start=datetime(2020, 1, 1, tzinfo=UTC),
        )
        with postgres_database.engine.connect() as connection:
            characters = connection.execute(
                text(
                    'SELECT sum(char_length(content)) FROM ('
                    'SELECT content FROM intelligence_mentor_messages '
                    'WHERE session_id = :id ORDER BY created_at, id LIMIT 5) AS oldest'
                ),
                {'id': session_id},
            ).scalar_one()
        assert characters == 12_800 + last_length
        assert characters == (16_000 if summarizes else 15_999)

        self._send(agentos_fixture, session_id)

        rows = self._summaries(postgres_database, session_id)
        if summarizes:
            (row,) = rows
            assert row.covered_message_count == 5
        else:
            assert rows == []
            assert 'summarize-context' not in self._status_progress(
                postgres_database, session_id
            )

    @pytest.mark.parametrize(('extra', 'summarizes'), [(16, False), (18, True)])
    def test_should_measure_the_threshold_after_the_previous_boundary(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        extra: int,
        summarizes: bool,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        self._send(agentos_fixture, session_id)
        (first,) = self._summaries(postgres_database, session_id)
        # Messages after the boundary: 10 recent + reply + pending + extra, minus the
        # 10 newest => extra + 2 unsummarized messages (18 or 20 here).
        self._seed_messages(
            postgres_database,
            session_id,
            [_QUESTIONS[index % len(_QUESTIONS)] for index in range(extra)],
            start=datetime.now(UTC) - timedelta(seconds=1),
        )

        self._send(agentos_fixture, session_id)

        (row,) = self._summaries(postgres_database, session_id)
        if summarizes:
            assert row.version == first.version + 1
            assert row.covered_message_count == first.covered_message_count + 20
        else:
            assert row.id == first.id
            assert row.version == first.version

    def test_should_keep_messages_unchanged_and_exclude_fenced_code_from_spans(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        fenced_id, _ = self._seed_messages(
            postgres_database,
            session_id,
            [_FENCED_MESSAGE, _GUIDANCE[0]],
            start=datetime(2019, 12, 31, tzinfo=UTC),
        )
        before = self._messages(postgres_database, session_id)

        self._send(agentos_fixture, session_id)

        after = self._messages(postgres_database, session_id)
        assert after[: len(before)] == before
        assert [role for _, role, _, _ in after[len(before) :]] == ['learner', 'mentor']
        assert [item[3] for item in after] == sorted(item[3] for item in after)
        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        contents = {message_id: content for message_id, _, content, _ in after}
        covered = {message_id for message_id, *_ in after}
        fence_start = _FENCED_MESSAGE.index('```')
        fence_end = _FENCED_MESSAGE.rindex('```') + 3
        for span in summary.excerpts or []:
            message_id = cast('str', span['message_id'])
            start, end = cast('int', span['start']), cast('int', span['end'])
            content = contents[message_id]
            assert message_id in covered
            assert 0 <= start < end <= len(content)
            assert end - start <= 280
            assert content[start:end].strip()
            if message_id == fenced_id:
                assert end <= fence_start or start >= fence_end

    def test_should_send_the_summary_and_only_later_history_to_the_reviewer(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        old_ids = self._seed_messages(
            postgres_database,
            session_id,
            [
                f'{_QUESTIONS[index % len(_QUESTIONS)]} [antiga-{index}]'
                for index in range(30)
            ],
            start=datetime(2020, 1, 1, tzinfo=UTC),
        )
        batch_id, attachment_id = upload_ready_text_attachment(
            agentos_fixture.client, session_id=session_id
        )
        goal_id = create_goal(agentos_fixture.client)
        agentos_fixture.model_transport.requests.clear()
        attempt_id = submit_message_with_attachment(
            agentos_fixture.client,
            session_id=session_id,
            batch_id=batch_id,
            attachment_id=attachment_id,
            goal_id=goal_id,
        )
        wait_for_session_response(agentos_fixture.client, session_id, attempt_id)

        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        ordered = self._messages(postgres_database, session_id)
        boundary_index = next(
            index
            for index, (message_id, *_) in enumerate(ordered)
            if message_id == summary.boundary_message_id
        )
        # The reviewer runs before the new mentor answer is persisted.
        assert ordered[-1][1] == 'mentor'
        expected_history = [
            message_id for message_id, *_ in ordered[boundary_index + 1 : -1]
        ]
        assert ordered[-2][0] == expected_history[-1]
        before_boundary = {
            message_id for message_id, *_ in ordered[: boundary_index + 1]
        }
        assert expected_history
        assert before_boundary & set(old_ids)

        reviewer_requests: list[dict[str, object]] = []
        attachment_requests: list[dict[str, object]] = []
        for payload in agentos_fixture.model_transport.requests:
            schema_keys = set(
                cast(
                    'dict[str, object]',
                    agentos_fixture.model_transport._response_schema(payload).get(
                        'properties', {}
                    ),
                )
            )
            if 'request_adherence' in schema_keys:
                reviewer_requests.append(
                    agentos_fixture.model_transport._find_payload(payload, 'request')
                )
            elif {'answer', 'sources'} <= schema_keys:
                attachment_requests.append(
                    agentos_fixture.model_transport._find_payload(
                        payload, 'allowed_sources'
                    )
                )
        assert reviewer_requests
        assert attachment_requests
        for review in reviewer_requests:
            request = cast('dict[str, object]', review['request'])
            history = cast('list[dict[str, object]]', request['history'])
            assert [item['id'] for item in history] == expected_history
            serialized_history = json.dumps(history, ensure_ascii=False)
            assert not any(
                content in serialized_history
                for message_id, _, content, _ in ordered[: boundary_index + 1]
                if message_id in set(old_ids)
            )
            assert not before_boundary & {item['id'] for item in history}
            captured_summary = cast('dict[str, object]', request['summary'])
            assert captured_summary['version'] == summary.version
            assert captured_summary['topics'] == summary.topics
            assert captured_summary['first_message_id'] == summary.first_message_id
            assert len(cast('list[object]', captured_summary['excerpts'])) == len(
                summary.excerpts or []
            )
        for attachment_request in attachment_requests:
            assert set(attachment_request) == {'question', 'allowed_sources', 'chunks'}

    def test_should_retry_routing_only_for_an_elliptical_unmatched_part(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        recorder = _ObservationRecorder()
        self._registry(agentos_fixture).observability.bind(cast('Langfuse', recorder))
        short_session = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, short_session)
        long_session = self._long_session(agentos_fixture, postgres_database, 15)
        self._send(agentos_fixture, long_session)
        (summary,) = self._summaries(postgres_database, long_session)
        assert summary.topics

        def expansions(session_id: str, content: str) -> int:
            recorder.observations.clear()
            self._send(agentos_fixture, session_id, content)
            (route,) = recorder.metadata('intelligence.route')
            return cast('int', route['expanded'])

        assert expansions(short_session, 'E o índice?') == 0
        assert (
            expansions(
                long_session,
                'Quero entender detalhadamente como funcionam geradores '
                'assíncronos em Python avançado dentro de pacotes grandes',
            )
            == 0
        )
        assert expansions(long_session, 'E o índice?') == 1

    def _latest_attempt_id(
        self, postgres_database: PostgresDatabase, session_id: str
    ) -> str:
        with postgres_database.engine.connect() as connection:
            return str(
                connection.execute(
                    text(
                        'SELECT id FROM intelligence_mentor_response_attempts '
                        'WHERE session_id = :id ORDER BY created_at DESC, id DESC '
                        'LIMIT 1'
                    ),
                    {'id': session_id},
                ).scalar_one()
            )

    def test_should_discard_the_uncommitted_summary_when_the_response_is_cancelled(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        registry = self._registry(agentos_fixture)
        during: list[list[str]] = []

        def cancel_while_summarizing() -> None:
            during.append(
                [row.status for row in self._summaries(postgres_database, session_id)]
            )
            CancelMentorResponseUseCase(
                registry.database,
                registry._clock_provider,
                registry._access_provider,
            ).execute(
                agentos_fixture.account.account_id,
                session_id,
                self._latest_attempt_id(postgres_database, session_id),
                str(uuid4()),
            )

        gate = _SummarizerGate(during=cancel_while_summarizing)
        gate.install(monkeypatch, registry)
        attempt_id = self._post(agentos_fixture, session_id)

        detail = wait_for_session_response(
            agentos_fixture.client, session_id, attempt_id
        )

        assert during == [['processing']]
        assert cast('dict[str, object]', detail['response'])['status'] == 'cancelled'
        self._wait_for(
            lambda: self._runs_settled(postgres_database), 'the cancelled run to end'
        )
        assert not {
            row.status for row in self._summaries(postgres_database, session_id)
        } & {'ready', 'failed'}
        learner_before = [
            item
            for item in self._messages(postgres_database, session_id)
            if item[1] == 'learner'
        ]

        retried = agentos_fixture.client.post(
            f'/intelligence/mentor-sessions/{session_id}/responses/{attempt_id}/retry',
            json={'submission_key': str(uuid4())},
        )
        assert retried.status_code == 202, retried.text
        assert retried.json()['attempt_id'] != attempt_id
        wait_for_session_response(
            agentos_fixture.client, session_id, retried.json()['attempt_id']
        )

        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        learner_after = [
            item
            for item in self._messages(postgres_database, session_id)
            if item[1] == 'learner'
        ]
        assert learner_after == learner_before

    def test_should_remove_the_conversation_while_a_summary_is_processing(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        registry = self._registry(agentos_fixture)
        during: list[list[str]] = []

        def delete_while_summarizing() -> None:
            during.append(
                [row.status for row in self._summaries(postgres_database, session_id)]
            )
            RemoveMentorSessionUseCase(
                registry.database,
                registry._clock_provider,
                registry._access_provider,
            ).execute(agentos_fixture.account.account_id, session_id)
            during.append(
                [row.status for row in self._summaries(postgres_database, session_id)]
            )

        gate = _SummarizerGate(during=delete_while_summarizing)
        gate.install(monkeypatch, registry)
        self._post(agentos_fixture, session_id)

        assert gate.finished.wait(timeout=60)
        self._wait_for(
            lambda: self._runs_settled(postgres_database), 'the deleted run to end'
        )

        assert during == [['processing'], []]
        assert self._summaries(postgres_database, session_id) == []
        assert self._messages(postgres_database, session_id) == []
        detail = agentos_fixture.client.get(
            f'/intelligence/mentor-sessions/{session_id}'
        )
        assert detail.status_code == 404

    def test_should_not_fail_the_run_when_the_claim_phase_hits_an_operational_error(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        module = (
            'shifu.intelligence.core.use_cases.'
            'summarize_mentor_session_context_use_case'
        )
        calls: list[str] = []

        def failing_claim(*_args: object, **_kwargs: object) -> None:
            calls.append('claim')
            raise OperationalError('claim', {}, Exception('forced'))

        monkeypatch.setattr(f'{module}.start_response_attempt', failing_claim)

        self._send(agentos_fixture, session_id)

        assert calls == ['claim']
        detail = agentos_fixture.client.get(
            f'/intelligence/mentor-sessions/{session_id}'
        )
        assert detail.json()['response']['status'] == 'completed'
        assert self._summaries(postgres_database, session_id) == []
        assert 'summarize-context' not in self._status_progress(
            postgres_database, session_id
        )

    def test_should_share_the_spacy_and_embeddings_instances_with_the_router(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        self._send(agentos_fixture, session_id)
        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        registry = self._registry(agentos_fixture)

        router = cast('LazyMentorRouteProvider', registry.route_provider)
        local = cast('LocalMentorRouteProvider', router._provider)
        summarizer = cast(
            'TextrankMentorConversationSummarizerProvider', registry.summarizer
        )
        assert local is not None
        assert local._embeddings is registry._shared_embeddings
        assert summarizer._embeddings is registry._shared_embeddings
        assert local._preprocessor is registry._shared_preprocessor
        assert summarizer._preprocessor is registry._shared_preprocessor
        assert router._embeddings is registry._shared_embeddings
        assert router._preprocessor is registry._shared_preprocessor
        loaded = cast('_LazyEmbeddingsProvider', registry._shared_embeddings)
        assert loaded._provider is not None

    def test_should_discard_the_summary_when_the_access_revision_changes(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        registry = self._registry(agentos_fixture)
        gate = _SummarizerGate(hold=True)
        gate.install(monkeypatch, registry)
        attempt_id = self._post(agentos_fixture, session_id)
        gate.wait_entered()
        revoked = [True]

        def revision_changed(*_args: object, **_kwargs: object) -> None:
            # The first access check made by the summarize step itself after the
            # summarizer returned: same worker thread, call already finished.
            if revoked and gate.finished.is_set() and get_ident() == gate.thread_id:
                revoked.pop()
                raise ServiceUnavailableError

        access = cast('MagicMock', registry._access_provider)
        access.assert_current.side_effect = revision_changed

        gate.release.set()
        wait_for_session_response(agentos_fixture.client, session_id, attempt_id)

        assert revoked == []
        assert not {
            row.status for row in self._summaries(postgres_database, session_id)
        } & {'ready', 'failed'}

    def test_should_reject_a_second_ready_or_processing_summary_row(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        ids = SystemIdentifierProvider()
        with Session(postgres_database.engine) as session:
            message = session.scalars(
                select(MentorMessageModel)
                .where(MentorMessageModel.session_id == session_id)
                .order_by(MentorMessageModel.created_at)
            ).first()
            attempt_row = session.execute(
                text(
                    'SELECT id, account_id FROM intelligence_mentor_response_attempts '
                    'WHERE session_id = :id'
                ),
                {'id': session_id},
            ).first()
            assert message is not None
            assert attempt_row is not None
            attempt_id, account_id = str(attempt_row[0]), str(attempt_row[1])
            boundary = (message.id, message.created_at)

        def build(status: str, version: int) -> MentorSessionSummaryModel:
            now = datetime.now(UTC)
            return MentorSessionSummaryModel(
                id=ids.generate(),
                account_id=account_id,
                session_id=session_id,
                attempt_id=attempt_id if status == 'processing' else None,
                version=version,
                status=status,
                boundary_message_id=boundary[0],
                boundary_created_at=boundary[1],
                first_message_id=boundary[0],
                covered_message_count=1,
                topics=[] if status == 'ready' else None,
                excerpts=[] if status == 'ready' else None,
                algorithm_version='test' if status == 'ready' else None,
                failure_code=None,
                created_at=now,
                updated_at=now,
                completed_at=now if status == 'ready' else None,
            )

        with Session(postgres_database.engine) as session:
            session.add_all([build('ready', 1), build('processing', 2)])
            session.commit()
        for status, version in (('ready', 3), ('processing', 4)):
            with Session(postgres_database.engine) as session:
                session.add(build(status, version))
                with pytest.raises(IntegrityError):
                    session.commit()
        assert [
            row.status for row in self._summaries(postgres_database, session_id)
        ] == [
            'ready',
            'processing',
        ]

    def test_should_not_use_a_model_or_record_usage_for_summarization(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        registry = self._registry(agentos_fixture)
        access = cast('MagicMock', registry._access_provider)

        def observe() -> object:
            with postgres_database.engine.connect() as connection:
                usage = connection.execute(
                    text(
                        'SELECT usage_calls::text FROM '
                        'intelligence_mentor_response_attempts '
                        'WHERE session_id = :id ORDER BY created_at, id'
                    ),
                    {'id': session_id},
                ).all()
            return (
                len(agentos_fixture.model_transport.requests),
                access.record_usage.call_count,
                [tuple(row) for row in usage],
            )

        gate = _SummarizerGate(hold=False, observe=observe)
        gate.install(monkeypatch, registry)

        self._send(agentos_fixture, session_id)

        assert gate.finished.is_set()
        started, ended = gate.observations
        assert started == ended
        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        with postgres_database.engine.connect() as connection:
            usage_calls = connection.execute(
                text(
                    'SELECT usage_calls::text FROM '
                    'intelligence_mentor_response_attempts WHERE session_id = :id'
                ),
                {'id': session_id},
            ).scalars()
            assert all('summar' not in str(value).lower() for value in usage_calls)

    def test_should_export_only_allowlisted_telemetry_attributes(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        recorder = _ObservationRecorder()
        self._registry(agentos_fixture).observability.bind(cast('Langfuse', recorder))
        session_id = self._long_session(agentos_fixture, postgres_database, 15)

        self._send(agentos_fixture, session_id)

        (summarize,) = recorder.metadata('intelligence.summarize')
        assert summarize['stage'] == 'summarize'
        assert summarize['outcome'] == 'ready'
        assert summarize['model_profile'] == 'local'
        assert summarize['messages'] == 23
        assert 'failure_code' not in summarize
        assert recorder.observations
        for observation in recorder.observations:
            metadata = cast('dict[str, object]', observation['metadata'])
            assert set(metadata) <= _ALLOWED_SPAN_ATTRIBUTES
            assert all(
                isinstance(value, (str, int, float)) for value in metadata.values()
            )
        exported = json.dumps(recorder.observations, default=str, ensure_ascii=False)
        for private in (*_QUESTIONS, *_GUIDANCE, session_id):
            assert private not in exported

    def test_should_export_the_closed_failure_code_and_recover_on_a_later_crossing(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        recorder = _ObservationRecorder()
        registry = self._registry(agentos_fixture)
        registry.observability.bind(cast('Langfuse', recorder))
        session_id = self._long_session(agentos_fixture, postgres_database, 15)

        def unavailable(*_args: object, **_kwargs: object) -> None:
            raise OSError

        with monkeypatch.context() as scenario:
            scenario.setattr(registry.summarizer, 'summarize', unavailable)
            self._send(agentos_fixture, session_id)
        (failure,) = recorder.metadata('intelligence.summarize')
        assert failure['outcome'] == 'failed'
        assert failure['failure_code'] == 'nlp_unavailable'
        assert set(failure) <= _ALLOWED_SPAN_ATTRIBUTES
        (failed,) = self._summaries(postgres_database, session_id)
        assert failed.status == 'failed'

        self._send(agentos_fixture, session_id)

        (recovered,) = self._summaries(postgres_database, session_id)
        assert recovered.status == 'ready'
        assert recovered.version == failed.version + 1

    @pytest.mark.parametrize(
        ('target', 'summarizes'), [(15_999, False), (16_000, True)]
    )
    def test_should_measure_sixteen_thousand_code_points_after_the_previous_boundary(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        target: int,
        summarizes: bool,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        self._send(agentos_fixture, session_id)
        (first,) = self._summaries(postgres_database, session_id)
        boundary = (first.boundary_created_at, first.boundary_message_id)
        # Four long messages placed right after the boundary become the oldest
        # post-boundary messages; with the two older recent ones the range is six
        # messages (the 10 newest stay recent), far below the count threshold.
        with postgres_database.engine.connect() as connection:
            older = (
                connection.execute(
                    text(
                        'SELECT char_length(content) FROM intelligence_mentor_messages '
                        'WHERE session_id = :id '
                        'AND (created_at, id) > (:created_at, :message_id) '
                        'ORDER BY created_at, id LIMIT 2'
                    ),
                    {
                        'id': session_id,
                        'created_at': boundary[0],
                        'message_id': boundary[1],
                    },
                )
                .scalars()
                .all()
            )
        assert len(older) == 2
        lengths = [3500, 3500, 3500, target - sum(older) - 3 * 3500]
        assert all(length > 0 for length in lengths)
        self._seed_messages(
            postgres_database,
            session_id,
            [_text_of(length) for length in lengths],
            start=boundary[0] + timedelta(milliseconds=1),
        )
        with postgres_database.engine.connect() as connection:
            measured = connection.execute(
                text(
                    'SELECT sum(char_length(content)), count(*) FROM ('
                    'SELECT content FROM intelligence_mentor_messages '
                    'WHERE session_id = :id '
                    'AND (created_at, id) > (:created_at, :message_id) '
                    'ORDER BY created_at, id LIMIT 6) AS oldest'
                ),
                {
                    'id': session_id,
                    'created_at': boundary[0],
                    'message_id': boundary[1],
                },
            ).one()
        assert tuple(measured) == (target, 6)

        self._send(agentos_fixture, session_id)

        (row,) = self._summaries(postgres_database, session_id)
        if summarizes:
            assert row.version == first.version + 1
            assert row.covered_message_count == first.covered_message_count + 6
        else:
            assert row.id == first.id

    def test_should_break_created_at_ties_by_message_id_for_every_boundary(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        tie = datetime(2020, 1, 1, tzinfo=UTC)
        self._seed_tied_messages(postgres_database, session_id, 14, at=tie)

        self._send(agentos_fixture, session_id)

        ordered = self._messages(postgres_database, session_id)
        evaluated = self._evaluated_messages(postgres_database, session_id)
        boundary_index = len(evaluated) - 11
        (first,) = self._summaries(postgres_database, session_id)
        # The boundary sits in the middle of the tied group, with equal timestamps
        # on both sides, so only the id decides which tied messages are covered.
        assert (
            evaluated[boundary_index - 1][3]
            == evaluated[boundary_index][3]
            == evaluated[boundary_index + 1][3]
            == tie
        )
        assert first.boundary_message_id == evaluated[boundary_index][0]
        assert first.first_message_id == ordered[0][0]
        assert first.covered_message_count == boundary_index + 1
        covered = {message_id for message_id, *_ in evaluated[: boundary_index + 1]}
        assert {span['message_id'] for span in first.excerpts or []} <= covered

        # The 7 tied messages after the boundary (larger ids) belong to the next range:
        # 10 recent + reply + 18 new + pending - 10 recent = exactly 20 unsummarized.
        self._seed_messages(
            postgres_database,
            session_id,
            [_QUESTIONS[index % len(_QUESTIONS)] for index in range(18)],
            # Past the tied group but before every message of the first run.
            start=datetime(2020, 1, 2, tzinfo=UTC),
        )

        self._send(agentos_fixture, session_id)

        (second,) = self._summaries(postgres_database, session_id)
        evaluated_again = self._evaluated_messages(postgres_database, session_id)
        assert second.version == first.version + 1
        assert second.boundary_message_id == evaluated_again[-11][0]
        assert second.covered_message_count == len(evaluated_again) - 10
        assert second.covered_message_count - first.covered_message_count == 20

    def test_should_keep_the_committed_summary_when_the_response_is_cancelled_later(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        registry = self._registry(agentos_fixture)
        route_provider = registry.route_provider
        original = cast('Callable[..., object]', route_provider.route)
        during: list[list[str]] = []

        def cancel_while_routing(*args: object, **kwargs: object) -> object:
            # Routing runs in the prepare phase, after the summary was committed.
            if not during:
                during.append(
                    [
                        row.status
                        for row in self._summaries(postgres_database, session_id)
                    ]
                )
                CancelMentorResponseUseCase(
                    registry.database,
                    registry._clock_provider,
                    registry._access_provider,
                ).execute(
                    agentos_fixture.account.account_id,
                    session_id,
                    self._latest_attempt_id(postgres_database, session_id),
                    str(uuid4()),
                )
            return original(*args, **kwargs)

        monkeypatch.setattr(route_provider, 'route', cancel_while_routing)
        attempt_id = self._post(agentos_fixture, session_id)

        detail = wait_for_session_response(
            agentos_fixture.client, session_id, attempt_id
        )

        assert during == [['ready']]
        assert cast('dict[str, object]', detail['response'])['status'] == 'cancelled'
        self._wait_for(
            lambda: self._runs_settled(postgres_database), 'the cancelled run to end'
        )
        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        assert summary.version == 1
        read = agentos_fixture.client.get(
            f'/intelligence/mentor-sessions/{session_id}/summary'
        )
        assert read.status_code == 200, read.text
        body = cast('dict[str, object]', read.json())
        assert body['version'] == 1
        assert cast('str', body['text']).strip()
        assert cast('str', body['first_message_id']) == summary.first_message_id

    def test_should_produce_the_same_summary_for_the_same_input(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        first = self._long_session(agentos_fixture, postgres_database, 15)
        second = self._long_session(agentos_fixture, postgres_database, 15)
        self._send(agentos_fixture, first)
        self._send(agentos_fixture, second)

        def shape(session_id: str) -> tuple[object, ...]:
            (row,) = self._summaries(postgres_database, session_id)
            positions = [
                message_id
                for message_id, *_ in self._messages(postgres_database, session_id)
            ]
            rendered = agentos_fixture.client.get(
                f'/intelligence/mentor-sessions/{session_id}/summary'
            )
            assert rendered.status_code == 200, rendered.text
            return (
                row.topics,
                [
                    (
                        positions.index(cast('str', span['message_id'])),
                        span['start'],
                        span['end'],
                        span['kind'],
                    )
                    for span in row.excerpts or []
                ],
                row.algorithm_version,
                row.covered_message_count,
                rendered.json()['text'],
            )

        assert shape(first) == shape(second)

    def test_should_serialize_embedding_calls_shared_by_the_router_and_the_summarizer(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._long_session(agentos_fixture, postgres_database, 15)
        registry = self._registry(agentos_fixture)
        embeddings = cast('_LazyEmbeddingsProvider', registry._shared_embeddings)
        probe = ('Como eu percorro a lista inteira com o índice?',)
        baseline = embeddings.embed_queries(probe)[0]
        assert embeddings._provider is not None
        original = cast('Callable[..., object]', SentenceTransformer.encode)
        guard = Lock()
        state = {'active': 0, 'peak': 0}
        threads: set[int] = set()

        def watched(self: object, *args: object, **kwargs: object) -> object:
            with guard:
                state['active'] += 1
                state['peak'] = max(state['peak'], state['active'])
                threads.add(get_ident())
            try:
                sleep(0.01)
                return original(self, *args, **kwargs)
            finally:
                with guard:
                    state['active'] -= 1

        monkeypatch.setattr(SentenceTransformer, 'encode', watched)
        stop = Event()
        failures: list[BaseException] = []

        def router_like() -> None:
            # What the router does on the event-loop thread: query embeddings.
            while not stop.is_set():
                try:
                    vector = embeddings.embed_queries(probe)[0]
                    drift = max(
                        abs(a - b) for a, b in zip(vector, baseline, strict=True)
                    )
                    assert drift < 1e-5
                except BaseException as error:  # noqa: BLE001 - reported below
                    failures.append(error)
                    return

        worker = Thread(target=router_like)
        worker.start()
        try:
            self._send(agentos_fixture, session_id)
        finally:
            stop.set()
            worker.join(timeout=60)

        assert failures == []
        assert not worker.is_alive()
        assert state['peak'] == 1
        assert len(threads) >= 2
        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        detail = agentos_fixture.client.get(
            f'/intelligence/mentor-sessions/{session_id}'
        )
        assert detail.json()['response']['status'] == 'completed'

    def test_should_answer_from_the_faq_when_the_topics_retry_passes_the_unchanged_gates(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # CI prepares only the embeddings model, never the cross-encoder, so the
        # reranker judgement is a content-based double: it accepts only a query that
        # actually names the tuple topic. Embeddings, retrieval and the router are real.
        def judge(
            self: SentenceTransformersMentorFaqRerankerProvider,
            content: str,
            documents: tuple[str, ...],
        ) -> tuple[float, ...]:
            relevant = 'tupla' in content.casefold()
            return tuple(
                10.0 if relevant and 'tupla' in document.casefold() else -10.0
                for document in documents
            )

        monkeypatch.setattr(
            SentenceTransformersMentorFaqRerankerProvider, 'score', judge
        )
        recorder = _ObservationRecorder()
        self._registry(agentos_fixture).observability.bind(cast('Langfuse', recorder))
        answer = next(
            item.answer
            for item in MentorResources().answers
            if item.id == 'python_tuples'
        )
        agentos_fixture.model_transport.requests.clear()
        outcomes: dict[str, tuple[int, str, str]] = {}
        for name, topics in (
            ('plain', None),
            ('related', ['tupla em Python']),
            ('unrelated', ['receita de bolo de chocolate']),
        ):
            session_id = create_session(agentos_fixture.client)
            wait_for_session_response(agentos_fixture.client, session_id)
            if topics is not None:
                self._seed_ready_summary(postgres_database, session_id, topics)
            outcomes[name] = self._routed(
                agentos_fixture, postgres_database, recorder, session_id, 'E o que é?'
            )

        # Without Assuntos the part has no answer of its own; no retry is attempted.
        assert outcomes['plain'][0] == 0
        assert answer not in outcomes['plain'][1]
        # A related Assunto lets the single retry reach the indexed FAQ through the
        # unchanged retrieval gates ...
        assert outcomes['related'][0] == 1
        assert answer in outcomes['related'][1]
        # ... while an unrelated one is retried once and still fails the same gates.
        assert outcomes['unrelated'][0] == 1
        assert outcomes['unrelated'][1] == outcomes['plain'][1]
        assert agentos_fixture.model_transport.requests == []

    def test_should_not_change_references_or_clarifications_when_a_part_has_an_explicit_reference(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        recorder = _ObservationRecorder()
        self._registry(agentos_fixture).observability.bind(cast('Langfuse', recorder))
        goal_id = create_goal(agentos_fixture.client)
        outcomes: dict[tuple[str, str], tuple[int, str, str]] = {}
        # The hint comes first: later explicit references give the conversation a
        # Goal, which is what removes the clarification.
        contents = {
            'hint': 'Me dê uma dica',
            'explicit': f'Qual é o estado do objetivo {goal_id}?',
            'explicit-elliptical': f'E o que é? Sobre o objetivo {goal_id}',
        }
        for name, topics in (
            ('plain', None),
            ('unrelated', ['receita de bolo de chocolate']),
            ('related', ['tupla em Python']),
        ):
            session_id = create_session(agentos_fixture.client)
            wait_for_session_response(agentos_fixture.client, session_id)
            if topics is not None:
                self._seed_ready_summary(postgres_database, session_id, topics)
            for label, content in contents.items():
                outcomes[name, label] = self._routed(
                    agentos_fixture, postgres_database, recorder, session_id, content
                )

        for label in contents:
            plain = outcomes['plain', label]
            assert plain[0] == 0, label
            for name in ('unrelated', 'related'):
                # Whatever the Assuntos, the resolved references are the same ...
                assert outcomes[name, label][2] == plain[2], (name, label)
            # ... and when the retry finds nothing new the whole reply is unchanged.
            assert outcomes['unrelated', label][1] == plain[1], label
        assert goal_id in outcomes['plain', 'explicit'][2]
        # The elliptical part next to an explicit reference may use the retry,
        # but never to change what was referenced.
        assert outcomes['unrelated', 'explicit-elliptical'][0] >= 1
        assert 'Qual Objetivo e Habilidade' in outcomes['plain', 'hint'][1]
        for name in ('unrelated', 'related'):
            assert outcomes[name, 'hint'][1] == outcomes['plain', 'hint'][1]

    def test_should_bound_the_candidate_sentences_of_a_very_long_range(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        # Twelve 3,200-code-point messages hold far more sentences than the cap.
        self._seed_messages(
            postgres_database,
            session_id,
            [
                *(_text_of(3200) for _ in range(12)),
                *(_QUESTIONS[index % len(_QUESTIONS)] for index in range(16)),
            ],
            start=datetime(2020, 1, 1, tzinfo=UTC),
        )

        self._send(agentos_fixture, session_id)

        (summary,) = self._summaries(postgres_database, session_id)
        assert summary.status == 'ready'
        cap = TextrankMentorConversationSummarizerProvider.MAX_CANDIDATES
        phrases = TextrankMentorConversationSummarizerProvider.MAX_PHRASES
        assert summary.algorithm_version is not None
        assert summary.algorithm_version.endswith(f'+cap{cap}.{phrases}')
        assert summary.topics
        with Session(postgres_database.engine) as session:
            contents = {
                message.id: message.content
                for message in session.scalars(
                    select(MentorMessageModel).where(
                        MentorMessageModel.session_id == session_id
                    )
                )
            }
        for span in summary.excerpts or []:
            content = contents[cast('str', span['message_id'])]
            piece = content[cast('int', span['start']) : cast('int', span['end'])]
            assert piece.strip()
            assert len(piece) <= 280
