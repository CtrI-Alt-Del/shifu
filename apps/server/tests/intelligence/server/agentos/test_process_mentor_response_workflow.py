from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import pytest
from agno.agent import Agent
from agno.run.agent import RunOutput
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorEmbeddingVersionModel,
    MentorIndexedEmbeddingModel,
    MentorResponseAttemptModel,
)
from shifu.intelligence.core.use_cases.publish_mentor_response_block_use_case import (
    PublishMentorResponseBlockUseCase,
)
from shifu.shared.messaging.agentos.agentos_handoff_store import AgentOSHandoffStore
from tests.intelligence.server.agentos.mentor_attachment_test_support import (
    ATTACHMENT_TEXT,
    MODEL_ANSWER,
    create_goal,
    create_session,
    submit_message_with_attachment,
    upload_ready_text_attachment,
    wait_for_session_response,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from shifu.intelligence.core.domain.structures import MentorResponseBlock
    from shifu.shared.core.domain.structures import MentorContextSnapshot
    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)


def test_registered_runtime_keeps_indexed_faq_and_abstention_local(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    def assert_local_response(
        question: str,
        *,
        expected_text: str | None = None,
        endswith: bool = False,
    ) -> str:
        created = agentos_fixture.client.post(
            '/intelligence/mentor-sessions',
            json={'submission_key': str(uuid4()), 'first_message': question},
        )
        assert created.status_code == 201, created.text
        session_id = cast('str', created.json()['session']['id'])
        detail = wait_for_session_response(agentos_fixture.client, session_id)
        snapshot = cast('dict[str, object]', detail['response'])
        with postgres_database.engine.connect() as connection:
            process_runs = connection.execute(
                text(
                    'SELECT status, run_data::text FROM '
                    'agentos_intelligence.agentos_workflow_runs '
                    'WHERE workflow_id = :workflow_id'
                ),
                {'workflow_id': 'intelligence-process-mentor-response'},
            ).all()
        assert snapshot['status'] == 'completed', json.dumps(
            {
                'response': snapshot,
                'model_profiles': agentos_fixture.model_transport.model_profiles,
                'model_requests': agentos_fixture.model_transport.requests,
                'process_runs': [
                    {
                        'status': str(status),
                        'run_data_head': str(run_data)[:700],
                        'run_data_tail': str(run_data)[-1100:],
                    }
                    for status, run_data in process_runs
                ],
            },
            ensure_ascii=False,
        )

        attempt_id = cast('str', snapshot['attempt_id'])
        learner_message_id = cast('str', snapshot['learner_message_id'])
        with Session(postgres_database.engine) as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            learner_message = session.get(MentorMessageModel, learner_message_id)
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_message_id
                )
            )

        assert attempt is not None and attempt.status == 'completed'
        assert attempt.generation_keys == []
        assert attempt.usage_calls == []
        assert learner_message is not None and learner_message.content == question
        assert reply is not None and reply.content.strip()
        if expected_text is not None:
            if endswith:
                assert reply.content.endswith(expected_text)
            else:
                assert expected_text in reply.content
        assert agentos_fixture.model_transport.requests == []
        return reply.content

    def index_snapshot() -> tuple[str, tuple[str, ...]]:
        with Session(postgres_database.engine) as session:
            active_versions = session.scalars(
                select(MentorEmbeddingVersionModel).where(
                    MentorEmbeddingVersionModel.active.is_(True)
                )
            ).all()
            assert len(active_versions) == 1
            rows = session.scalars(
                select(MentorIndexedEmbeddingModel).order_by(
                    MentorIndexedEmbeddingModel.version,
                    MentorIndexedEmbeddingModel.corpus,
                    MentorIndexedEmbeddingModel.reference_id,
                    MentorIndexedEmbeddingModel.variation_key,
                )
            ).all()
            vectors = tuple(
                json.dumps(
                    [
                        row.version,
                        row.corpus,
                        row.reference_id,
                        row.variation_key,
                        [float(value) for value in row.vector],
                    ],
                    separators=(',', ':'),
                )
                for row in rows
            )
            return active_versions[0].version, vectors

    index_before = index_snapshot()
    assert_local_response(
        'O que é uma lista em Python?',
        expected_text=(
            'Uma lista em Python reúne elementos em uma sequência que pode ser alterada. '
            'Os elementos têm posições, chamadas índices, começando em zero.'
        ),
        endswith=True,
    )
    assert_local_response(
        'Como organizar meus estudos?',
        expected_text='Ainda não encontrei uma resposta local confiável',
    )

    assert index_snapshot() == index_before

    with Session(postgres_database.engine) as session:
        removed = session.execute(
            delete(MentorIndexedEmbeddingModel).where(
                MentorIndexedEmbeddingModel.version == index_before[0],
                MentorIndexedEmbeddingModel.corpus == 'answers',
            )
        )
        assert removed.rowcount > 0  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType] - Verify affected answer-vector rows.
        session.commit()
    damaged = index_snapshot()
    assert_local_response(
        'O que é uma lista em Python?',
        expected_text='Ainda não encontrei uma resposta local confiável',
    )
    assert index_snapshot() == damaged


def test_registered_runtime_processes_and_persists_attachment_answer(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_detail['response'])
    assert initial_snapshot['status'] == 'completed', json.dumps(
        {
            'session_id': session_id,
            'initial_response': initial_snapshot,
            'model_profiles': agentos_fixture.model_transport.model_profiles,
            'model_request_count': len(agentos_fixture.model_transport.requests),
        },
        ensure_ascii=False,
    )

    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    goal_id = create_goal(agentos_fixture.client)
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=goal_id,
    )

    detail = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id=attempt_id,
    )
    snapshot = cast('dict[str, object]', detail['response'])
    with postgres_database.engine.connect() as connection:
        process_runs = connection.execute(
            text(
                'SELECT status, run_data::text FROM '
                'agentos_intelligence.agentos_workflow_runs '
                'WHERE workflow_id = :workflow_id'
            ),
            {'workflow_id': 'intelligence-process-mentor-response'},
        ).all()
        preparation_runs = connection.execute(
            text(
                'SELECT status FROM agentos_intelligence.agentos_workflow_runs '
                'WHERE workflow_id = :workflow_id'
            ),
            {'workflow_id': 'intelligence-prepare-mentor-attachment'},
        ).all()
        progress_steps = (
            connection.execute(
                text(
                    'SELECT progress FROM intelligence_mentor_response_events '
                    'WHERE attempt_id = :attempt_id AND progress IS NOT NULL '
                    'ORDER BY sequence'
                ),
                {'attempt_id': attempt_id},
            )
            .scalars()
            .all()
        )
        learning_run_count = connection.execute(
            text('SELECT count(*) FROM agentos_learning.agentos_workflow_runs')
        ).scalar_one()

    assert process_runs
    assert preparation_runs
    assert learning_run_count == 0
    assert any(str(status).lower() == 'completed' for status, _data in process_runs), (
        f'Native response run statuses: {[status for status, _data in process_runs]}'
    )
    public_source_ids = [
        str(cast('dict[str, object]', source_value)['chunk_id'])
        for block_value in cast('list[object]', snapshot['blocks'])
        for source_value in cast(
            'list[object]', cast('dict[str, object]', block_value)['sources']
        )
    ]
    messages_page = cast('dict[str, object]', detail['messages'])
    messages = cast('list[object]', messages_page['items'])
    learner_message_id = snapshot['learner_message_id']
    learner_message = next(
        cast('dict[str, object]', item)
        for item in messages
        if cast('dict[str, object]', item)['id'] == learner_message_id
    )
    learner_attachments = cast('list[object]', learner_message['attachments'])
    assert progress_steps == ['write-answer', 'review-answer'], json.dumps(
        {
            'session_id': session_id,
            'batch_id': batch_id,
            'attachment_id': attachment_id,
            'attempt_id': attempt_id,
            'response': snapshot,
            'workflow_run_statuses': [status for status, _data in process_runs],
            'progress_steps': progress_steps,
            'public_attachment_ids': [
                cast('dict[str, object]', item)['attachment_id']
                for item in learner_attachments
            ],
            'public_source_ids': public_source_ids,
            'model_profiles': agentos_fixture.model_transport.model_profiles,
            'model_request_count': len(agentos_fixture.model_transport.requests),
        },
        ensure_ascii=False,
    )
    assert snapshot['attempt_id'] == attempt_id
    assert agentos_fixture.model_transport.model_profiles.count('primary') >= 2

    assert 'reviewer' in agentos_fixture.model_transport.model_profiles
    assert 'vision' in agentos_fixture.model_transport.model_profiles
    assert any(
        cast('dict[str, object]', item)['attachment_id'] == attachment_id
        for item in learner_attachments
    )
    captured_model_requests = json.dumps(
        agentos_fixture.model_transport.requests,
        ensure_ascii=False,
    )
    assert agentos_fixture.model_transport.requests, (
        'Registered attempt completed without a model request; '
        f'run statuses: {[status for status, _data in process_runs]}, '
        f'attempt: {snapshot["attempt_id"]}, progress: {snapshot["progress"]}, '
        f'public source IDs: {public_source_ids}'
    )
    assert ATTACHMENT_TEXT in captured_model_requests
    assert 'allowed_sources' in captured_model_requests
    assert snapshot['status'] == 'completed'
    assert snapshot['failure_code'] is None
    blocks = cast('list[object]', snapshot['blocks'])
    attachment_answer_blocks = [
        cast('dict[str, object]', block)
        for block in blocks
        if any(
            cast('dict[str, object]', source)['attachment_id'] == attachment_id
            for source in cast(
                'list[object]', cast('dict[str, object]', block)['sources']
            )
        )
    ]
    assert len(attachment_answer_blocks) == 1, json.dumps(
        {
            'session_id': session_id,
            'goal_id': goal_id,
            'attempt_id': attempt_id,
            'response': snapshot,
            'progress_steps': progress_steps,
            'workflow_run_statuses': [status for status, _data in process_runs],
            'model_profiles': agentos_fixture.model_transport.model_profiles,
            'model_request_count': len(agentos_fixture.model_transport.requests),
            'captured_attachment_text': ATTACHMENT_TEXT in captured_model_requests,
            'captured_allowed_sources': 'allowed_sources' in captured_model_requests,
        },
        ensure_ascii=False,
    )
    attachment_answer = attachment_answer_blocks[0]
    assert attachment_answer['content'] == MODEL_ANSWER, json.dumps(
        {
            'session_id': session_id,
            'goal_id': goal_id,
            'attempt_id': attempt_id,
            'response': snapshot,
            'progress_steps': progress_steps,
            'workflow_run_statuses': [status for status, _data in process_runs],
            'model_profiles': agentos_fixture.model_transport.model_profiles,
            'model_request_count': len(agentos_fixture.model_transport.requests),
            'captured_attachment_text': ATTACHMENT_TEXT in captured_model_requests,
            'captured_allowed_sources': 'allowed_sources' in captured_model_requests,
        },
        ensure_ascii=False,
    )
    sources = cast('list[object]', attachment_answer['sources'])
    source = cast('dict[str, object]', sources[0])
    assert set(source) == {'attachment_id', 'chunk_id', 'page_number', 'locator'}
    assert source['attachment_id'] == attachment_id
    assert source['page_number'] is None
    assert str(source['locator']).startswith('chars:')
    assert str(source['chunk_id']) in captured_model_requests
    assert all(
        ATTACHMENT_TEXT not in str(data) and MODEL_ANSWER not in str(data)
        for _status, data in process_runs
    )
    assert learning_run_count == 0


def _review_output(content: object) -> dict[str, object] | None:
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except ValueError:
            return None
    elif isinstance(content, BaseModel):
        content = content.model_dump(mode='python')
    if not isinstance(content, dict) or 'fact_fidelity' not in content:
        return None
    return cast('dict[str, object]', content)


def _reject_first_review(
    original_run: Callable[..., RunOutput], calls: list[int]
) -> Callable[..., RunOutput]:
    def run_with_one_rejection(
        agent: Agent, *args: object, **kwargs: object
    ) -> RunOutput:
        response = original_run(agent, *args, **kwargs)
        output = _review_output(response.content)
        if output is None:
            return response
        calls[0] += 1
        if calls[0] != 1:
            return response
        return RunOutput(
            content={
                **output,
                'fact_fidelity': {
                    'choice': 'rejected',
                    'feedback': 'Revise a resposta para manter a precisão.',
                },
            },
            metrics=response.metrics,
            status=response.status,
        )

    return run_with_one_rejection


def test_registered_response_replays_rejected_review_after_handoff_loss(
    agentos_fixture: RegisteredAgentOSFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_detail['response'])
    assert initial_snapshot['status'] == 'completed'

    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )

    reviewer_calls = [0]
    original_run = cast('Callable[..., RunOutput]', Agent.run)
    monkeypatch.setattr(
        Agent,
        'run',
        _reject_first_review(original_run, reviewer_calls),
    )

    original_read = AgentOSHandoffStore.read_input
    process_handoff_reads = 0

    def read_once_after_loss(
        store: AgentOSHandoffStore,
        reference: str,
        *,
        capability: str,
    ) -> object:
        nonlocal process_handoff_reads
        if capability == 'process-mentor-response':
            process_handoff_reads += 1
            if process_handoff_reads == 2:
                raise KeyError('simulated expired retry handoff')
        return original_read(store, reference, capability=capability)

    monkeypatch.setattr(AgentOSHandoffStore, 'read_input', read_once_after_loss)
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=create_goal(agentos_fixture.client),
    )

    detail = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id=attempt_id,
    )
    snapshot = cast('dict[str, object]', detail['response'])
    assert process_handoff_reads >= 3
    assert reviewer_calls[0] >= 2
    assert snapshot['status'] == 'completed'
    assert snapshot['attempt_id'] == attempt_id


def test_registered_runtime_fails_closed_on_unknown_attachment_source(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    assert (
        cast('dict[str, object]', initial_detail['response'])['status'] == 'completed'
    )
    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    goal_id = create_goal(agentos_fixture.client)
    agentos_fixture.model_transport.reject_attachment_source = True

    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=goal_id,
    )
    detail = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id=attempt_id,
    )
    snapshot = cast('dict[str, object]', detail['response'])
    assert snapshot['status'] == 'failed'
    assert snapshot['failure_code'] == 'service_unavailable'
    assert snapshot['attempt_id'] == attempt_id

    learner_message_id = cast('str', snapshot['learner_message_id'])
    with Session(postgres_database.engine) as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        reply = session.scalar(
            select(MentorMessageModel).where(
                MentorMessageModel.in_reply_to_message_id == learner_message_id
            )
        )
    with postgres_database.engine.connect() as connection:
        process_runs = (
            connection.execute(
                text(
                    'SELECT run_data::text FROM agentos_intelligence.agentos_workflow_runs '
                    'WHERE workflow_id = :workflow_id'
                ),
                {'workflow_id': 'intelligence-process-mentor-response'},
            )
            .scalars()
            .all()
        )

    assert attempt is not None and attempt.status == 'failed'
    assert reply is None
    assert process_runs
    assert all(
        ATTACHMENT_TEXT not in run_data
        and MODEL_ANSWER not in run_data
        and 'Z' * 26 not in run_data
        for run_data in process_runs
    )


def test_registered_response_fails_closed_when_reviewer_provider_raises(
    agentos_fixture: RegisteredAgentOSFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_detail['response'])
    assert initial_snapshot['status'] == 'completed'
    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    original_run = cast('Callable[..., RunOutput]', Agent.run)
    reviewer_calls = 0

    def fail_reviewer_run(agent: Agent, *args: object, **kwargs: object) -> RunOutput:
        nonlocal reviewer_calls
        if getattr(agent, 'name', None) == 'Mentor Reviewer':
            reviewer_calls += 1
            raise RuntimeError('controlled reviewer provider failure')
        return original_run(agent, *args, **kwargs)

    monkeypatch.setattr(
        Agent,
        'run',
        cast('Callable[..., RunOutput]', fail_reviewer_run),
    )
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=create_goal(agentos_fixture.client),
    )

    detail = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id=attempt_id,
    )
    snapshot = cast('dict[str, object]', detail['response'])
    assert reviewer_calls == 1
    assert snapshot['status'] == 'failed'
    assert snapshot['failure_code'] == 'service_unavailable'
    serialized_detail = json.dumps(detail, ensure_ascii=False)
    assert 'Essas informações estão indisponíveis no momento.' in serialized_detail
    assert MODEL_ANSWER not in serialized_detail
    assert ATTACHMENT_TEXT not in serialized_detail


def test_registered_response_fails_closed_when_generated_block_is_not_published(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    initial_snapshot = cast('dict[str, object]', initial_detail['response'])
    assert initial_snapshot['status'] == 'completed'
    batch_id, attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )

    original_execute = PublishMentorResponseBlockUseCase.execute
    rejected_blocks = 0

    def reject_generated_block(
        use_case: PublishMentorResponseBlockUseCase,
        attempt_id: str,
        execution_owner: str,
        block: MentorResponseBlock,
        expected_context: MentorContextSnapshot,
    ) -> bool:
        nonlocal rejected_blocks
        if block.block_key == 'generated-0':
            rejected_blocks += 1
            return False
        return original_execute(
            use_case,
            attempt_id,
            execution_owner,
            block,
            expected_context,
        )

    monkeypatch.setattr(
        PublishMentorResponseBlockUseCase,
        'execute',
        reject_generated_block,
    )
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=attachment_id,
        goal_id=create_goal(agentos_fixture.client),
    )

    detail = wait_for_session_response(
        agentos_fixture.client,
        session_id,
        attempt_id=attempt_id,
    )
    snapshot = cast('dict[str, object]', detail['response'])
    assert rejected_blocks == 1
    assert snapshot['status'] == 'failed'
    assert snapshot['failure_code'] == 'service_unavailable'
    assert MODEL_ANSWER not in json.dumps(detail, ensure_ascii=False)
    learner_message_id = cast('str', snapshot['learner_message_id'])
    with Session(postgres_database.engine) as session:
        reply = session.scalar(
            select(MentorMessageModel).where(
                MentorMessageModel.in_reply_to_message_id == learner_message_id
            )
        )
    assert reply is None


def test_registered_response_recovers_when_private_handoff_is_lost(
    agentos_fixture: RegisteredAgentOSFixture,
    postgres_database: PostgresDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = create_session(agentos_fixture.client)
    initial_detail = wait_for_session_response(agentos_fixture.client, session_id)
    assert (
        cast('dict[str, object]', initial_detail['response'])['status'] == 'completed'
    )
    batch_id, _attachment_id = upload_ready_text_attachment(
        agentos_fixture.client,
        session_id=session_id,
    )
    goal_id = create_goal(agentos_fixture.client)

    original_read = AgentOSHandoffStore.read_input
    simulated_restart = False

    def read_after_restart(
        store: AgentOSHandoffStore, reference: str, *, capability: str
    ) -> object:
        nonlocal simulated_restart
        if capability == 'process-mentor-response' and not simulated_restart:
            simulated_restart = True
            raise KeyError('The process-local handoff disappeared with its worker.')
        return original_read(store, reference, capability=capability)

    monkeypatch.setattr(AgentOSHandoffStore, 'read_input', read_after_restart)
    attempt_id = submit_message_with_attachment(
        agentos_fixture.client,
        session_id=session_id,
        batch_id=batch_id,
        attachment_id=_attachment_id,
        goal_id=goal_id,
    )

    detail = wait_for_session_response(
        agentos_fixture.client, session_id, attempt_id=attempt_id
    )
    snapshot = cast('dict[str, object]', detail['response'])
    assert simulated_restart
    assert snapshot['status'] == 'completed'
    assert snapshot['attempt_id'] == attempt_id

    with postgres_database.engine.connect() as connection:
        persisted_runs = (
            connection.execute(
                text(
                    'SELECT run_data::text FROM agentos_intelligence.agentos_workflow_runs '
                    'WHERE workflow_id = :workflow_id'
                ),
                {'workflow_id': 'intelligence-process-mentor-response'},
            )
            .scalars()
            .all()
        )

    assert persisted_runs
    assert all(
        ATTACHMENT_TEXT not in run_data and MODEL_ANSWER not in run_data
        for run_data in persisted_runs
    )
