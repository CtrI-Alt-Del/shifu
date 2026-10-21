# pyright: reportPrivateUsage=false
# ruff: noqa: SLF001
"""Registered answer workflow with learner memories (real spaCy and scikit-learn)."""

from __future__ import annotations

import logging
import os
from threading import Event
from time import monotonic, sleep
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from shifu.intelligence.core.use_cases import (
    CancelMentorResponseUseCase,
    RemoveLearnerMemoryUseCase,
    RemoveMentorSessionUseCase,
)
from shifu.intelligence.database.sqlalchemy.models import (
    LearnerMemoryChangeModel,
    LearnerMemoryModel,
    LearnerMemoryOriginModel,
    MentorMessageModel,
    MentorResponseAttemptModel,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from tests.intelligence.server.agentos.mentor_attachment_test_support import (
    create_goal,
    create_session,
    upload_ready_text_attachment,
    wait_for_session_response,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI

    from shifu.intelligence.ai.intelligence_workflows_registry import (
        IntelligenceWorkflowsRegistry,
    )
    from shifu.intelligence.core.domain.structures import LearnerMemoryAnalysis
    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)

_ACKNOWLEDGEMENT = 'Anotado. Vou considerar isso nas próximas explicações.'
_ABSTENTION = 'Ainda não encontrei uma resposta local confiável'
_PREFERENCE = 'explanation_preference'


class TestProcessMentorResponseMemories:
    # --- helpers --------------------------------------------------------------

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
    def _post(
        agentos_fixture: RegisteredAgentOSFixture,
        session_id: str,
        content: str,
        **extra: object,
    ) -> str:
        response = agentos_fixture.client.post(
            f'/intelligence/mentor-sessions/{session_id}/messages',
            json={'submission_key': str(uuid4()), 'content': content, **extra},
        )
        assert response.status_code == 202, response.text
        return cast('str', response.json()['response']['attempt_id'])

    def _send(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        session_id: str,
        content: str,
    ) -> dict[str, object]:
        return wait_for_session_response(
            agentos_fixture.client,
            session_id,
            self._post(agentos_fixture, session_id, content),
        )

    def _new_session(self, agentos_fixture: RegisteredAgentOSFixture) -> str:
        session_id = create_session(agentos_fixture.client)
        wait_for_session_response(agentos_fixture.client, session_id)
        agentos_fixture.model_transport.requests.clear()
        return session_id

    @staticmethod
    def _memories(postgres_database: PostgresDatabase) -> list[LearnerMemoryModel]:
        with Session(postgres_database.engine) as session:
            rows = session.scalars(
                select(LearnerMemoryModel).order_by(
                    LearnerMemoryModel.created_at, LearnerMemoryModel.id
                )
            ).all()
            session.expunge_all()
            return list(rows)

    @staticmethod
    def _changes(postgres_database: PostgresDatabase) -> list[LearnerMemoryChangeModel]:
        with Session(postgres_database.engine) as session:
            rows = session.scalars(
                select(LearnerMemoryChangeModel).order_by(
                    LearnerMemoryChangeModel.created_at, LearnerMemoryChangeModel.id
                )
            ).all()
            session.expunge_all()
            return list(rows)

    @staticmethod
    def _origins(postgres_database: PostgresDatabase) -> list[LearnerMemoryOriginModel]:
        with Session(postgres_database.engine) as session:
            rows = session.scalars(select(LearnerMemoryOriginModel)).all()
            session.expunge_all()
            return list(rows)

    @staticmethod
    def _receipt(
        postgres_database: PostgresDatabase, message_id: str
    ) -> tuple[bool, bool]:
        """``(analyzed, statement_only)`` of the learner message."""
        with Session(postgres_database.engine) as session:
            message = session.get(MentorMessageModel, message_id)
            assert message is not None
            return message.memory_analyzed_at is not None, message.memory_statement_only

    @staticmethod
    def _reply(postgres_database: PostgresDatabase, learner_message_id: str) -> str:
        with Session(postgres_database.engine) as session:
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_message_id
                )
            )
            assert reply is not None
            return reply.content

    def _answer(
        self,
        postgres_database: PostgresDatabase,
        detail: dict[str, object],
    ) -> tuple[str, str]:
        snapshot = cast('dict[str, object]', detail['response'])
        learner_id = cast('str', snapshot['learner_message_id'])
        return learner_id, self._reply(postgres_database, learner_id)

    @staticmethod
    def _wait_for(condition: Callable[[], bool], what: str) -> None:
        deadline = monotonic() + 45
        while monotonic() < deadline:
            if condition():
                return
            sleep(0.5)
        pytest.fail(f'Timed out waiting for {what}')

    @staticmethod
    def _agentos_records(postgres_database: PostgresDatabase) -> str:
        """Every row of every table of the private AgentOS schema, as text."""
        with postgres_database.engine.connect() as connection:
            tables = (
                connection.execute(
                    text(
                        'SELECT table_name FROM information_schema.tables '
                        "WHERE table_schema = 'agentos_intelligence' "
                        "AND table_type = 'BASE TABLE'"
                    )
                )
                .scalars()
                .all()
            )
            assert 'agentos_workflow_runs' in tables
            return ' '.join(
                str(row)
                for table in tables
                for row in connection.execute(
                    text(f'SELECT t::text FROM agentos_intelligence."{table}" t')  # noqa: S608 - names come from information_schema, not input.
                ).scalars()
            )

    @staticmethod
    def _runs_settled(postgres_database: PostgresDatabase) -> bool:
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
    def _latest_attempt_id(postgres_database: PostgresDatabase, session_id: str) -> str:
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

    def _during_analysis(
        self,
        monkeypatch: pytest.MonkeyPatch,
        registry: IntelligenceWorkflowsRegistry,
        during: Callable[[], object],
    ) -> Event:
        """Run ``during`` inside the first analysis, on the step's worker thread."""
        analyzer = registry.learner_memory_analyzer
        original = analyzer.analyze
        finished = Event()
        pending = [during]

        def gated(content: str) -> LearnerMemoryAnalysis:
            try:
                if pending:
                    pending.pop()()
                return original(content)
            finally:
                finished.set()

        monkeypatch.setattr(analyzer, 'analyze', gated)
        return finished

    def _count_analyses(
        self, monkeypatch: pytest.MonkeyPatch, registry: IntelligenceWorkflowsRegistry
    ) -> list[str]:
        analyzer = registry.learner_memory_analyzer
        original = analyzer.analyze
        calls: list[str] = []

        def counted(content: str) -> LearnerMemoryAnalysis:
            calls.append('analyze')
            return original(content)

        monkeypatch.setattr(analyzer, 'analyze', counted)
        return calls

    def _attachment_message(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        session_id: str,
        content: str,
    ) -> str:
        batch_id, attachment_id = upload_ready_text_attachment(
            agentos_fixture.client, session_id=session_id
        )
        return self._post(
            agentos_fixture,
            session_id,
            content,
            context_hint={'goal_id': create_goal(agentos_fixture.client)},
            attachment_batch_id=batch_id,
            attachment_ids=[attachment_id],
        )

    @staticmethod
    def _captured_requests(
        agentos_fixture: RegisteredAgentOSFixture,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        transport = agentos_fixture.model_transport
        attachment_requests: list[dict[str, object]] = []
        reviewer_requests: list[dict[str, object]] = []
        for payload in transport.requests:
            schema_keys = set(
                cast(
                    'dict[str, object]',
                    transport._response_schema(payload).get('properties', {}),
                )
            )
            if 'request_adherence' in schema_keys:
                reviewer_requests.append(transport._find_payload(payload, 'request'))
            elif {'answer', 'sources'} <= schema_keys:
                attachment_requests.append(
                    transport._find_payload(payload, 'allowed_sources')
                )
        return attachment_requests, reviewer_requests

    # --- creation, update and routing --------------------------------------------

    def test_should_create_one_memory_and_answer_statement_only_messages_with_anotado(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._new_session(agentos_fixture)

        detail = self._send(
            agentos_fixture, session_id, 'Prefiro exemplos curtos em JavaScript.'
        )

        learner_id, reply = self._answer(postgres_database, detail)
        assert cast('dict[str, object]', detail['response'])['status'] == 'completed'
        assert reply == _ACKNOWLEDGEMENT
        (memory,) = self._memories(postgres_database)
        assert memory.category == _PREFERENCE
        assert memory.content == 'Prefiro exemplos curtos em JavaScript.'
        assert memory.version == 1
        assert memory.account_id == agentos_fixture.account.account_id
        (change,) = self._changes(postgres_database)
        assert change.kind == 'created'
        assert change.memory_id == memory.id
        assert change.message_id == learner_id
        assert change.content == memory.content
        assert change.previous_content is None
        (origin,) = self._origins(postgres_database)
        assert origin.memory_id == memory.id
        assert origin.message_id == learner_id
        assert self._receipt(postgres_database, learner_id) == (True, True)
        items = cast('list[dict[str, object]]', detail['memory_items'])
        assert [(item['kind'], item['memory_id']) for item in items] == [
            ('created', memory.id)
        ]
        # The extraction is local: no model call, usage receipt or quota effect.
        assert agentos_fixture.model_transport.requests == []
        with Session(postgres_database.engine) as session:
            attempt = session.get(
                MentorResponseAttemptModel,
                cast('dict[str, object]', detail['response'])['attempt_id'],
            )
            assert attempt is not None
            assert attempt.usage_calls in (None, [])
            assert attempt.generation_keys == []

    def test_should_update_a_contradicted_preference_and_keep_the_previous_text(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        self._send(agentos_fixture, session_id, 'Prefiro exemplos em Python.')
        self._send(agentos_fixture, session_id, 'Sei Python.')

        detail = self._send(
            agentos_fixture, session_id, 'Agora prefiro exemplos em JavaScript.'
        )
        self._send(agentos_fixture, session_id, 'Prefiro explicações curtas.')

        memories = {m.content: m for m in self._memories(postgres_database)}
        assert set(memories) == {
            'Prefiro exemplos em JavaScript.',
            'Sei Python.',
            'Prefiro explicações curtas.',
        }
        updated = memories['Prefiro exemplos em JavaScript.']
        assert updated.version == 2
        assert memories['Sei Python.'].version == 1
        assert memories['Prefiro explicações curtas.'].version == 1
        updates = [c for c in self._changes(postgres_database) if c.kind == 'updated']
        assert [(c.memory_id, c.previous_content, c.content) for c in updates] == [
            (
                updated.id,
                'Prefiro exemplos em Python.',
                'Prefiro exemplos em JavaScript.',
            )
        ]
        assert (
            len(
                [
                    o
                    for o in self._origins(postgres_database)
                    if o.memory_id == updated.id
                ]
            )
            == 2
        )
        _, reply = self._answer(postgres_database, detail)
        assert reply == _ACKNOWLEDGEMENT

    def test_should_classify_only_eligible_sentences_and_keep_routing_for_questions(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._new_session(agentos_fixture)

        mixed = self._send(
            agentos_fixture,
            session_id,
            'Prefiro explicações com diagramas. Como organizar meus estudos?',
        )
        question = self._send(
            agentos_fixture, session_id, 'O que é uma lista em Python?'
        )
        third_person = self._send(
            agentos_fixture, session_id, 'A Maria prefere exemplos curtos.'
        )
        oversized = self._send(
            agentos_fixture, session_id, 'Prefiro ' + 'exemplos curtos e diretos ' * 14
        )

        (memory,) = self._memories(postgres_database)
        assert memory.content == 'Prefiro explicações com diagramas.'
        mixed_id, mixed_reply = self._answer(postgres_database, mixed)
        assert mixed_reply.strip()
        assert mixed_reply != _ACKNOWLEDGEMENT
        assert self._receipt(postgres_database, mixed_id) == (True, False)
        for other in (question, third_person, oversized):
            learner_id, reply = self._answer(postgres_database, other)
            assert reply != _ACKNOWLEDGEMENT
            assert self._receipt(postgres_database, learner_id) == (True, False)
        assert len(self._changes(postgres_database)) == 1
        assert agentos_fixture.model_transport.requests == []

    def test_should_keep_local_answers_unchanged_when_memories_exist(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        self._send(agentos_fixture, session_id, 'Prefiro respostas curtas.')

        detail = self._send(agentos_fixture, session_id, 'O que é uma lista em Python?')

        _, reply = self._answer(postgres_database, detail)
        assert reply.endswith('começando em zero.')
        assert 'Anotado' not in reply
        assert agentos_fixture.model_transport.requests == []

    def test_should_keep_memory_text_out_of_agentos_run_records(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        self._send(
            agentos_fixture, session_id, 'Tenho dificuldade com ponteiros duplos.'
        )

        with postgres_database.engine.connect() as connection:
            runs = connection.execute(
                text(
                    'SELECT run_data::text FROM '
                    'agentos_intelligence.agentos_workflow_runs'
                )
            ).scalars()
            serialized = ' '.join(str(item) for item in runs)
        assert serialized
        assert 'ponteiros' not in serialized
        assert 'Tenho dificuldade' not in serialized

    # --- failures, retries and fences ----------------------------------------------

    def test_should_not_analyze_again_when_a_failed_answer_is_retried(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        calls = self._count_analyses(monkeypatch, self._registry(agentos_fixture))
        agentos_fixture.model_transport.reject_attachment_source = True
        attempt_id = self._attachment_message(
            agentos_fixture,
            session_id,
            'Prefiro exemplos curtos em JavaScript. Explique o documento anexado.',
        )

        failed = wait_for_session_response(
            agentos_fixture.client, session_id, attempt_id
        )

        assert cast('dict[str, object]', failed['response'])['status'] == 'failed'
        (memory,) = self._memories(postgres_database)
        assert memory.content == 'Prefiro exemplos curtos em JavaScript.'
        assert calls == ['analyze']
        assert len(cast('list[object]', failed['memory_items'])) == 1

        agentos_fixture.model_transport.reject_attachment_source = False
        retry = agentos_fixture.client.post(
            f'/intelligence/mentor-sessions/{session_id}/responses/{attempt_id}/retry',
            json={'submission_key': str(uuid4())},
        )
        assert retry.status_code == 202, retry.text
        completed = wait_for_session_response(
            agentos_fixture.client, session_id, retry.json()['attempt_id']
        )

        assert cast('dict[str, object]', completed['response'])['status'] == 'completed'
        assert calls == ['analyze']
        assert len(self._memories(postgres_database)) == 1
        assert len(self._changes(postgres_database)) == 1
        assert len(cast('list[object]', completed['memory_items'])) == 1

    def test_should_complete_the_answer_and_write_nothing_when_the_analyzer_fails(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        analyzer = self._registry(agentos_fixture).learner_memory_analyzer

        def broken(_content: str) -> LearnerMemoryAnalysis:
            raise RuntimeError('texto privado do aprendiz')

        monkeypatch.setattr(analyzer, 'analyze', broken)

        detail = self._send(
            agentos_fixture, session_id, 'Prefiro exemplos curtos em JavaScript.'
        )

        learner_id, reply = self._answer(postgres_database, detail)
        assert cast('dict[str, object]', detail['response'])['status'] == 'completed'
        assert _ABSTENTION in reply
        assert self._memories(postgres_database) == []
        assert self._changes(postgres_database) == []
        assert self._receipt(postgres_database, learner_id) == (False, False)

    def test_should_leave_no_memory_when_the_conversation_is_deleted_during_the_step(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        registry = self._registry(agentos_fixture)

        def delete_conversation() -> None:
            RemoveMentorSessionUseCase(
                registry.database, registry._clock_provider, registry._access_provider
            ).execute(agentos_fixture.account.account_id, session_id)

        finished = self._during_analysis(monkeypatch, registry, delete_conversation)
        self._post(agentos_fixture, session_id, 'Prefiro exemplos curtos.')

        assert finished.wait(timeout=60)
        self._wait_for(
            lambda: self._runs_settled(postgres_database), 'the deleted run to end'
        )
        assert self._memories(postgres_database) == []
        assert self._changes(postgres_database) == []
        assert self._origins(postgres_database) == []

    def test_should_leave_no_memory_or_receipt_when_the_attempt_is_cancelled_during_the_step(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        registry = self._registry(agentos_fixture)

        def cancel() -> None:
            CancelMentorResponseUseCase(
                registry.database, registry._clock_provider, registry._access_provider
            ).execute(
                agentos_fixture.account.account_id,
                session_id,
                self._latest_attempt_id(postgres_database, session_id),
                str(uuid4()),
            )

        finished = self._during_analysis(monkeypatch, registry, cancel)
        attempt_id = self._post(agentos_fixture, session_id, 'Prefiro exemplos curtos.')

        detail = wait_for_session_response(
            agentos_fixture.client, session_id, attempt_id
        )
        assert finished.wait(timeout=60)
        assert cast('dict[str, object]', detail['response'])['status'] == 'cancelled'
        learner_id = cast(
            'str', cast('dict[str, object]', detail['response'])['learner_message_id']
        )
        assert self._memories(postgres_database) == []
        assert self._changes(postgres_database) == []
        assert self._receipt(postgres_database, learner_id) == (False, False)

    def test_should_leave_no_memory_when_access_is_revoked_during_the_step(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        registry = self._registry(agentos_fixture)
        access = registry._access_provider

        def revoke() -> None:
            access.assert_current.side_effect = ServiceUnavailableError()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType] - the fixture injects an autospec.

        finished = self._during_analysis(monkeypatch, registry, revoke)
        self._post(agentos_fixture, session_id, 'Prefiro exemplos curtos.')

        assert finished.wait(timeout=60)
        self._wait_for(
            lambda: self._runs_settled(postgres_database), 'the revoked run to end'
        )
        access.assert_current.side_effect = None  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType] - the fixture injects an autospec.
        assert self._memories(postgres_database) == []
        assert self._changes(postgres_database) == []

    def test_should_not_recreate_a_memory_deleted_while_an_older_message_was_pending(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        session_id = self._new_session(agentos_fixture)
        self._send(agentos_fixture, session_id, 'Prefiro exemplos em Python.')
        (existing,) = self._memories(postgres_database)
        registry = self._registry(agentos_fixture)

        def delete_memory() -> None:
            RemoveLearnerMemoryUseCase(
                registry.database, registry._access_provider, registry._clock_provider
            ).execute(agentos_fixture.account.account_id, existing.id)

        finished = self._during_analysis(monkeypatch, registry, delete_memory)
        pending = self._send(
            agentos_fixture, session_id, 'Prefiro exemplos curtos em JavaScript.'
        )

        assert finished.is_set()
        pending_id, pending_reply = self._answer(postgres_database, pending)
        assert self._memories(postgres_database) == []
        assert pending_reply != _ACKNOWLEDGEMENT
        assert self._receipt(postgres_database, pending_id) == (True, False)
        erased = [c for c in self._changes(postgres_database) if c.memory_id is None]
        assert [(c.content, c.previous_content) for c in erased] == [(None, None)]

        newer = self._send(
            agentos_fixture, session_id, 'Prefiro exemplos curtos em JavaScript.'
        )
        (created,) = self._memories(postgres_database)
        assert created.content == 'Prefiro exemplos curtos em JavaScript.'
        assert created.id != existing.id
        assert self._answer(postgres_database, newer)[1] == _ACKNOWLEDGEMENT

    # --- relevant memories in attachment answers -------------------------------------

    def test_should_send_only_relevant_labeled_memories_to_the_attachment_answer_and_reviewer(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
        postgres_database: PostgresDatabase,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        caplog.set_level(logging.DEBUG)
        session_id = self._new_session(agentos_fixture)
        for statement in (
            'Prefiro exemplos em Python.',
            'Tenho dificuldade com frações equivalentes.',
            'Quero aprender violão.',
            'Sei Python.',
        ):
            self._send(agentos_fixture, session_id, statement)
        assert len(self._memories(postgres_database)) == 4
        agentos_fixture.model_transport.requests.clear()

        attempt_id = self._attachment_message(
            agentos_fixture,
            session_id,
            'Explique o documento anexado sobre frações equivalentes.',
        )
        detail = wait_for_session_response(
            agentos_fixture.client, session_id, attempt_id
        )

        assert cast('dict[str, object]', detail['response'])['status'] == 'completed'
        attachment_requests, reviewer_requests = self._captured_requests(
            agentos_fixture
        )
        assert attachment_requests and reviewer_requests
        expected = {
            ('explanation_preference', 'Prefiro exemplos em Python.'),
            ('recurring_difficulty', 'Tenho dificuldade com frações equivalentes.'),
        }
        for request in attachment_requests:
            declarations = cast('list[dict[str, str]]', request['learner_memories'])
            assert {
                (item['category'], item['content']) for item in declarations
            } == expected
            assert {item['label'] for item in declarations} == {
                'declaração do aprendiz, não domínio comprovado'
            }
        for review in reviewer_requests:
            reviewed = cast('dict[str, object]', review['request'])
            memories = cast('list[dict[str, str]]', reviewed['memories'])
            assert {
                (item['category'], item['content']) for item in memories
            } == expected
        # The declarations travel only in the in-memory handoff to the model request:
        # no AgentOS table (runs, steps, sessions, any text column) and no log keeps them.
        records = self._agentos_records(postgres_database)
        for _, content in expected:
            assert content not in records
            assert content not in caplog.text

    def test_should_keep_attachment_requests_identical_without_memories(
        self,
        agentos_fixture: RegisteredAgentOSFixture,
    ) -> None:
        session_id = self._new_session(agentos_fixture)

        attempt_id = self._attachment_message(
            agentos_fixture, session_id, 'Explique o documento anexado.'
        )
        wait_for_session_response(agentos_fixture.client, session_id, attempt_id)

        attachment_requests, reviewer_requests = self._captured_requests(
            agentos_fixture
        )
        assert attachment_requests and reviewer_requests
        for request in attachment_requests:
            assert set(request) == {'question', 'allowed_sources', 'chunks'}
        for review in reviewer_requests:
            assert cast('dict[str, object]', review['request'])['memories'] == []
