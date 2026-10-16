# pyright: reportPrivateUsage=false
from __future__ import annotations

import json
import os
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from agno.agent import Agent
from agno.metrics import RunMetrics
from agno.run.agent import RunOutput
from pydantic import BaseModel
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from agno.workflow.types import StepInput

from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorEmbeddingVersionModel,
    MentorIndexedEmbeddingModel,
    MentorResponseAttemptModel,
)
from shifu.intelligence.core.use_cases.publish_mentor_response_block_use_case import (
    PublishMentorResponseBlockUseCase,
)
import shifu.intelligence.ai.agno.workflows.process_mentor_response_workflow as response_workflow_module
from shifu.intelligence.ai.agno.workflows.process_mentor_response_workflow import (
    ProcessMentorResponseWorkflow,
    _ExecutionState,
    _Input,
    _StepReference,
)
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import (
    MentorReviewResult,
    MentorResponseBlock,
    PreparedMentorResponse,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorContextSnapshot
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

    from tests.fixtures.agentos_fixture import RegisteredAgentOSFixture
    from tests.fixtures.postgres_fixture import PostgresDatabase

# The deterministic tests below exercise private workflow transition methods directly.
# ruff: noqa: SLF001

pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_REAL_AGENTOS_TESTS') != '1',
    reason='Set SHIFU_RUN_REAL_AGENTOS_TESTS=1 for registered AgentOS tests',
)


_UNIT_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'


def _response_snapshot() -> MentorContextSnapshot:
    return MentorContextSnapshot(
        goal_id=None,
        skill_experience_id=None,
        skill_id=None,
        competency_id=None,
        activity_id=None,
        skill_completed=None,
        diagnostic_in_progress=False,
        facts=(),
        eligible_references=(),
        resolved_references=(),
        unavailable_sources=(),
    )


def _prepared_response(
    *, local_blocks: tuple[MentorResponseBlock, ...] = ()
) -> PreparedMentorResponse:
    return PreparedMentorResponse(
        attempt_id=_UNIT_ID,
        execution_owner=_UNIT_ID,
        account_id=_UNIT_ID,
        session_id=_UNIT_ID,
        learner_message_id=_UNIT_ID,
        context=_response_snapshot(),
        local_blocks=local_blocks,
        attachment_request=None,
    )


def _local_block(key: str = 'local-0', ordinal: int = 0) -> MentorResponseBlock:
    return MentorResponseBlock(
        block_key=key,
        ordinal=ordinal,
        intent=None,
        content=f'Answer {key}',
        sources=(),
    )


def _step_input(last_content: str | None = None) -> Any:
    def get_last_step_content(_self: Any) -> str | None:
        return last_content

    return type(
        'WorkflowStepInput',
        (),
        {
            'input': {'attempt_id': _UNIT_ID},
            'get_last_step_content': get_last_step_content,
        },
    )()


def test_response_workflow_rejects_json_and_mapping_input_errors() -> None:
    workflow = object.__new__(ProcessMentorResponseWorkflow)

    for raw in cast(
        'tuple[Any, ...]', ('{invalid', {'attempt_id': _UNIT_ID, 'extra': True}, [])
    ):
        with pytest.raises(ServiceUnavailableError):
            workflow._prepare_and_publish(StepInput(input=raw))


def test_response_workflow_validates_publication_review_and_usage_contracts() -> None:
    for published in (False, True):
        if published:
            ProcessMentorResponseWorkflow._assert_published(published)
        else:
            with pytest.raises(ServiceUnavailableError):
                ProcessMentorResponseWorkflow._assert_published(published)

    with pytest.raises(ServiceUnavailableError):
        ProcessMentorResponseWorkflow._assert_review_result(object())
    ProcessMentorResponseWorkflow._assert_review_result(
        MentorReviewResult(
            approved=True,
            criteria=(),
            correction=None,
            probabilities=(),
        )
    )

    assert ProcessMentorResponseWorkflow._usage_fields(
        cast('Any', SimpleNamespace(metrics=None))
    ) == (None, None, None, None)
    assert ProcessMentorResponseWorkflow._usage_fields(
        cast(
            'Any',
            SimpleNamespace(
                metrics=RunMetrics(input_tokens=1, output_tokens=2, total_tokens=3)
            ),
        )
    ) == (1, 2, 3, None)
    for metrics in (
        RunMetrics(input_tokens=-1, output_tokens=2, total_tokens=1),
        RunMetrics(input_tokens=1, output_tokens=2, total_tokens=0),
        RunMetrics(input_tokens=1, output_tokens=2, total_tokens=4),
    ):
        assert ProcessMentorResponseWorkflow._usage_fields(
            cast('Any', SimpleNamespace(metrics=metrics))
        ) == (None, None, None, None)
    assert ProcessMentorResponseWorkflow._usage_fields(
        cast(
            'Any',
            SimpleNamespace(
                metrics=RunMetrics(
                    input_tokens=1, output_tokens=2, total_tokens=3, cost=-1
                )
            ),
        )
    ) == (1, 2, 3, None)


def test_response_workflow_cancels_recovery_when_claim_is_no_longer_active() -> None:
    workflow = object.__new__(ProcessMentorResponseWorkflow)
    workflow._consume = Mock(side_effect=KeyError('expired handoff'))
    workflow._prepare = Mock()
    workflow._prepare.execute.return_value = None
    workflow._release_claim = Mock()

    state = workflow._consume_or_recover(
        _StepReference(handoff='h' * 32, decision='continue'),
        _Input(attempt_id=_UNIT_ID),
    )

    assert state.prepared is None
    assert state.status is MentorResponseStatus.CANCELLED
    workflow._release_claim.execute.assert_called_once_with(_UNIT_ID, _UNIT_ID)


def test_response_workflow_rejects_handoff_values_outside_its_execution_state() -> None:
    workflow = object.__new__(ProcessMentorResponseWorkflow)
    workflow._handoffs = Mock()
    workflow._handoffs.read_input.return_value = object()

    with pytest.raises(ServiceUnavailableError):
        workflow._consume(_StepReference(handoff='h' * 32, decision='continue'))


def test_response_workflow_reuses_existing_handoff_without_repreparing() -> None:
    workflow = object.__new__(ProcessMentorResponseWorkflow)
    state = _ExecutionState(
        prepared=_prepared_response(),
        status=MentorResponseStatus.PROCESSING,
    )
    workflow._consume = Mock(return_value=state)
    workflow._prepare = Mock()

    recovered = workflow._consume_or_recover(
        _StepReference(handoff='h' * 32, decision='continue'),
        _Input(attempt_id=_UNIT_ID),
    )

    assert recovered is state
    workflow._prepare.execute.assert_not_called()


def test_response_workflow_stops_inference_when_claim_renewal_is_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ControlledEvent:
        def __init__(self) -> None:
            self.state = False

        def wait(self, timeout: float | None = None) -> bool:
            return self.state

        def is_set(self) -> bool:
            return self.state

        def set(self) -> None:
            self.state = True

    class SynchronousThread:
        def __init__(self, *, target: Callable[[], None], daemon: bool) -> None:
            self.target = target
            self.joined = False

        def start(self) -> None:
            self.target()

        def join(self, timeout: float | None = None) -> None:
            self.joined = True

    workflow = object.__new__(ProcessMentorResponseWorkflow)
    workflow._renew_claim = Mock()
    workflow._renew_claim.execute.return_value = False
    workflow._assert_current = Mock()
    events: list[ControlledEvent] = []

    def make_event() -> ControlledEvent:
        event = ControlledEvent()
        events.append(event)
        return event

    thread: SynchronousThread | None = None

    def make_thread(*, target: Callable[[], None], daemon: bool) -> SynchronousThread:
        nonlocal thread
        thread = SynchronousThread(target=target, daemon=daemon)
        return thread

    monkeypatch.setattr(response_workflow_module, 'Event', make_event)
    monkeypatch.setattr(response_workflow_module, 'Thread', make_thread)

    with (
        pytest.raises(ServiceUnavailableError),
        workflow._inference_guard(_UNIT_ID, _UNIT_ID),
    ):
        pytest.fail('inference must not run after claim renewal is lost')

    workflow._renew_claim.execute.assert_called_once_with(_UNIT_ID, _UNIT_ID)
    workflow._assert_current.assert_not_called()
    assert len(events) == 2 and events[0].state
    assert thread is not None and thread.joined


@pytest.mark.parametrize(
    ('published', 'expected'), [(True, 'continue'), (False, 'done')]
)
def test_response_workflow_publishes_local_blocks_or_fails_closed(
    published: bool, expected: str
) -> None:
    workflow = object.__new__(ProcessMentorResponseWorkflow)
    block = _local_block()
    workflow._prepare = Mock()
    workflow._prepare.execute.return_value = _prepared_response(local_blocks=(block,))
    workflow._publish_block = Mock()
    workflow._publish_block.execute.return_value = published
    workflow._fail = Mock()
    workflow._fail.execute.return_value = MentorResponseStatus.FAILED
    workflow._release_claim = Mock()
    workflow._handoffs = Mock()
    workflow._handoffs.create.return_value = 'h' * 32

    output = workflow._prepare_and_publish(StepInput(input={'attempt_id': _UNIT_ID}))
    reference = _StepReference.model_validate_json(
        cast('str', output.content), strict=True
    )

    assert reference.decision == expected
    if published:
        stored = workflow._handoffs.create.call_args.kwargs['input_value']
        assert stored.status is MentorResponseStatus.PROCESSING
        assert stored.approved_blocks == (block,)
        workflow._fail.execute.assert_not_called()
    else:
        assert workflow._handoffs.create.call_args.kwargs['input_value'].status is (
            MentorResponseStatus.FAILED
        )
        workflow._fail.execute.assert_called_once_with(
            _UNIT_ID, _UNIT_ID, 'service_unavailable'
        )


@pytest.mark.parametrize(
    ('finalized', 'expected'),
    [(True, MentorResponseStatus.COMPLETED), (False, MentorResponseStatus.FAILED)],
)
def test_response_workflow_finalizes_recovered_local_answer_and_releases_claim(
    finalized: bool, expected: MentorResponseStatus
) -> None:
    workflow = object.__new__(ProcessMentorResponseWorkflow)
    block = _local_block()
    prepared = _prepared_response()
    state = _ExecutionState(
        prepared=prepared,
        status=MentorResponseStatus.PROCESSING,
        approved_blocks=(block,),
    )
    workflow._consume_or_recover = Mock(return_value=state)
    workflow._assert_current = Mock()
    workflow._finalizer = Mock()
    workflow._finalizer.execute.return_value = finalized
    workflow._fail = Mock()
    workflow._fail.execute.return_value = MentorResponseStatus.FAILED
    workflow._release_claim = Mock()
    reference = _StepReference(handoff='h' * 32, decision='done')

    output = workflow._publish_and_finalize(
        cast('StepInput', _step_input(reference.model_dump_json()))
    )

    assert output.content == expected.value
    workflow._finalizer.execute.assert_called_once_with(
        _UNIT_ID,
        _UNIT_ID,
        _UNIT_ID,
        block.content,
        _UNIT_ID,
        _UNIT_ID,
    )
    workflow._release_claim.execute.assert_called_once_with(_UNIT_ID, _UNIT_ID)


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
