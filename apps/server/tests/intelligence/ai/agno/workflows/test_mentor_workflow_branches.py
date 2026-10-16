"""Direct workflow branch coverage uses internal boundaries by design."""

# pyright: reportPrivateUsage=false
import json
from contextlib import nullcontext
from contextvars import ContextVar
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import Mock

import pytest
from agno.agent import Agent
from agno.run.base import RunStatus
from agno.workflow.types import StepInput, StepOutput

from shifu.intelligence.ai.agno.agents.mentor_attachment_answer_agent import (
    MentorAttachmentAnswerAgent,
)
from shifu.intelligence.ai.agno.agents.mentor_attachment_vision_agent import (
    MentorAttachmentVisionAgent,
)
from shifu.intelligence.ai.agno.outputs import (
    MentorAttachmentAnswerOutput,
    MentorAttachmentSourceOutput,
    MentorAttachmentVisionOutput,
)
from shifu.intelligence.ai.agno.workflows.agno_generate_mentor_title_workflow import (
    AgnoGenerateMentorTitleWorkflow,
)
from shifu.intelligence.ai.agno.workflows.prepare_mentor_attachment_workflow import (
    PrepareMentorAttachmentWorkflow,
    _ClaimHeartbeat,
    _Execution,
    _PreparationInput,
)
from shifu.intelligence.ai.agno.workflows.process_mentor_response_workflow import (
    ProcessMentorResponseWorkflow,
    _ExecutionState,
    _StepReference,
)
from shifu.intelligence.ai.agno.workflows.purge_mentor_attachments_workflow import (
    PurgeMentorAttachmentsWorkflow,
)
from shifu.intelligence.ai.data.mentor_inference_usage import (
    inference_guard_scope,
    inference_usage_scope,
)
from shifu.intelligence.core.domain.errors import (
    MentorAttachmentInvalidError,
    MentorAttachmentUnavailableError,
)
from shifu.intelligence.core.domain.structures import (
    MentorAttachmentChunk,
    MentorAttachmentContext,
    MentorAttachmentExtraction,
    MentorAttachmentSource,
    MentorGenerationRequest,
    MentorResponseBlock,
    MentorReviewResult,
    PreparedMentorAttachment,
    PreparedMentorResponse,
)
from shifu.intelligence.providers.mentor_attachment.local_mentor_attachment_extractor_provider import (
    LocalMentorAttachmentExtractorProvider,
)
from shifu.intelligence.core.domain.enums import (
    MentorAttachmentStatus,
    MentorResponseStatus,
    MentorWorkflowStep,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorContextSnapshot

if TYPE_CHECKING:
    from agno.models.base import Model


_ID = '01J00000000000000000000000'


def _ignore_usage(_usage: Any) -> None:
    return


def _noop_guard(*_args: Any) -> Any:
    return nullcontext()


def _stub_agent(monkeypatch: pytest.MonkeyPatch, result: Any) -> None:
    def initialize(_self: Any, **_kwargs: Any) -> None:
        return

    def run(_self: Any, **_kwargs: Any) -> Any:
        return result

    monkeypatch.setattr(cast('Any', Agent), '__init__', initialize)
    monkeypatch.setattr(cast('Any', Agent), 'run', run)


def test_title_workflow_validates_handoff_and_completes_result() -> None:
    handoffs = Mock()
    handoffs.read_input.return_value = 'Help me study'
    agent = Mock()
    agent.run.return_value = SimpleNamespace(content={'title': 'Study plan'})
    workflow = AgnoGenerateMentorTitleWorkflow(
        cast('Any', agent), cast('Any', handoffs)
    )

    output = workflow._generate(StepInput(input='{"handoff_ref":"handoff-1"}'))

    assert output.content == {'status': 'complete'}
    handoffs.complete.assert_called_once_with(
        'handoff-1',
        capability='mentor-title-generation',
        result_value='Study plan',
    )


@pytest.mark.parametrize(
    ('payload', 'handoff_value', 'expected_status'),
    [
        ('not-json', 'unused', 'invalid_request'),
        ('{"handoff_ref":"h"}', None, 'invalid_request'),
        ('{"handoff_ref":"h"}', {'private': 'bad'}, 'invalid_output'),
    ],
)
def test_title_workflow_fails_closed_on_invalid_handoff_or_output(
    payload: object, handoff_value: object, expected_status: str
) -> None:
    handoffs = Mock()
    handoffs.read_input.return_value = (
        'valid request' if expected_status == 'invalid_output' else handoff_value
    )
    agent = Mock()
    agent.run.return_value = SimpleNamespace(
        content={'private': 'bad'}
        if expected_status == 'invalid_output'
        else handoff_value
    )
    workflow = AgnoGenerateMentorTitleWorkflow(
        cast('Any', agent), cast('Any', handoffs)
    )

    output = workflow._generate(StepInput(input=cast('Any', payload)))

    assert output.content == {'status': expected_status}


def test_purge_workflow_parses_string_generation_and_executes_target() -> None:
    workflow = cast('Any', object.__new__(PurgeMentorAttachmentsWorkflow))
    workflow._purge_use_case = Mock()
    workflow._request = ContextVar('test-purge-request', default=None)
    workflow._purge_use_case.execute.return_value = 3

    request = json.dumps(
        {'account_id': _ID, 'batch_id': _ID, 'deletion_generation': '2'}
    )
    parsed = PurgeMentorAttachmentsWorkflow._parse_input(request)
    output = workflow._purge(StepInput(input=request))

    assert parsed.deletion_generation == 2
    assert output.content == '{"removed_objects": 3}'
    workflow._purge_use_case.execute.assert_called_once_with(_ID, None, _ID, 2)


def test_purge_workflow_rejects_missing_or_ambiguous_cleanup_target() -> None:
    for payload in (
        {'account_id': _ID, 'deletion_generation': 1},
        {
            'account_id': _ID,
            'session_id': _ID,
            'batch_id': _ID,
            'deletion_generation': 1,
        },
    ):
        with pytest.raises(MentorAttachmentInvalidError):
            PurgeMentorAttachmentsWorkflow._parse_input(payload)


def test_purge_workflow_deep_copy_preserves_use_case_and_applies_updates() -> None:
    use_case = Mock()
    workflow = PurgeMentorAttachmentsWorkflow(use_case)
    workflow_any = cast('Any', workflow)
    workflow_any.db = 'test-database'

    copied = workflow.deep_copy(update={'db': 'copied-database'})

    assert copied.db == 'copied-database'
    assert copied._purge_use_case is use_case


def _prepare_workflow() -> Any:
    workflow = cast('Any', object.__new__(PrepareMentorAttachmentWorkflow))
    workflow._execution = cast(
        'Any', ContextVar('test-preparation-execution', default=None)
    )
    workflow._prepare_use_case = Mock()
    workflow._release_claim_use_case = Mock()
    workflow._complete_use_case = Mock()
    workflow._fail_use_case = Mock()
    return workflow


def test_prepare_workflow_normalizes_generation_and_noops_when_claim_is_stale() -> None:
    workflow = _prepare_workflow()
    workflow._prepare_use_case.execute.return_value = None
    payload = json.dumps({'attachment_id': _ID, 'generation': '2'})

    parsed = workflow._parse_input(payload)
    prepared = workflow._prepare(StepInput(input=payload))
    completed = workflow._complete(StepInput(input=payload))

    assert parsed.generation == 2
    assert prepared.content == 'stale_or_already_claimed'
    assert completed.content == 'no_op'


def test_prepare_workflow_releases_a_claim_when_prepare_use_case_fails() -> None:
    workflow = _prepare_workflow()
    workflow._prepare_use_case.execute.side_effect = RuntimeError('private detail')
    payload = {'attachment_id': _ID, 'generation': 1}

    with pytest.raises(RuntimeError, match='private detail'):
        workflow._prepare(StepInput(input=payload))

    workflow._release_claim_use_case.execute.assert_called_once_with(_ID, 1, _ID)
    assert workflow._execution.get() is None


def test_prepare_workflow_extracts_and_commits_safe_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Heartbeat:
        lost = False

        def __init__(self, *_args: object) -> None:
            pass

        def __enter__(self) -> '_Heartbeat':
            return self

        def __exit__(self, *_args: object) -> None:
            return

    monkeypatch.setattr(
        'shifu.intelligence.ai.agno.workflows.prepare_mentor_attachment_workflow._ClaimHeartbeat',
        _Heartbeat,
    )
    workflow = _prepare_workflow()
    workflow._execution = cast(
        'Any', ContextVar('test-successful-preparation', default=None)
    )
    prepared = PreparedMentorAttachment(
        attachment_id=_ID,
        generation=1,
        execution_owner=_ID,
        media_type='text/plain',
        content=b'lesson notes',
    )
    execution = _Execution(
        request=_PreparationInput(attachment_id=_ID, generation=1),
        owner=_ID,
        prepared=prepared,
    )
    workflow._execution.set(execution)
    workflow._extractor_provider = Mock()
    workflow._extractor_provider.extract.return_value = MentorAttachmentExtraction(
        chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
    )
    workflow._extractor_provider.render_visual_pages.return_value = ()
    workflow._renew_claim_use_case = Mock()
    workflow._identifier_provider = Mock()
    workflow._max_pdf_pages = 10
    workflow._usage_recorder = None
    workflow._complete_use_case.execute.return_value = MentorAttachmentStatus.READY

    extraction_output = workflow._extract(StepInput(input={}))
    completion_output = workflow._complete(StepInput(input={}))

    assert isinstance(extraction_output.content, str)
    assert json.loads(extraction_output.content)['attachment_id'] == _ID
    assert isinstance(completion_output.content, str)
    assert json.loads(completion_output.content)['status'] == 'ready'
    workflow._complete_use_case.execute.assert_called_once()
    assert workflow._execution.get() is None


def test_prepare_workflow_marks_invalid_extraction_as_terminal_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shifu.intelligence.ai.agno.workflows import (
        prepare_mentor_attachment_workflow as module,
    )

    class _Heartbeat:
        lost = False

        def __init__(self, *_args: object) -> None:
            pass

        def __enter__(self) -> '_Heartbeat':
            return self

        def __exit__(self, *_args: object) -> None:
            return

    monkeypatch.setattr(module, '_ClaimHeartbeat', _Heartbeat)
    workflow = _prepare_workflow()
    workflow._execution = cast(
        'Any', ContextVar('test-invalid-preparation', default=None)
    )
    workflow._execution.set(
        _Execution(
            request=_PreparationInput(attachment_id=_ID, generation=1),
            owner=_ID,
            prepared=PreparedMentorAttachment(
                attachment_id=_ID,
                generation=1,
                execution_owner=_ID,
                media_type='text/plain',
                content=b'bad file',
            ),
        )
    )
    workflow._extractor_provider = Mock()
    workflow._renew_claim_use_case = Mock()
    workflow._extractor_provider.extract.side_effect = MentorAttachmentInvalidError
    workflow._renew_claim_use_case = Mock()
    workflow._max_pdf_pages = 10

    result = workflow._extract(StepInput(input={}))

    assert result.content == 'failed_invalid_file'
    workflow._fail_use_case.execute.assert_called_once_with(_ID, 1, _ID, 'invalid_file')
    assert workflow._execution.get() is None


def test_prepare_workflow_discards_extraction_after_heartbeat_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shifu.intelligence.ai.agno.workflows import (
        prepare_mentor_attachment_workflow as module,
    )

    class _LostHeartbeat:
        lost = True

        def __init__(self, *_args: object) -> None:
            pass

        def __enter__(self) -> '_LostHeartbeat':
            return self

        def __exit__(self, *_args: object) -> None:
            return

    monkeypatch.setattr(module, '_ClaimHeartbeat', _LostHeartbeat)
    workflow = _prepare_workflow()
    workflow._execution = cast('Any', ContextVar('test-lost-preparation', default=None))
    workflow._execution.set(
        _Execution(
            request=_PreparationInput(attachment_id=_ID, generation=1),
            owner=_ID,
            prepared=PreparedMentorAttachment(
                attachment_id=_ID,
                generation=1,
                execution_owner=_ID,
                media_type='text/plain',
                content=b'lesson notes',
            ),
        )
    )
    workflow._extractor_provider = Mock()
    workflow._renew_claim_use_case = Mock()

    result = workflow._extract(StepInput(input={}))

    assert result.content == 'stale_claim'
    workflow._extractor_provider.render_visual_pages.assert_not_called()
    assert workflow._execution.get() is None


def test_prepare_workflow_analyzes_rendered_image_and_commits_failure_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shifu.intelligence.ai.agno.workflows import (
        prepare_mentor_attachment_workflow as module,
    )

    class _Heartbeat:
        lost = False

        def __init__(self, *_args: object) -> None:
            pass

        def __enter__(self) -> '_Heartbeat':
            return self

        def __exit__(self, *_args: object) -> None:
            return

    monkeypatch.setattr(module, '_ClaimHeartbeat', _Heartbeat)
    workflow = _prepare_workflow()
    workflow._execution = cast(
        'Any', ContextVar('test-image-preparation', default=None)
    )
    prepared = PreparedMentorAttachment(
        attachment_id=_ID,
        generation=1,
        execution_owner=_ID,
        media_type='image/png',
        content=b'image-bytes',
    )
    execution = _Execution(
        request=_PreparationInput(attachment_id=_ID, generation=1),
        owner=_ID,
        prepared=prepared,
    )
    workflow._execution.set(execution)
    workflow._extractor_provider = Mock()
    workflow._extractor_provider.extract.return_value = MentorAttachmentExtraction(
        chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
    )
    workflow._extractor_provider.render_visual_pages.return_value = ((1, b'rendered'),)
    workflow._vision_agent = Mock()
    workflow._vision_agent.analyze.return_value = SimpleNamespace(
        legible=False, description='ignored when page is illegible'
    )
    workflow._renew_claim_use_case = Mock()
    workflow._renew_claim_use_case.execute.return_value = True
    workflow._usage_recorder = _ignore_usage

    extracted = workflow._extract(StepInput(input={}))

    assert isinstance(extracted.content, str)
    assert json.loads(extracted.content)['analyzed_page_count'] == 0
    assert execution.extraction is not None
    assert execution.extraction.illegible_pages == (1,)
    workflow._extractor_provider.render_visual_pages.assert_called_once_with(
        b'image-bytes', 'image/png', (1,)
    )
    workflow._vision_agent.analyze.assert_called_once()


def test_prepare_workflow_releases_claim_when_completion_fails() -> None:
    workflow = _prepare_workflow()
    workflow._execution = cast(
        'Any', ContextVar('test-failed-completion', default=None)
    )
    prepared = PreparedMentorAttachment(
        attachment_id=_ID,
        generation=1,
        execution_owner=_ID,
        media_type='text/plain',
        content=b'lesson notes',
    )
    workflow._execution.set(
        _Execution(
            request=_PreparationInput(attachment_id=_ID, generation=1),
            owner=_ID,
            prepared=prepared,
            extraction=MentorAttachmentExtraction(
                chunks=(), analyzed_pages=(), illegible_pages=(), uninterpreted_pages=()
            ),
        )
    )
    workflow._complete_use_case.execute.side_effect = RuntimeError(
        'storage unavailable'
    )

    with pytest.raises(RuntimeError, match='storage unavailable'):
        workflow._complete(StepInput(input={}))

    workflow._release_claim_use_case.execute.assert_called_once_with(_ID, 1, _ID)
    assert workflow._execution.get() is None


def test_prepare_workflow_uses_local_extractor_for_text_and_asserts_claim() -> None:
    provider = LocalMentorAttachmentExtractorProvider(
        cast(
            'Any',
            SimpleNamespace(
                mentor_attachment_max_image_pixels=1_000_000,
                mentor_attachment_max_pdf_pages=5,
                mentor_attachment_max_extracted_chars=2_000,
                mentor_attachment_pdf_processing_timeout_seconds=1.0,
                mentor_attachment_max_pdf_rendered_bytes=1_000_000,
            ),
        )
    )
    workflow = _prepare_workflow()
    workflow._execution = cast(
        'Any', ContextVar('test-real-text-extraction', default=None)
    )
    prepared = PreparedMentorAttachment(
        attachment_id=_ID,
        generation=1,
        execution_owner=_ID,
        media_type='text/plain',
        content=b'A list stores items in order.',
    )
    execution = _Execution(
        request=_PreparationInput(attachment_id=_ID, generation=1),
        owner=_ID,
        prepared=prepared,
    )
    workflow._execution.set(execution)
    workflow._extractor_provider = provider
    workflow._renew_claim_use_case = Mock()
    workflow._renew_claim_use_case.execute.return_value = True
    workflow._usage_recorder = _ignore_usage

    output = workflow._extract(StepInput(input={}))
    workflow._assert_claim_current(execution)

    assert isinstance(output.content, str)
    assert json.loads(output.content)['chunk_count'] == 1
    assert execution.extraction is not None
    assert execution.extraction.chunks[0].content == 'A list stores items in order.'
    workflow._renew_claim_use_case.execute.assert_called_once_with(_ID, 1, _ID)


def test_prepare_workflow_heartbeat_stops_after_lost_claim() -> None:
    heartbeat = cast('Any', _ClaimHeartbeat(Mock(), _ID, 1, _ID))

    class _StopAfterRenewal:
        calls = 0

        def wait(self, _timeout: float) -> bool:
            self.calls += 1
            return self.calls > 1

    heartbeat._stop = _StopAfterRenewal()  # type: ignore[assignment]
    heartbeat._renew_use_case.execute.return_value = False

    heartbeat._run()

    assert heartbeat.lost is True
    heartbeat._renew_use_case.execute.assert_called_once_with(_ID, 1, _ID)


def test_prepare_workflow_skips_completion_after_execution_is_already_done() -> None:
    workflow = _prepare_workflow()
    workflow._execution = cast(
        'Any', ContextVar('test-completed-execution', default=None)
    )
    workflow._execution.set(
        _Execution(
            request=_PreparationInput(attachment_id=_ID, generation=1),
            owner=_ID,
            completed=True,
        )
    )

    assert workflow._complete(StepInput(input={})).content == 'no_op'
    workflow._complete_use_case.execute.assert_not_called()


def test_prepare_workflow_rejects_non_positive_pdf_page_limit() -> None:
    with pytest.raises(ValueError, match='max_pdf_pages must be positive'):
        PrepareMentorAttachmentWorkflow(
            Mock(),
            Mock(),
            Mock(),
            Mock(),
            Mock(),
            Mock(),
            Mock(),
            Mock(),
            max_pdf_pages=0,
        )


def test_process_workflow_cancels_when_prepare_returns_no_active_claim() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    workflow._prepare = Mock()
    workflow._release_claim = Mock()
    workflow._handoffs = Mock()
    workflow._prepare.execute.return_value = None
    workflow._handoffs.create.return_value = 'h' * 32

    output = workflow._prepare_and_publish(StepInput(input={'attempt_id': _ID}))

    assert isinstance(output.content, str)
    assert json.loads(output.content)['decision'] == 'done'
    workflow._release_claim.execute.assert_called_once_with(_ID, _ID)


def test_process_workflow_fails_closed_when_preparation_raises() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    workflow._prepare = Mock()
    workflow._prepare.execute.side_effect = RuntimeError('private adapter error')
    workflow._fail = Mock()
    workflow._fail.execute.return_value = MentorResponseStatus.FAILED
    workflow._release_claim = Mock()
    workflow._handoffs = Mock()
    workflow._handoffs.create.return_value = 'h' * 32

    output = workflow._prepare_and_publish(StepInput(input={'attempt_id': _ID}))

    assert isinstance(output.content, str)
    assert json.loads(output.content)['decision'] == 'done'
    workflow._fail.execute.assert_called_once_with(_ID, _ID, 'service_unavailable')
    workflow._release_claim.execute.assert_called_once_with(_ID, _ID)


def test_process_workflow_rejects_malformed_request_and_publication() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    with pytest.raises(ServiceUnavailableError):
        workflow._prepare_and_publish(StepInput(input={'unexpected': True}))
    with pytest.raises(ServiceUnavailableError):
        ProcessMentorResponseWorkflow._assert_published(published=False)
    ProcessMentorResponseWorkflow._assert_published(published=True)


def test_process_workflow_writes_and_reviews_attachment_answer() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    context, _ = _attachment_context()
    snapshot = MentorContextSnapshot(
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
    request = MentorGenerationRequest(
        session_id=_ID,
        learner_message_id=_ID,
        attempt_id=_ID,
        requested_part='Explain the list data structure',
        history=(),
        context=snapshot,
        approved_blocks=(),
        correction=None,
        attachment_context=context,
    )
    prepared = PreparedMentorResponse(
        attempt_id=_ID,
        execution_owner=_ID,
        account_id=_ID,
        session_id=_ID,
        learner_message_id=_ID,
        context=snapshot,
        local_blocks=(),
        attachment_request=request,
    )
    state = _ExecutionState(
        prepared=prepared,
        status=MentorResponseStatus.PROCESSING,
    )
    workflow._record_usage = Mock()
    workflow._record_progress = Mock()
    workflow._assert_current = Mock()
    workflow._renew_claim = Mock()
    workflow._inference_guard = _noop_guard
    workflow._telemetry = None
    workflow._attachment_answer = Mock()
    workflow._attachment_answer.answer.return_value = SimpleNamespace(
        answer='A list stores items.'
    )
    workflow._attachment_answer.domain_sources.return_value = ()
    workflow._reviewer = Mock()
    workflow._reviewer.review.return_value = MentorReviewResult(
        approved=True,
        criteria=(),
        correction=None,
    )
    workflow._store = Mock(return_value=StepOutput(content='stored'))

    output = workflow._write_state(state)

    assert output.content == 'stored'
    stored_state = workflow._store.call_args.args[0]
    assert stored_state.approved is True
    assert stored_state.iteration == 1
    assert stored_state.candidate is not None
    assert stored_state.candidate.content == 'A list stores items.'
    workflow._attachment_answer.answer.assert_called_once_with(
        request.requested_part, context
    )
    workflow._reviewer.review.assert_called_once()
    workflow._record_progress.execute.assert_any_call(
        _ID, _ID, MentorWorkflowStep.WRITE_ANSWER
    )
    workflow._store.assert_called_once_with(stored_state, 'done')


def test_process_workflow_writes_general_answer_from_structured_output() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    snapshot = MentorContextSnapshot(
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
    request = MentorGenerationRequest(
        session_id=_ID,
        learner_message_id=_ID,
        attempt_id=_ID,
        requested_part='Explain a list',
        history=(),
        context=snapshot,
        approved_blocks=(),
        correction=None,
    )
    workflow._record_usage = Mock()
    workflow._assert_current = Mock()
    workflow._writer = Mock()
    workflow._writer.run.return_value = SimpleNamespace(
        status=RunStatus.completed,
        content={
            'block_key': 'model-key',
            'ordinal': 0,
            'intent': None,
            'content': 'A list keeps items in order.',
            'sources': [],
        },
        metrics=None,
    )

    candidate = workflow._write_general_answer(request, _ID, _ID, 0)

    assert candidate.block_key == 'generated-0'
    assert candidate.content == 'A list keeps items in order.'
    assert candidate.sources == ()
    workflow._assert_current.execute.assert_called_once_with(_ID, _ID)
    workflow._record_usage.execute.assert_called_once()


@pytest.mark.parametrize(
    ('outputs', 'expected'),
    [
        ((), True),
        ((StepOutput(content=object()),), True),
        ((StepOutput(content='not-json'),), True),
        (
            (
                StepOutput(
                    content='{"handoff":"h1234567890123456789012345678901","decision":"retry","iteration":1}'
                ),
            ),
            False,
        ),
        (
            (
                StepOutput(
                    content='{"handoff":"h1234567890123456789012345678901","decision":"done","iteration":1}'
                ),
            ),
            True,
        ),
    ],
)
def test_process_workflow_stops_review_loop_for_terminal_or_malformed_output(
    outputs: tuple[StepOutput, ...], expected: bool
) -> None:
    assert ProcessMentorResponseWorkflow._review_complete(outputs) is expected


def test_process_workflow_recovers_handoff_from_prepared_response() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    workflow._handoffs = Mock()
    workflow._handoffs.read_input.side_effect = KeyError('expired handoff')
    workflow._prepare = Mock()
    workflow._release_claim = Mock()
    context = MentorContextSnapshot(
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
    prepared = PreparedMentorResponse(
        attempt_id=_ID,
        execution_owner=_ID,
        account_id=_ID,
        session_id=_ID,
        learner_message_id=_ID,
        context=context,
        local_blocks=(),
        attachment_request=None,
    )
    workflow._prepare.execute.return_value = prepared
    request = ProcessMentorResponseWorkflow._request_for_step(
        StepInput(input={'attempt_id': _ID})
    )

    recovered = workflow._consume_or_recover(
        _StepReference(handoff='h' * 32, decision='continue', iteration=0), request
    )

    assert recovered.prepared is prepared
    assert recovered.status is MentorResponseStatus.PROCESSING
    assert recovered.approved_blocks == ()
    workflow._prepare.execute.assert_called_once_with(_ID, _ID)


def test_process_workflow_recovers_and_republishes_local_blocks_after_handoff_loss() -> (
    None
):
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    workflow._handoffs = Mock()
    workflow._handoffs.read_input.side_effect = KeyError('expired handoff')
    workflow._prepare = Mock()
    workflow._release_claim = Mock()
    workflow._publish_block = Mock()
    workflow._publish_block.execute.return_value = True
    context = MentorContextSnapshot(
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
    local = MentorResponseBlock(
        block_key='local-1', ordinal=0, intent=None, content='Use an example.'
    )
    prepared = PreparedMentorResponse(
        attempt_id=_ID,
        execution_owner=_ID,
        account_id=_ID,
        session_id=_ID,
        learner_message_id=_ID,
        context=context,
        local_blocks=(local,),
        attachment_request=None,
    )
    workflow._prepare.execute.return_value = prepared
    request = ProcessMentorResponseWorkflow._request_for_step(
        StepInput(input={'attempt_id': _ID})
    )

    recovered = workflow._consume_or_recover(
        _StepReference(handoff='h' * 32, decision='continue', iteration=0), request
    )

    assert recovered.approved_blocks == (local,)
    workflow._publish_block.execute.assert_called_once_with(_ID, _ID, local, context)


def test_process_workflow_recovers_prior_review_iteration() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    workflow._handoffs = Mock()
    workflow._prepare = Mock()
    workflow._prepare.execute.return_value = PreparedMentorResponse(
        attempt_id=_ID,
        execution_owner=_ID,
        account_id=_ID,
        session_id=_ID,
        learner_message_id=_ID,
        context=MentorContextSnapshot(
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
        ),
        local_blocks=(),
        attachment_request=None,
    )
    request = ProcessMentorResponseWorkflow._request_for_step(
        StepInput(input={'attempt_id': _ID})
    )
    approved = _ExecutionState(
        prepared=workflow._prepare.execute.return_value,
        status=MentorResponseStatus.PROCESSING,
        approved=True,
        iteration=1,
    )
    next_reference = _StepReference(handoff='n' * 32, decision='done', iteration=1)
    workflow._consume = Mock(side_effect=[KeyError('expired'), approved])
    workflow._write_state = Mock(return_value=StepOutput(content='state-ref'))
    workflow._read_reference = Mock(return_value=next_reference)

    recovered = workflow._consume_or_recover(
        _StepReference(handoff='h' * 32, decision='retry', iteration=1), request
    )

    assert recovered is approved
    workflow._write_state.assert_called_once()
    workflow._read_reference.assert_called_once_with('state-ref')


def test_process_workflow_finalizes_published_local_response() -> None:
    workflow = cast('Any', object.__new__(ProcessMentorResponseWorkflow))
    context = MentorContextSnapshot(
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
    block = MentorResponseBlock(
        block_key='local-1', ordinal=0, intent=None, content='Use an example.'
    )
    prepared = PreparedMentorResponse(
        attempt_id=_ID,
        execution_owner=_ID,
        account_id=_ID,
        session_id=_ID,
        learner_message_id=_ID,
        context=context,
        local_blocks=(block,),
        attachment_request=None,
    )
    state = _ExecutionState(
        prepared=prepared,
        status=MentorResponseStatus.PROCESSING,
        approved_blocks=(block,),
    )
    workflow._read_reference = Mock()
    workflow._request_for_step = Mock()
    workflow._consume_or_recover = Mock(return_value=state)
    workflow._assert_current = Mock()
    workflow._finalizer = Mock()
    workflow._finalizer.execute.return_value = True
    workflow._release_claim = Mock()

    output = workflow._publish_and_finalize(StepInput(input={}))

    assert output.content == MentorResponseStatus.COMPLETED.value
    workflow._finalizer.execute.assert_called_once_with(
        _ID, _ID, _ID, 'Use an example.', _ID, _ID
    )
    workflow._release_claim.execute.assert_called_once_with(_ID, _ID)


def _attachment_context() -> tuple[MentorAttachmentContext, MentorAttachmentSource]:
    source = MentorAttachmentSource(
        attachment_id=_ID,
        chunk_id='01J00000000000000000000001',
        page_number=None,
        locator='chars:1-5#1',
    )
    chunk = MentorAttachmentChunk(
        chunk_id=source.chunk_id,
        attachment_id=source.attachment_id,
        generation=1,
        page_number=None,
        locator=source.locator,
        content='A list stores items.',
    )
    return MentorAttachmentContext(chunks=(chunk,), sources=(source,)), source


def test_attachment_answer_agent_accepts_only_context_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context, source = _attachment_context()
    output_source = MentorAttachmentSourceOutput(
        attachment_id=source.attachment_id,
        chunk_id=source.chunk_id,
        page_number=source.page_number,
        locator=source.locator,
    )
    _stub_agent(
        monkeypatch,
        SimpleNamespace(
            content=MentorAttachmentAnswerOutput(
                answer='A list stores items.', sources=[output_source]
            ),
            metrics=None,
        ),
    )
    agent = MentorAttachmentAnswerAgent(cast('Model', object()))
    usage: list[object] = []

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('attempt', usage.append),
    ):
        result = agent.answer('What is a list?', context)

    assert result.answer == 'A list stores items.'
    assert len(usage) == 1


def test_attachment_answer_agent_rejects_empty_input_and_unapproved_citations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty_context = MentorAttachmentContext(chunks=(), sources=())
    with pytest.raises(MentorAttachmentUnavailableError):
        MentorAttachmentAnswerAgent.answer(
            object.__new__(MentorAttachmentAnswerAgent), 'question', empty_context
        )

    context, source = _attachment_context()
    foreign_source = MentorAttachmentSourceOutput(
        attachment_id=source.attachment_id,
        chunk_id=source.chunk_id,
        page_number=None,
        locator='page:3/secret',
    )
    _stub_agent(
        monkeypatch,
        SimpleNamespace(
            content=MentorAttachmentAnswerOutput(
                answer='claim', sources=[foreign_source]
            ),
            metrics=None,
        ),
    )
    agent = MentorAttachmentAnswerAgent(cast('Model', object()))

    with (
        inference_guard_scope(lambda: None),
        inference_usage_scope('attempt', lambda _usage: None),
        pytest.raises(MentorAttachmentUnavailableError),
    ):
        agent.answer('question', context)


def test_attachment_vision_agent_records_usage_and_rejects_invalid_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_agent(
        monkeypatch,
        SimpleNamespace(
            content=MentorAttachmentVisionOutput(
                legible=True, description='lesson text'
            ),
            metrics=None,
        ),
    )
    agent = MentorAttachmentVisionAgent(cast('Model', object()))
    usage: list[object] = []

    with inference_guard_scope(lambda: None):
        result = agent.analyze(
            b'image-bytes',
            media_type='image/png',
            attachment_id=_ID,
            page_number=1,
            usage_recorder=usage.append,
        )

    assert result.description == 'lesson text'
    assert len(usage) == 1
    with pytest.raises(MentorAttachmentUnavailableError):
        agent.analyze(b'', media_type='image/png', attachment_id=_ID, page_number=1)
    with pytest.raises(MentorAttachmentUnavailableError):
        agent.analyze(
            b'image-bytes',
            media_type='image/gif',
            attachment_id=_ID,
            page_number=1,
        )


"""Focused direct boundary coverage for Mentor AgentOS workflow steps."""

# ruff: noqa: SLF001
