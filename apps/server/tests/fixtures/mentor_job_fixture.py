"""Concrete NLP/Agno/Decisions proof through the registered disposable job."""

import hashlib
import json
import logging
import os
import sys
import subprocess
import math
from pathlib import Path
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING, Never, cast
from unittest.mock import patch

from agno.workflow.step import Step
from agno.workflow.types import StepOutput
from langfuse.types import TraceContext
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from shifu.intelligence.ai.agno.agents.mentor_writer_agent import MentorWriterAgent
from shifu.intelligence.ai.agno.models.mentor_openai_chat import MentorOpenAIChat
from shifu.intelligence.ai.agno.workflows.agno_answer_mentor_message_workflow import (
    AgnoAnswerMentorMessageWorkflow,
)
from shifu.intelligence.ai.data.mentor_resources import MentorResources
from shifu.intelligence.core.domain.events.mentor_response_requested_event import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.core.domain.structures.mentor_generation_request import (
    MentorGenerationRequest,
)
from shifu.intelligence.core.domain.structures.mentor_response_block import (
    MentorResponseBlock,
)
from shifu.intelligence.core.domain.structures.mentor_route_result import (
    MentorRouteResult,
)
from shifu.intelligence.core.domain.entities.mentor_response_attempt import (
    MentorResponseAttempt,
)
from shifu.intelligence.core.domain.enums.mentor_response_status import (
    MentorResponseStatus,
)
from shifu.intelligence.database.mentor_embeddings_database_repository import (
    MentorEmbeddingsDatabaseRepository,
)
from shifu.intelligence.database.sqlalchemy.intelligence_database import (
    SqlalchemyIntelligenceDatabase,
)
from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
    MentorResponseEventModel,
    MentorSessionModel,
    MentorEmbeddingVersionModel,
    MentorIndexedEmbeddingModel,
)
from shifu.intelligence.providers.embeddings.sentence_transformers.sentence_transformers_embeddings_provider import (
    SentenceTransformersEmbeddingsProvider,
)
from shifu.intelligence.providers.mentor_review_provider.openrouter.openrouter_jev_mentor_review_provider import (
    OpenrouterJevMentorReviewProvider,
)
from shifu.intelligence.providers.routing.local_mentor_route_provider import (
    LocalMentorRouteProvider,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    LangfuseMentorTelemetryProvider,
)
from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
    SpacyMentorTextPreprocessorProvider,
)
from shifu.shared.core.domain.structures import (
    MentorAccessGrant,
    MentorUsage,
    MentorContextSnapshot,
)
from shifu.shared.database.sqlalchemy.session import Session
from shifu.shared.database.sqlalchemy.model import Model
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.shared.core.domain.errors import ServiceUnavailableError

_PRIVATE_SDK_ERROR_CANARY = 'mentor-private-sdk-error-body-canary'
_PUBLIC_SDK_LOG_MARKER = 'mentor_sdk_public_log_boundary'

if TYPE_CHECKING:
    from shifu.intelligence.core.interfaces.mentor_faq_reranker_provider import (
        MentorFaqRerankerProvider,
    )
    from shifu.intelligence.core.interfaces import (
        MentorRouteProvider,
        MentorReviewProvider,
        AnswerMentorMessageWorkflow,
    )
    from shifu.intelligence.core.domain.enums import MentorWorkflowStep
    from shifu.intelligence.core.domain.structures import MentorInferenceUsage
    from sqlalchemy.orm import Session as SqlalchemySession
    from tests.fixtures.inngest_fixture import InngestFixture


class _Access:
    """Test-owned grant; it does not establish production quota/revocation proof."""

    _endpoint: str

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def authorize(self, account_id: str, operation_key: str) -> MentorAccessGrant:
        return MentorAccessGrant(
            account_id=account_id,
            access_revision='test-active',
            operation_key=operation_key,
        )

    def assert_current(self, grant: MentorAccessGrant) -> None:
        response = httpx.post(
            f'{self._endpoint}/access', json={'account_id': grant.account_id}
        )
        if response.status_code != 200:
            raise ServiceUnavailableError('Acesso sintético revogado.')

    def record_usage(self, grant: MentorAccessGrant, usage: MentorUsage) -> None:
        del grant
        httpx.post(
            f'{self._endpoint}/accounting',
            json={
                'operation_key': usage.operation_key,
                'attempt_id': usage.attempt_id,
                'used_tokens': usage.used_tokens,
                'cancelled': usage.cancelled,
            },
        ).raise_for_status()


class _ControlledInference:
    mode: str
    reranker_cache_folder: str | None
    calibration_case: dict[str, object] | None
    calibration_thresholds: dict[str, float]
    calibration_observations: list[dict[str, object]]
    calibration_progress: list[dict[str, object]]
    requests: list[tuple[str, dict[str, object]]]
    native_steps: list[str]
    metadata_requests: list[dict[str, object]]
    accounting_requests: list[dict[str, object]]
    effective_usage: dict[tuple[str, str], int]
    writer_entered: Event
    writer_release: Event
    accounting_entered: Event
    accounting_release: Event
    revoked_accounts: set[str]
    lock: Lock

    def __init__(self) -> None:
        self.reranker_cache_folder = None
        self.calibration_case = None
        self.calibration_thresholds = {}
        self.calibration_observations = []
        self.calibration_progress = []
        self.mode = 'approve'
        self.requests = []
        self.native_steps = []
        self.metadata_requests = []
        self.accounting_requests = []
        self.effective_usage = {}
        self.writer_entered = Event()
        self.writer_release = Event()
        self.accounting_entered = Event()
        self.accounting_release = Event()
        self.revoked_accounts = set()
        self.lock = Lock()

    def reset(self, mode: str) -> None:
        with self.lock:
            self.mode = mode
            self.reranker_cache_folder = None
            self.requests.clear()
            self.calibration_progress.clear()
            self.native_steps.clear()
            self.metadata_requests.clear()
            self.accounting_requests.clear()
            self.effective_usage.clear()
            self.writer_entered.clear()
            self.writer_release.clear()
            self.accounting_entered.clear()
            self.accounting_release.clear()
            self.revoked_accounts.clear()

    def respond(self, path: str, payload: dict[str, object]) -> tuple[int, object]:
        calibration_response = self._calibration_response(path, payload)
        if calibration_response is not None:
            return calibration_response
        if path == '/review-backoff':
            return self._backoff_response()
        if path == '/accounting':
            return self._accounting_response(payload)
        if path == '/telemetry':
            return self._telemetry_response(payload)
        with self.lock:
            if path in {'/configuration', '/access'}:
                return self._control_response(path, payload)
            self.requests.append((path, payload))
            review_count = sum(name == '/decisions' for name, _ in self.requests)
            writer_count = sum(
                name == '/v1/chat/completions' for name, _ in self.requests
            )
            mode = self.mode
        if path == '/v1/chat/completions' and (
            mode in {'pause_writer', 'pause_lease'}
            or mode == 'pause_failure'
            or (mode == 'pause_second_writer' and writer_count == 2)
        ):
            self.writer_entered.set()
            if not self.writer_release.wait(
                timeout=45 if mode == 'pause_lease' else 30
            ):
                return 503, {'error': {'message': 'controlled pause timeout'}}
        error_response = self._writer_error_response(path, mode)
        if error_response is not None:
            return error_response
        if path == '/decisions':
            return self._review_with_barrier(payload, mode, review_count)
        return self._calibration_writer_response(payload, mode)

    def _agent_review_with_count(
        self, payload: dict[str, object]
    ) -> tuple[int, object]:
        path = '/review/v1/chat/completions'
        with self.lock:
            self.requests.append((path, payload))
            review_count = sum(name == path for name, _ in self.requests)
            mode = self.mode
        if mode == 'pause_agent_review':
            self.writer_entered.set()
            if not self.writer_release.wait(timeout=30):
                return 503, {'error': {'message': 'controlled review pause timeout'}}
        return self._agent_review_response(payload, mode, review_count)

    @staticmethod
    def _agent_review_response(
        payload: dict[str, object], mode: str, review_count: int
    ) -> tuple[int, object]:
        if mode == 'agent_review_body_list':
            return 503, [_PRIVATE_SDK_ERROR_CANARY]
        if mode in {
            'agent_review_failure',
            'agent_review_failure_unknown',
            'agent_review_usage_bool',
        }:
            failure: dict[str, object] = {
                'error': {'message': _PRIVATE_SDK_ERROR_CANARY, 'type': 'server_error'}
            }
            if mode in {'agent_review_failure', 'agent_review_usage_bool'}:
                failure['usage'] = {
                    'prompt_tokens': 50,
                    'completion_tokens': 10,
                    'total_tokens': 60,
                }
            if mode == 'agent_review_usage_bool':
                failure['usage'] = {
                    'prompt_tokens': True,
                    'completion_tokens': 10,
                    'total_tokens': 60,
                }
            return 503, failure
        response_format = cast('dict[str, object]', payload['response_format'])
        schema = cast(
            'dict[str, object]',
            cast('dict[str, object]', response_format['json_schema'])['schema'],
        )
        required = cast('list[str]', schema['required'])
        choice = 'approved'
        if mode == 'reject' or (mode == 'correct' and review_count == 1):
            choice = 'rejected'
        elif mode == 'agent_review_inconclusive':
            choice = 'inconclusive'
        review: dict[str, object] = {
            key: {
                'choice': choice,
                'feedback': 'Reformule o trecho sem criar fatos.'
                if choice != 'approved'
                else '',
            }
            for key in required
        }
        if mode == 'agent_review_malformed':
            review.pop(required[0])
        response: dict[str, object] = {
            'id': 'controlled-agent-review',
            'object': 'chat.completion',
            'created': 1,
            'model': payload['model'],
            'choices': [
                {
                    'index': 0,
                    'finish_reason': 'stop',
                    'message': {
                        'role': 'assistant',
                        'content': json.dumps(review),
                        'refusal': None,
                    },
                }
            ],
            'usage': {'prompt_tokens': 50, 'completion_tokens': 10, 'total_tokens': 60},
        }
        if mode == 'agent_review_usage_unknown':
            response.pop('usage')
        return 200, response

    def _calibration_writer_response(
        self, payload: dict[str, object], mode: str
    ) -> tuple[int, object]:
        status, response = self._writer_success_response(payload, mode)
        if self.calibration_case is not None:
            candidate = cast('dict[str, object]', self.calibration_case['candidate'])
            choices = cast('list[dict[str, object]]', response['choices'])
            message = cast('dict[str, object]', choices[0]['message'])
            content = cast('dict[str, object]', json.loads(str(message['content'])))
            content['content'] = candidate['content']
            message['content'] = json.dumps(content)
        return status, response

    def _calibration_response(
        self, path: str, payload: dict[str, object]
    ) -> tuple[int, object] | None:
        if path == '/review/v1/chat/completions':
            return self._agent_review_with_count(payload)
        destinations = {
            '/calibration-observation': self.calibration_observations,
            '/calibration-progress': self.calibration_progress,
        }
        if path not in destinations:
            return None
        with self.lock:
            destinations[path].append(payload)
        return 200, {'recorded': True}

    @staticmethod
    def _writer_error_response(path: str, mode: str) -> tuple[int, object] | None:
        if path == '/fallback/v1/chat/completions' and mode == 'fallback_failure':
            return 503, {
                'error': {'message': _PRIVATE_SDK_ERROR_CANARY},
                'usage': {
                    'prompt_tokens': 50,
                    'completion_tokens': 20,
                    'total_tokens': 70,
                },
            }
        if path != '/v1/chat/completions':
            return None
        modes = {
            'writer_failure',
            'pause_failure',
            'fallback_failure',
            'writer_usage_unknown',
            'writer_usage_body_list',
            'writer_usage_list',
            'writer_usage_bool',
            'writer_usage_negative',
            'writer_usage_sum',
            'writer_usage_invalid_json',
            'writer_bad_request',
            'writer_unauthorized',
        }
        if mode not in modes:
            return None
        if mode == 'writer_usage_body_list':
            return 503, [{'error': {'message': _PRIVATE_SDK_ERROR_CANARY}}]
        if mode == 'writer_usage_invalid_json':
            return 503, _PRIVATE_SDK_ERROR_CANARY.encode()
        usage: object = {
            'prompt_tokens': 40,
            'completion_tokens': 0,
            'total_tokens': 40,
        }
        malformed: dict[str, object] = {
            'writer_usage_list': [40],
            'writer_usage_bool': {
                'prompt_tokens': True,
                'completion_tokens': 0,
                'total_tokens': 1,
            },
            'writer_usage_negative': {
                'prompt_tokens': -1,
                'completion_tokens': 0,
                'total_tokens': -1,
            },
            'writer_usage_sum': {
                'prompt_tokens': 40,
                'completion_tokens': 0,
                'total_tokens': 41,
            },
        }
        usage = malformed.get(mode, usage)
        body: dict[str, object] = {
            'error': {'message': _PRIVATE_SDK_ERROR_CANARY, 'type': 'server_error'},
        }
        if mode != 'writer_usage_unknown':
            body['usage'] = usage
        status = {'writer_bad_request': 400, 'writer_unauthorized': 401}.get(mode, 503)
        return status, body

    @staticmethod
    def _writer_success_response(
        payload: dict[str, object], mode: str
    ) -> tuple[int, dict[str, object]]:
        messages = cast('list[dict[str, object]]', payload['messages'])
        request = cast('dict[str, object]', json.loads(str(messages[-1]['content'])))
        content = {
            'block_key': request['block_key'],
            'ordinal': request['ordinal'],
            'intent': None,
            'content': 'Observe o conceito e tente organizar seu raciocínio em etapas.',
        }
        content.update(
            {
                'writer_blank_content': {'content': '   '},
                'writer_wrong_key': {'block_key': 'unmatched-private-candidate'},
                'writer_wrong_ordinal': {'ordinal': 9999},
            }.get(mode, {})
        )
        serialized = (
            'not-json' if mode == 'writer_invalid_json' else json.dumps(content)
        )
        response: dict[str, object] = {
            'id': 'controlled-writer',
            'object': 'chat.completion',
            'created': 1,
            'model': 'controlled-writer',
            'choices': [
                {
                    'index': 0,
                    'finish_reason': 'stop',
                    'message': {
                        'role': 'assistant',
                        'content': serialized,
                        'refusal': None,
                    },
                }
            ],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 20,
                'total_tokens': 120,
            },
        }
        if mode == 'writer_success_usage_missing':
            response.pop('usage')
        return 200, response

    def _control_response(
        self, path: str, payload: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        if path == '/configuration':
            return 200, {
                'mode': self.mode,
                'reranker_cache_folder': self.reranker_cache_folder,
                'calibration_case': self.calibration_case,
                'calibration_thresholds': self.calibration_thresholds,
                'calibration_review_ordinal': len(self.calibration_observations),
            }
        return (403 if payload.get('account_id') in self.revoked_accounts else 200), {
            'checked': True
        }

    @staticmethod
    def _review_response(
        payload: dict[str, object],
        mode: str,
        review_count: int,
    ) -> tuple[int, dict[str, object]]:
        if mode in {'review_unavailable', 'review_bad_request'}:
            return 400 if mode == 'review_bad_request' else 503, {
                'error': 'controlled unavailable',
                'usage': {
                    'prompt_tokens': 50,
                    'completion_tokens': 10,
                    'total_tokens': 60,
                },
            }
        if mode in {'review_transient', 'pause_review_retry'} and review_count <= 2:
            return 429, {
                'error': 'controlled rate limit',
                'usage': {
                    'prompt_tokens': 50,
                    'completion_tokens': 10,
                    'total_tokens': 60,
                },
            }
        choice = 'approved'
        if mode in {'reject', 'pause_quality'} or (
            mode == 'correct' and review_count == 1
        ):
            choice = 'rejected'
        questions = cast('dict[str, object]', payload['questions'])
        answers: dict[str, dict[str, object]] = {
            key: {
                'type': 'choice',
                'choice': choice,
                'confidence': 0.99,
                'probabilities': {
                    'approved': 0.99 if choice == 'approved' else 0.005,
                    'rejected': 0.99 if choice == 'rejected' else 0.005,
                    'inconclusive': 0.005,
                },
            }
            for key in questions
        }
        if mode == 'malformed_review':
            answers.pop(next(iter(answers)))
        _ControlledInference._apply_review_boundary(answers, mode)
        _ControlledInference._malform_review(answers, mode)
        return 200, {
            'answers': answers,
            'id': 'controlled-review',
            'usage': {
                'prompt_tokens': 50,
                'completion_tokens': 10,
                'total_tokens': 61 if mode == 'review_usage_sum_mismatch' else 60,
            },
        }

    @staticmethod
    def _apply_review_boundary(
        answers: dict[str, dict[str, object]], mode: str
    ) -> None:
        if not mode.startswith('review_boundary:'):
            return
        _, criterion, confidence, choice = mode.split(':')
        answers[criterion].update(
            {
                'choice': choice,
                'confidence': float(confidence),
                'probabilities': {
                    option: 0.99 if option == choice else 0.005
                    for option in ('approved', 'rejected', 'inconclusive')
                },
            }
        )

    @staticmethod
    def _malform_review(answers: dict[str, dict[str, object]], mode: str) -> None:
        first = answers[next(iter(answers))]
        changes: dict[str, dict[str, object]] = {
            'review_invalid_confidence': {'confidence': 1.1},
            'review_invalid_probabilities': {
                'probabilities': {
                    'approved': -1.0,
                    'rejected': 1.0,
                    'inconclusive': 1.0,
                }
            },
            'review_probability_sum': {
                'probabilities': {'approved': 0.0, 'rejected': 0.0, 'inconclusive': 0.0}
            },
        }
        first.update(changes.get(mode, {}))
        if mode == 'review_extra_criterion':
            answers['uncontracted_criterion'] = dict(first)

    def _review_with_barrier(
        self,
        payload: dict[str, object],
        mode: str,
        review_count: int,
    ) -> tuple[int, dict[str, object]]:
        if mode == 'pause_quality':
            self.writer_entered.set()
            if not self.writer_release.wait(timeout=30):
                return 503, {'error': 'controlled review pause timeout'}
        return self._review_response(payload, mode, review_count)

    def _backoff_response(self) -> tuple[int, dict[str, object]]:
        with self.lock:
            pause = self.mode == 'pause_review_retry'
        if pause:
            self.writer_entered.set()
            if not self.writer_release.wait(timeout=30):
                return 503, {'error': 'controlled backoff pause timeout'}
        return 200, {'waited': True}

    def _accounting_response(
        self, payload: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        with self.lock:
            self.accounting_requests.append(payload)
            key = (
                cast('str', payload['operation_key']),
                cast('str', payload['attempt_id']),
            )
            self.effective_usage[key] = max(
                self.effective_usage.get(key, 0),
                cast('int', payload['used_tokens']),
            )
            pause = self.mode == 'pause_accounting'
        if pause:
            self.accounting_entered.set()
            if not self.accounting_release.wait(timeout=30):
                return 503, {'error': 'controlled accounting pause timeout'}
        return 200, {'accepted': True}

    def _telemetry_response(
        self, payload: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        with self.lock:
            self.metadata_requests.append(payload)
            pause = self.mode == 'pause_finalize' and payload.get('name') == 'persist'
        if pause:
            self.accounting_entered.set()
            if not self.accounting_release.wait(timeout=30):
                return 503, {'error': 'controlled finalization pause timeout'}
        return 503, {'error': 'controlled telemetry unavailable'}


class _ThrowingTelemetryClient:
    _endpoint: str

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def start_span(
        self,
        *,
        name: str,
        metadata: dict[str, str | int | float],
        input: object | None = None,
        output: object | None = None,
        trace_context: TraceContext | None = None,
    ) -> Never:
        observation: dict[str, object] = {'name': name, 'metadata': metadata}
        if trace_context is not None:
            observation['trace_context'] = trace_context
        if input is not None:
            observation['input'] = input
        if output is not None:
            observation['output'] = output
        httpx.post(f'{self._endpoint}/telemetry', json=observation).raise_for_status()
        raise RuntimeError('controlled telemetry failure')

    def start_generation(
        self,
        *,
        trace_context: TraceContext | None = None,
        name: str,
        model: str,
        metadata: dict[str, str | int | float],
        usage_details: dict[str, int] | None,
        cost_details: dict[str, float] | None,
    ) -> Never:
        httpx.post(
            f'{self._endpoint}/telemetry',
            json={
                'name': name,
                'trace_context': trace_context,
                'model': model,
                'metadata': metadata,
                'usage_details': usage_details,
                'cost_details': cost_details,
            },
        ).raise_for_status()
        raise RuntimeError('controlled telemetry failure')


class _LegacyOptionalObserverConsumer:
    """Test-only legacy port consumer retaining native inference and accounting."""

    def __init__(self, workflow: AgnoAnswerMentorMessageWorkflow) -> None:
        self._workflow: AgnoAnswerMentorMessageWorkflow = workflow

    def run(
        self,
        request: MentorGenerationRequest,
        usage_recorder: Callable[['MentorInferenceUsage'], None] | None = None,
        inference_guard: Callable[[], None] | None = None,
        progress_recorder: Callable[['MentorWorkflowStep'], None] | None = None,
    ) -> MentorResponseBlock:
        assert usage_recorder is not None
        assert inference_guard is not None
        assert progress_recorder is not None
        # Spec11 keeps this observer optional for callers using the older public
        # signature. Native calls still execute the real fresh guard and sink.
        return self._workflow.run(request, usage_recorder, inference_guard)


def _observe_native_steps(endpoint: str) -> None:
    actual_step_execute = cast('Callable[..., StepOutput]', Step.execute)

    def observe_native_step(self: Step, *args: object, **kwargs: object) -> StepOutput:
        if self.name in {'write-answer', 'review-answer'}:
            httpx.post(
                f'{endpoint}/agno-step', json={'name': self.name}
            ).raise_for_status()
        return actual_step_execute(self, *args, **kwargs)

    Step.execute = observe_native_step


def _configure_native_faq_reranker(endpoint: str) -> object:
    from sentence_transformers import CrossEncoder
    import sentence_transformers
    from shifu.intelligence.providers.retrieval.sentence_transformers.sentence_transformers_mentor_faq_reranker_provider import (
        SentenceTransformersMentorFaqRerankerProvider,
    )

    configuration = httpx.post(f'{endpoint}/configuration', json={}).json()
    mode = configuration['mode']
    if mode == 'reranker_invalid_score':

        def invalid_scores(
            sentences: list[tuple[str, str]], **kwargs: object
        ) -> list[float]:
            del kwargs
            return [float('nan')] * len(sentences)

        patch.object(CrossEncoder, 'predict', side_effect=invalid_scores).start()
    if mode == 'reranker_over_capacity':
        original = cast('Callable[..., CrossEncoder]', CrossEncoder)

        def bounded_constructor(*args: object, **kwargs: object) -> CrossEncoder:
            kwargs['max_length'] = 1
            return original(*args, **kwargs)

        patch.object(
            sentence_transformers, 'CrossEncoder', side_effect=bounded_constructor
        ).start()
    return SentenceTransformersMentorFaqRerankerProvider(
        cache_folder=configuration['reranker_cache_folder']
        if mode == 'reranker_missing_cache'
        else None,
        local_files_only=True,
    )


def create_mentor_test_app() -> FastAPI:
    """Factory loaded only by the fixture-owned child, never production composition."""
    from shifu.app import FastAPIApp
    import shifu.app as app_module
    from shifu.intelligence.core.use_cases.process_mentor_response_use_case import (
        ProcessMentorResponseUseCase,
    )
    from shifu.composition.lazy_mentor_route_provider import LazyMentorRouteProvider
    import shifu.intelligence.providers.mentor_review_provider.openrouter.openrouter_jev_mentor_review_provider as review_module
    from shifu.curriculum.database.sqlalchemy.curriculum_database import (
        SqlalchemyCurriculumDatabase,
    )
    from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
        CurriculumMentorCatalogProvider,
    )

    job_logger = logging.getLogger(
        'shifu.intelligence.messaging.inngest.jobs.answer_mentor_message_job'
    )
    job_logger.addHandler(logging.StreamHandler(sys.stdout))
    job_logger.setLevel(logging.INFO)
    job_logger.propagate = False

    from agno.utils.log import agent_logger

    class _DiagnosedProcess(ProcessMentorResponseUseCase):
        def _process(self, attempt: MentorResponseAttempt) -> MentorResponseStatus:
            try:
                return super()._process(attempt)
            except Exception as error:
                frame = error.__traceback__
                while frame is not None and frame.tb_next is not None:
                    frame = frame.tb_next
                location = (
                    f'{Path(frame.tb_frame.f_code.co_filename).name}:{frame.tb_frame.f_code.co_name}:{frame.tb_lineno}'
                    if frame is not None
                    else 'unknown'
                )
                job_logger.error(  # noqa: TRY400 - Never emit private exception text or stack.
                    'mentor_test_process_error kind=%s location=%s',
                    type(error).__name__,
                    location,
                )
                raise
            finally:
                agent_logger.warning(_PUBLIC_SDK_LOG_MARKER)

    app_module.ProcessMentorResponseUseCase = _DiagnosedProcess

    endpoint = os.environ['SHIFU_MENTOR_TEST_ENDPOINT']
    _observe_native_steps(endpoint)
    actual_backoff = review_module.sleep

    def controlled_backoff(seconds: float) -> None:
        httpx.post(
            f'{endpoint}/review-backoff', json={'stage': 'review_backoff'}
        ).raise_for_status()
        actual_backoff(seconds)

    review_module.sleep = controlled_backoff
    engine = Session.create_database_engine()
    repository = MentorEmbeddingsDatabaseRepository(
        SqlalchemyIntelligenceDatabase(engine)
    )
    embeddings = SentenceTransformersEmbeddingsProvider()
    resources = MentorResources()
    resources.bind_catalog_version(())
    startup_mode = httpx.post(f'{endpoint}/configuration', json={}).json()['mode']
    reranker = cast(
        'MentorFaqRerankerProvider', _configure_native_faq_reranker(endpoint)
    )
    telemetry = LangfuseMentorTelemetryProvider(
        None
        if startup_mode == 'telemetry_disabled'
        else _ThrowingTelemetryClient(endpoint),
        capture_content=startup_mode != 'telemetry_metadata_only',
    )
    catalog = CurriculumMentorCatalogProvider(SqlalchemyCurriculumDatabase(engine))
    preprocessor = SpacyMentorTextPreprocessorProvider()
    stable_route = LazyMentorRouteProvider(
        SqlalchemyIntelligenceDatabase(engine), catalog, telemetry
    )

    class _CurrentTestRoute:
        def route(
            self, content: str, context: MentorContextSnapshot
        ) -> MentorRouteResult:
            current_resources = MentorResources()
            projection = catalog.read_projection()
            configuration = httpx.post(f'{endpoint}/configuration', json={}).json()
            failure_mode = str(configuration['mode']).startswith('reranker_')
            if (not projection and not failure_mode) or configuration[
                'mode'
            ] == 'lazy_catalog':
                return stable_route.route(content, context)
            current_resources.bind_catalog_version(projection)
            return LocalMentorRouteProvider(
                embeddings,
                repository,
                preprocessor,
                current_resources,
                telemetry=telemetry,
                catalog_provider=catalog,
                reranker_provider=reranker,
            ).route(content, context)

    route: MentorRouteProvider = _CurrentTestRoute()
    writer = MentorWriterAgent(
        MentorOpenAIChat(
            id='controlled-writer',
            base_url=f'{endpoint}/v1',
            api_key='disposable-test-key',
            max_retries=0,
            retries=0,
            store=False,
        )
    )
    review: MentorReviewProvider = OpenrouterJevMentorReviewProvider(
        httpx.Client(),
        '' if startup_mode == 'review_key_missing' else 'disposable-test-key',
        f'{endpoint}/decisions',
        resources.manifest.review_thresholds,
    )
    fallback = MentorWriterAgent(
        MentorOpenAIChat(
            id='controlled-approved-fallback',
            base_url=f'{endpoint}/fallback/v1',
            api_key='disposable-test-key',
            max_retries=0,
            retries=0,
            store=False,
        )
    )
    workflow: AnswerMentorMessageWorkflow | None = None
    if startup_mode != 'unavailable_workflow':
        native_workflow = AgnoAnswerMentorMessageWorkflow(
            writer,
            review,
            fallback_writer=fallback,
            fallback_privacy_verified=True,
            telemetry=telemetry,
        )
        workflow = (
            _LegacyOptionalObserverConsumer(native_workflow)
            if startup_mode == 'legacy_optional_observer'
            else native_workflow
        )
    return FastAPIApp.register(
        database_engine=engine,
        mentor_access_provider=_Access(endpoint),
        mentor_telemetry_provider=telemetry,
        mentor_route_provider=route,
        answer_mentor_message_workflow=workflow,
    )


@pytest.fixture(scope='session')
def controlled_mentor_endpoint() -> Iterator[tuple[_ControlledInference, str]]:
    state = _ControlledInference()

    class _Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            payload = cast(
                'dict[str, object]',
                json.loads(self.rfile.read(int(self.headers['content-length']))),
            )
            if self.path == '/agno-step':
                assert set(payload) == {'name'}
                name = payload['name']
                assert name in {'write-answer', 'review-answer'}
                with state.lock:
                    state.native_steps.append(cast('str', name))
                status, body = 200, {}
            else:
                status, body = state.respond(self.path, payload)
            self.send_response(status)
            self.send_header('content-type', 'application/json')
            self.end_headers()
            encoded = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(('127.0.0.1', 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f'http://127.0.0.1:{server.server_port}'
    previous = os.environ.get('SHIFU_MENTOR_TEST_ENDPOINT')
    os.environ['SHIFU_MENTOR_TEST_ENDPOINT'] = endpoint
    try:
        yield state, endpoint
    finally:
        if previous is None:
            os.environ.pop('SHIFU_MENTOR_TEST_ENDPOINT', None)
        else:
            os.environ['SHIFU_MENTOR_TEST_ENDPOINT'] = previous
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope='session')
def inngest_app_target(
    controlled_mentor_endpoint: tuple[_ControlledInference, str],
) -> tuple[str, bool]:
    del controlled_mentor_endpoint
    return (
        'tests.fixtures.mentor_job_fixture:create_mentor_test_app',
        True,
    )


@pytest.fixture(scope='session')
def mentor_local_embeddings() -> SentenceTransformersEmbeddingsProvider:
    return SentenceTransformersEmbeddingsProvider()


@pytest.fixture
def prepared_mentor_index(
    inngest_fixture: 'InngestFixture',
) -> Iterator[None]:
    completed = run_preparation_cli(inngest_fixture)
    assert completed.returncode == 0, 'Isolated Mentor preparation CLI failed.'
    resources = MentorResources()
    resources.bind_catalog_version(())
    assert f'Mentor index activated: {resources.version}' in completed.stdout
    with inngest_fixture.inspection_session() as session:
        active = session.scalars(
            select(MentorEmbeddingVersionModel).where(
                MentorEmbeddingVersionModel.active.is_(True)
            )
        ).all()
        assert len(active) == 1 and active[0].version == resources.version
    yield


def run_preparation_cli(
    fixture: 'InngestFixture', package_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment['DATABASE_URL'] = fixture.database_url
    if package_root is not None:
        environment['PYTHONPATH'] = str(package_root)
    command = [sys.executable]
    command.extend(['-m', 'shifu.mentor_indexes'])
    return subprocess.run(  # noqa: S603 - Execute the fixed application CLI in the fixture-owned isolated environment.
        command,
        cwd=fixture.runtime_directory,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def seed_request(
    fixture: 'InngestFixture',
    content: str,
    *,
    history_pairs: int = 0,
    account_id: str | None = None,
    context_hint: dict[str, str | None] | None = None,
) -> tuple[str, str, str]:
    ids = SystemIdentifierProvider()
    session_id, learner_id, attempt_id = ids.generate(), ids.generate(), ids.generate()
    now = datetime.now(UTC)
    with fixture.inspection_session() as session:
        session.add(
            MentorSessionModel(
                id=session_id,
                account_id=account_id or ids.generate(),
                submission_key=str(uuid4()),
                content_fingerprint=hashlib.sha256(content.encode()).hexdigest(),
                title='Conversa sintética',
                title_search='conversa sintética',
                created_at=now,
                updated_at=now,
                last_activity_at=now,
                deleted_at=None,
            )
        )
        session.flush()
        from datetime import timedelta

        for index in range(history_pairs):
            message_id = ids.generate()
            session.add(
                MentorMessageModel(
                    id=message_id,
                    session_id=session_id,
                    role='learner',
                    content=f'Mensagem anterior privada {index}',
                    created_at=now - timedelta(seconds=2 * (history_pairs - index)),
                    in_reply_to_message_id=None,
                )
            )
            session.flush()
            session.add(
                MentorMessageModel(
                    id=ids.generate(),
                    session_id=session_id,
                    role='mentor',
                    content=f'Dica anterior aprovada {index}',
                    created_at=now - timedelta(seconds=2 * (history_pairs - index) - 1),
                    in_reply_to_message_id=message_id,
                )
            )
        session.add(
            MentorMessageModel(
                id=learner_id,
                session_id=session_id,
                role='learner',
                content=content,
                created_at=now,
                in_reply_to_message_id=None,
            )
        )
        session.flush()
        mentor_session = session.get(MentorSessionModel, session_id)
        assert mentor_session is not None
        session.add(
            MentorResponseAttemptModel(
                id=attempt_id,
                account_id=mentor_session.account_id,
                session_id=session_id,
                learner_message_id=learner_id,
                status='queued',
                context_hint=context_hint,
                access_revision='test-active',
                generation_keys=[],
                operation_key=str(uuid4()),
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return session_id, learner_id, attempt_id


def publish_and_wait(
    fixture: 'InngestFixture', attempt_id: str, expected_status: str
) -> None:
    event = MentorResponseRequestedEvent(
        payload=MentorResponseRequestedPayload(attempt_id=attempt_id)
    )
    event_id = SystemIdentifierProvider().generate()
    fixture.publish(event.name, {'attempt_id': event.payload.attempt_id}, event_id)

    def reached_terminal_status(session: 'SqlalchemySession') -> bool:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        return attempt is not None and attempt.status in {
            'completed',
            'failed',
            'cancelled',
        }

    fixture.wait_for_database(reached_terminal_status)
    fixture.wait_for_log(f'mentor_response_job_completed event_id={event_id}')
    with fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        assert attempt is not None
        failures = session.scalars(
            select(MentorResponseEventModel).where(
                MentorResponseEventModel.attempt_id == attempt_id,
                MentorResponseEventModel.kind == 'failed',
            )
        ).all()
        assert attempt.status == expected_status, (
            f'Unexpected terminal status: {attempt.status}; expected {expected_status}. '
            f'Failure codes: {[event.failure_code for event in failures]!r}. '
            f'FastAPI output: {fixture.output[-100:]!r}; '
            f'Inngest output: {fixture.inngest_diagnostics()}'
        )


def index_snapshot(fixture: 'InngestFixture') -> tuple[str, tuple[str, ...]]:
    with fixture.inspection_session() as session:
        active = session.scalars(
            select(MentorEmbeddingVersionModel).where(
                MentorEmbeddingVersionModel.active.is_(True)
            )
        ).all()
        assert len(active) == 1
        rows = session.scalars(
            select(MentorIndexedEmbeddingModel).order_by(
                MentorIndexedEmbeddingModel.version,
                MentorIndexedEmbeddingModel.corpus,
                MentorIndexedEmbeddingModel.reference_id,
                MentorIndexedEmbeddingModel.variation_key,
            )
        ).all()
        return active[0].version, tuple(
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


def official_snapshot(fixture: 'InngestFixture') -> dict[str, tuple[str, ...]]:
    with fixture.inspection_session() as session:
        return {
            name: tuple(
                sorted(
                    json.dumps(dict(row), sort_keys=True, default=str)
                    for row in session.execute(select(table)).mappings()
                )
            )
            for name, table in Model.metadata.tables.items()
            if name.startswith(('learning_', 'curriculum_', 'gamification_'))
        }


def assert_prepared_vectors(fixture: 'InngestFixture') -> None:
    with fixture.inspection_session() as session:
        rows = session.scalars(select(MentorIndexedEmbeddingModel)).all()
        assert rows
        for row in rows:
            vector = tuple(float(value) for value in row.vector)
            assert len(vector) == 384
            assert all(math.isfinite(value) for value in vector)
            assert math.isclose(
                sum(value * value for value in vector), 1.0, abs_tol=1e-5
            )
