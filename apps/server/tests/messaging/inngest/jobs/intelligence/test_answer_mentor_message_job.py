"""Concrete NLP/Agno/Decisions proof through the registered disposable job."""

import hashlib
import base64
import binascii
import json
import logging
import os
import sys
import subprocess
import shutil
import math
from pathlib import Path
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Lock, Thread
from time import monotonic
from typing import TYPE_CHECKING, Literal, Never, cast
from unittest.mock import patch

from agno.workflow.step import Step
from agno.workflow.types import StepOutput
from langfuse.types import TraceContext
from pydantic import TypeAdapter
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, func, select

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
from shifu.intelligence.core.domain.structures.mentor_review_result import (
    MentorReviewResult,
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
from shifu.intelligence.prepare_mentor_indexes import prepare_indexes
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


def _assert_candidate_review_observations(
    state: _ControlledInference, attempt_id: str, writers: int
) -> None:
    answers = [row for row in state.metadata_requests if row['name'] == 'mentor-answer']
    reviews = [row for row in state.metadata_requests if row['name'] == 'mentor-review']
    requests = [payload for path, payload in state.requests if path == '/decisions']
    # Transport retries review the same candidate; correction versions may be identical.
    version_requests = requests[-1:] if writers == 1 else requests
    assert len(answers) == writers
    expected_reviews = (
        0 if state.mode in {'malformed_review', 'review_unavailable'} else writers
    )
    assert len(reviews) == expected_reviews
    for version, (answer, payload) in enumerate(
        zip(answers, version_requests, strict=True)
    ):
        candidate = cast(
            'dict[str, object]',
            cast('dict[str, object]', payload['state'])['candidate'],
        )
        metadata = cast('dict[str, object]', answer['metadata'])
        assert set(metadata) == {'attempt_id', 'block_key', 'version', 'correlation_id'}
        assert metadata['attempt_id'] == attempt_id
        assert metadata['block_key'] == candidate['block_key']
        assert metadata['version'] == version
        assert (
            isinstance(metadata['correlation_id'], str) and metadata['correlation_id']
        )
        assert answer['trace_context'] == {
            'trace_id': UUID(str(metadata['correlation_id'])).hex
        }
        assert answer['output'] == candidate['content']
        assert 'input' not in answer
        if version < len(reviews):
            review = reviews[version]
            assert review['metadata'] == metadata
            assert review['trace_context'] == answer['trace_context']
            assert review['input'] == candidate['content']
            result = cast('dict[str, object]', review['output'])
            choice = (
                'rejected'
                if state.mode == 'reject' or (state.mode == 'correct' and version == 0)
                else 'approved'
            )
            assert set(result) == {'approved', 'criteria'}
            assert result['approved'] is (choice == 'approved')
            criteria = cast('dict[str, dict[str, object]]', result['criteria'])
            assert set(criteria) == set(cast('dict[str, object]', payload['questions']))
            assert len(criteria) == 6
            for criterion in criteria.values():
                assert criterion == {
                    'choice': choice,
                    'confidence': 0.99,
                    'probabilities': {
                        'approved': 0.99 if choice == 'approved' else 0.005,
                        'rejected': 0.99 if choice == 'rejected' else 0.005,
                        'inconclusive': 0.005,
                    },
                }
    encoded = json.dumps(answers + reviews, ensure_ascii=False)
    for canary in (
        'Mensagem anterior privada',
        'Como organizar meus estudos?',
        'MENTOR_DIAGNOSTIC_PRIVATE_CANARY',
        'MENTOR_MATERIAL_BODY_PRIVATE_CANARY',
        _PRIVATE_SDK_ERROR_CANARY,
    ):
        assert canary not in encoded


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
    calibration = os.environ.get('SHIFU_RUN_REAL_MENTOR_REVIEW_CALIBRATION') == '1'
    context_provider = _CalibrationContext(endpoint) if calibration else None
    if calibration:
        route = _CalibrationRoute(endpoint)
        review = _CalibrationReview(endpoint)
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
        mentor_context_provider=context_provider,
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
        'tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job:create_mentor_test_app',
        True,
    )


@pytest.fixture(scope='session')
def mentor_local_embeddings() -> SentenceTransformersEmbeddingsProvider:
    return SentenceTransformersEmbeddingsProvider()


@pytest.fixture
def prepared_mentor_index(
    inngest_fixture: 'InngestFixture',
) -> Iterator[None]:
    completed = _run_preparation_cli(inngest_fixture)
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


def _run_preparation_cli(
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
        cwd=Path(__file__).resolve().parents[5],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _seed_request(
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


def _publish_and_wait(
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


def _has_status(session: 'SqlalchemySession', attempt_id: str, status: str) -> bool:
    attempt = session.get(MentorResponseAttemptModel, attempt_id)
    return attempt is not None and attempt.status == status


def _calibration_configuration(endpoint: str) -> dict[str, object]:
    response = httpx.post(f'{endpoint}/configuration', json={})
    response.raise_for_status()
    return cast('dict[str, object]', response.json())


def _calibration_request(case: dict[str, object]) -> MentorGenerationRequest:
    return TypeAdapter(MentorGenerationRequest).validate_python(case['request'])


class _CalibrationContext:
    """Editorial authorized snapshot port; never claims Learning integration proof."""

    _endpoint: str

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def read(
        self,
        account_id: str,
        reference_ids: tuple[str, ...],
        *,
        goal_id: str | None = None,
        skill_id: str | None = None,
        competency_id: str | None = None,
        material_id: str | None = None,
        activity_id: str | None = None,
    ) -> MentorContextSnapshot:
        del (
            account_id,
            reference_ids,
            goal_id,
            skill_id,
            competency_id,
            material_id,
            activity_id,
        )
        case = cast(
            'dict[str, object]',
            _calibration_configuration(self._endpoint)['calibration_case'],
        )
        return _calibration_request(case).context


class _CalibrationRoute:
    """Frozen editorial routing input; Core gates remain active."""

    _endpoint: str

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def route(self, content: str, context: MentorContextSnapshot) -> MentorRouteResult:
        del content, context
        case = cast(
            'dict[str, object]',
            _calibration_configuration(self._endpoint)['calibration_case'],
        )
        request = _calibration_request(case)
        return MentorRouteResult(
            intents=(),
            local_blocks=request.approved_blocks,
            generation_requests=(request.requested_part,),
            clarification=None,
        )


def _calibration_semantics(request: MentorGenerationRequest) -> dict[str, object]:
    return {
        'requested_part': request.requested_part,
        'context': TypeAdapter(MentorContextSnapshot).dump_python(
            request.context, mode='json'
        ),
        'history': [
            {'role': item.role.value, 'content': item.content}
            for item in request.history
        ],
        'approved_blocks': TypeAdapter(tuple[MentorResponseBlock, ...]).dump_python(
            request.approved_blocks, mode='json'
        ),
    }


class _CalibrationReview:
    """Delegate the public review port unchanged and emit only closed observations."""

    _endpoint: str

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def review(
        self, request: MentorGenerationRequest, candidate: MentorResponseBlock
    ) -> MentorReviewResult:
        from shifu.shared.settings import get_settings

        configuration = _calibration_configuration(self._endpoint)
        case = cast('dict[str, object]', configuration['calibration_case'])
        expected = _calibration_request(case)
        assert _calibration_semantics(request) == _calibration_semantics(expected)
        assert (
            candidate.content == cast('dict[str, object]', case['candidate'])['content']
        )
        thresholds = cast('dict[str, float]', configuration['calibration_thresholds'])
        settings = get_settings()
        observation: dict[str, object] = {'case_id': case['id'], 'http_calls': 0}

        def count_request(outbound: httpx.Request) -> None:
            del outbound
            observation['http_calls'] = cast('int', observation['http_calls']) + 1
            httpx.post(
                f'{self._endpoint}/calibration-progress',
                json={
                    'case_id': case['id'],
                    'review_ordinal': configuration['calibration_review_ordinal'],
                    'http_calls': observation['http_calls'],
                },
            ).raise_for_status()

        try:
            with httpx.Client(
                timeout=30.0, event_hooks={'request': [count_request]}
            ) as client:
                result = OpenrouterJevMentorReviewProvider(
                    client,
                    settings.openrouter_api_key,
                    str(settings.openrouter_decisions_url),
                    thresholds,
                ).review(request, candidate)
        except Exception as error:
            observation['error_class'] = type(error).__name__
            try:
                httpx.post(
                    f'{self._endpoint}/calibration-observation', json=observation
                ).raise_for_status()
            except Exception as diagnostic_error:  # noqa: BLE001 - Preserve the original exception when best-effort diagnostics fail.
                _note_calibration_diagnostic_failure(error, diagnostic_error)
            raise
        else:
            observation['criteria'] = [list(item) for item in result.criteria]
            observation['approved'] = result.approved
            # Successful review without its required observation must fail closed.
            httpx.post(
                f'{self._endpoint}/calibration-observation', json=observation
            ).raise_for_status()
            return result


def _seed_calibration_request(
    fixture: 'InngestFixture', case: dict[str, object]
) -> tuple[str, str, str]:
    request = _calibration_request(case)
    session_id, learner_id, attempt_id = _seed_request(
        fixture, request.history[-1].content
    )
    with fixture.inspection_session() as session:
        learner = session.get(MentorMessageModel, learner_id)
        assert learner is not None
        learner.created_at = request.history[-1].created_at
        mapped_ids: dict[str, str] = {}
        previous_learner: str | None = None
        for item in request.history[:-1]:
            message_id = SystemIdentifierProvider().generate()
            mapped_ids[item.id] = message_id
            reply_to = None
            if item.role.value == 'mentor':
                reply_to = (
                    mapped_ids[item.in_reply_to_message_id]
                    if item.in_reply_to_message_id
                    else previous_learner
                )
                assert reply_to is not None, (
                    'Mentor history requires a persisted learner.'
                )
            else:
                previous_learner = message_id
            session.add(
                MentorMessageModel(
                    id=message_id,
                    session_id=session_id,
                    role=item.role.value,
                    content=item.content,
                    created_at=item.created_at,
                    in_reply_to_message_id=reply_to,
                )
            )
            session.flush()
        session.commit()
    return session_id, learner_id, attempt_id


def _run_calibration_case(
    fixture: 'InngestFixture',
    state: _ControlledInference,
    case: dict[str, object],
    thresholds: dict[str, float],
    report: dict[str, object] | None = None,
) -> dict[str, object]:
    state.reset('review_calibration')
    state.calibration_case = case
    state.calibration_thresholds = dict(thresholds)
    state.calibration_observations.clear()
    started = monotonic()
    attempt_id: str | None = None
    event_id: str | None = None
    try:
        _, learner_id, attempt_id = _seed_calibration_request(fixture, case)
        event_id = SystemIdentifierProvider().generate()
        return _finish_calibration_case(
            fixture, state, case, learner_id, attempt_id, event_id, started
        )
    except Exception as error:
        if report is not None:
            report['status'] = 'runtime_error'
            report['error_class'] = type(error).__name__
            try:
                report['in_flight_failure'] = _calibration_failure_snapshot(
                    fixture, state, case, error, started, attempt_id, event_id
                )
                _write_calibration_report(report)
            except Exception as diagnostic_error:  # noqa: BLE001 - Preserve the original exception when best-effort diagnostics fail.
                _note_calibration_diagnostic_failure(error, diagnostic_error, report)
        raise


def _finish_calibration_case(
    fixture: 'InngestFixture',
    state: _ControlledInference,
    case: dict[str, object],
    learner_id: str,
    attempt_id: str,
    event_id: str,
    started: float,
) -> dict[str, object]:
    event = MentorResponseRequestedEvent(
        payload=MentorResponseRequestedPayload(attempt_id=attempt_id)
    )
    fixture.publish(event.name, {'attempt_id': event.payload.attempt_id}, event_id)
    fixture.wait_for_database(
        lambda session: any(
            _has_status(session, attempt_id, status)
            for status in ('completed', 'failed', 'cancelled')
        ),
        timeout=240,
    )
    fixture.wait_for_log(f'mentor_response_job_completed event_id={event_id}')
    with fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        assert attempt is not None
        reply = session.scalar(
            select(MentorMessageModel).where(
                MentorMessageModel.in_reply_to_message_id == learner_id
            )
        )
        blocks = session.scalars(
            select(MentorResponseEventModel)
            .where(
                MentorResponseEventModel.attempt_id == attempt_id,
                MentorResponseEventModel.kind == 'block',
            )
            .order_by(MentorResponseEventModel.ordinal)
        ).all()
        generated = [
            block
            for block in blocks
            if (block.block_key or '').startswith('generated-')
        ]
        completed = attempt.status == 'completed'
        assert (reply is not None) == completed
        assert len(generated) == int(completed)
        if generated:
            assert (
                generated[0].content
                == cast('dict[str, object]', case['candidate'])['content']
            )
        receipts = attempt.usage_calls or []
        result: dict[str, object] = {
            'case_id': case['id'],
            'case_sha256': _calibration_case_digest(case),
            'partition': case['partition'],
            'labels': case['labels'],
            'observations': list(state.calibration_observations),
            'status': attempt.status,
            'published': completed,
            'writer_calls': sum(
                path == '/v1/chat/completions' for path, _ in state.requests
            ),
            'receipt_count': len(receipts),
            'usage_receipts': receipts,
            'usage_provenance': {
                'jev': 'genuine_remote_response_metadata_or_unknown',
                'primary': 'controlled_synthetic_writer_receipt',
                'fallback': 'controlled_synthetic_writer_receipt',
            },
            'http_calls': sum(
                cast('int', item['http_calls'])
                for item in state.calibration_observations
            ),
            'elapsed_seconds': round(monotonic() - started, 3),
        }
    return result


def _note_calibration_diagnostic_failure(
    original_error: Exception,
    diagnostic_error: Exception,
    report: dict[str, object] | None = None,
) -> None:
    error_class = type(diagnostic_error).__name__
    original_error.add_note(f'calibration_diagnostic_error_class={error_class}')
    if report is not None:
        report['diagnostic_error_class'] = error_class


def _calibration_failure_snapshot(
    fixture: 'InngestFixture',
    state: _ControlledInference,
    case: dict[str, object],
    error: Exception,
    started: float,
    attempt_id: str | None,
    event_id: str | None,
) -> dict[str, object]:
    with state.lock:
        observations = list(state.calibration_observations)
        progress = list(state.calibration_progress)
        writer_calls = sum(path == '/v1/chat/completions' for path, _ in state.requests)
    review_attempts: dict[int, int] = {}
    for item in progress:
        ordinal = cast('int', item['review_ordinal'])
        review_attempts[ordinal] = max(
            review_attempts.get(ordinal, 0), cast('int', item['http_calls'])
        )
    snapshot: dict[str, object] = {
        'case_id': case['id'],
        'case_sha256': _calibration_case_digest(case),
        'partition': case['partition'],
        'attempt_id': attempt_id,
        'event_id': event_id,
        'error_class': type(error).__name__,
        'elapsed_seconds': round(monotonic() - started, 3),
        'writer_calls_observed': writer_calls,
        'review_versions_observed': len(observations),
        'review_http_attempts_started_observed': sum(review_attempts.values()),
        'review_http_calls_in_completed_observations': sum(
            cast('int', item['http_calls']) for item in observations
        ),
        'review_progress': progress,
        'review_observations': observations,
        'absence_of_observation_does_not_prove_no_remote_call': True,
        'quality_verdict': 'interrupted_not_evaluated',
        'attempt_status': 'not_seeded' if attempt_id is None else 'unknown',
    }
    if attempt_id is not None:
        _capture_calibration_failure_attempt(fixture, attempt_id, snapshot)
    return snapshot


def _capture_calibration_failure_attempt(
    fixture: 'InngestFixture', attempt_id: str, snapshot: dict[str, object]
) -> None:
    try:
        with fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            if attempt is None:
                snapshot['attempt_status'] = 'missing'
                return
            snapshot['attempt_status'] = attempt.status
            snapshot['attempt_terminal'] = attempt.status in {
                'completed',
                'failed',
                'cancelled',
            }
            snapshot['usage_receipts'] = attempt.usage_calls or []
            snapshot['receipt_count'] = len(attempt.usage_calls or [])
    except Exception as inspection_error:  # noqa: BLE001 - Diagnostic collection must preserve the original failure.
        snapshot['attempt_inspection_error_class'] = type(inspection_error).__name__


def _calibration_metrics(
    results: list[dict[str, object]], criterion: str, threshold: float
) -> dict[str, object]:
    selected = 0
    false_positives = 0
    positive_labels = 0
    for result in results:
        labels = cast('dict[str, str]', result['labels'])
        positive_labels += labels[criterion] == 'approved'
        observations = cast('list[dict[str, object]]', result['observations'])
        if not observations or 'criteria' not in observations[0]:
            continue
        decisions = {
            str(item[0]): (str(item[1]), float(str(item[2])))
            for item in cast('list[list[object]]', observations[0]['criteria'])
        }
        choice, confidence = decisions[criterion]
        accepted = choice == 'approved' and confidence >= threshold
        selected += accepted
        false_positives += accepted and labels[criterion] != 'approved'
    return {
        'selected': selected,
        'false_positives': false_positives,
        'positive_labels': positive_labels,
        'false_negatives': positive_labels - selected + false_positives,
        'precision': (selected - false_positives) / selected if selected else None,
        'coverage': selected / len(results) if results else 0,
        'abstention': 1 - selected / len(results) if results else 1,
    }


def _select_calibration_thresholds(
    results: list[dict[str, object]], criteria: tuple[str, ...]
) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for criterion in criteria:
        for hundredths in range(50, 96, 5):
            threshold = hundredths / 100
            metrics = _calibration_metrics(results, criterion, threshold)
            if (
                cast('int', metrics['selected']) >= 12
                and metrics['false_positives'] == 0
                and _calibration_criterion_versions_safe(results, criterion, threshold)
            ):
                thresholds[criterion] = threshold
                break
    return thresholds


def _calibration_criterion_versions_safe(
    results: list[dict[str, object]], criterion: str, threshold: float
) -> bool:
    return all(
        str(item[1]) != 'approved'
        or float(str(item[2])) < threshold
        or cast('dict[str, str]', result['labels'])[criterion] == 'approved'
        for result in results
        for observation in cast('list[dict[str, object]]', result['observations'])
        for item in cast('list[list[object]]', observation.get('criteria', []))
        if str(item[0]) == criterion
    )


def _validate_calibration_matrix(
    cases: list[dict[str, object]], criteria: tuple[str, ...]
) -> None:
    assert len(cases) == 96 and len({case['id'] for case in cases}) == 96
    families: dict[str, set[str]] = {}
    for partition in ('calibration', 'held_out'):
        selected = [case for case in cases if case['partition'] == partition]
        assert len(selected) == 48
        assert {
            category: sum(case['category'] == category for case in selected)
            for category in ('approved', 'violation', 'inconclusive')
        } == {'approved': 24, 'violation': 18, 'inconclusive': 6}
        families[partition] = {str(case['family_id']) for case in selected}
        for criterion in criteria:
            assert (
                sum(
                    case['category'] == 'violation'
                    and case['primary_criterion'] == criterion
                    for case in selected
                )
                == 3
            )
            assert (
                sum(
                    case['category'] == 'inconclusive'
                    and case['primary_criterion'] == criterion
                    for case in selected
                )
                == 1
            )
        _validate_calibration_cases(selected, criteria)
    assert families['calibration'].isdisjoint(families['held_out'])


def _validate_calibration_cases(
    cases: list[dict[str, object]], criteria: tuple[str, ...]
) -> None:
    for case in cases:
        request = _calibration_request(case)
        _validate_calibration_history(request)
        candidate = TypeAdapter(MentorResponseBlock).validate_python(case['candidate'])
        labels = cast('dict[str, str]', case['labels'])
        assert set(labels) == set(criteria)
        assert set(labels.values()) <= {'approved', 'rejected', 'inconclusive'}
        assert request.history and request.history[-1].role.value == 'learner'
        assert request.correction is None and candidate.content.strip()
    for approved in (True, False):
        prefix_families = {
            str(case['family_id'])
            for case in cases
            if (case['category'] == 'approved') == approved
            and (
                len(_calibration_request(case).history) > 1
                or _calibration_request(case).approved_blocks
            )
        }
        assert len(prefix_families) >= 2


def _calibration_joint_metrics(results: list[dict[str, object]]) -> dict[str, object]:
    positives = sum(
        all(
            label == 'approved'
            for label in cast('dict[str, str]', result['labels']).values()
        )
        for result in results
    )
    selected = sum(bool(result['published']) for result in results)
    false_positives = sum(
        bool(result['published'])
        and any(
            label != 'approved'
            for label in cast('dict[str, str]', result['labels']).values()
        )
        for result in results
    )
    return {
        'positive_labels': positives,
        'selected': selected,
        'false_positives': false_positives,
        'false_negatives': positives - selected + false_positives,
        'precision': (selected - false_positives) / selected if selected else None,
        'coverage': selected / len(results) if results else 0,
        'abstention': 1 - selected / len(results) if results else 1,
    }


def _calibration_held_out_passes(
    results: list[dict[str, object]], thresholds: dict[str, float]
) -> bool:
    criterion_passes = all(
        cast('int', metrics['selected']) >= 12 and metrics['false_positives'] == 0
        for criterion, threshold in thresholds.items()
        for metrics in [_calibration_metrics(results, criterion, threshold)]
    )
    all_versions_safe = all(
        str(item[1]) != 'approved'
        or float(str(item[2])) < thresholds[str(item[0])]
        or cast('dict[str, str]', result['labels'])[str(item[0])] == 'approved'
        for result in results
        for observation in cast('list[dict[str, object]]', result['observations'])
        for item in cast('list[list[object]]', observation.get('criteria', []))
    )
    complete = len(results) == 48 and all(
        1 <= len(cast('list[dict[str, object]]', result['observations'])) <= 2
        and result['writer_calls']
        == len(cast('list[dict[str, object]]', result['observations']))
        and all(
            'criteria' in observation
            for observation in cast('list[dict[str, object]]', result['observations'])
        )
        for result in results
    )
    joint = _calibration_joint_metrics(results)
    return (
        cast('int', joint['selected']) >= 12
        and complete
        and all_versions_safe
        and criterion_passes
        and all(
            not result['published']
            or all(
                value == 'approved'
                for value in cast('dict[str, str]', result['labels']).values()
            )
            for result in results
        )
    )


def _write_calibration_report(report: dict[str, object]) -> None:
    report_path = Path('/tmp/shifu-mentor-jev-calibration-report.json')  # noqa: S108 - Closed synthetic metadata only; no prompts or credentials.
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


def _calibration_case_digest(case: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            case, sort_keys=True, separators=(',', ':'), ensure_ascii=False
        ).encode()
    ).hexdigest()


def _validate_calibration_history(request: MentorGenerationRequest) -> None:
    learners: set[str] = set()
    for message in request.history:
        if message.role.value == 'learner':
            learners.add(message.id)
        else:
            assert learners, 'Mentor history requires an earlier learner.'
            assert (
                message.in_reply_to_message_id is None
                or message.in_reply_to_message_id in learners
            )


def _validate_calibration_checkpoint_result(
    result: dict[str, object], case: dict[str, object], criteria: tuple[str, ...]
) -> None:
    assert result['case_id'] == case['id'] and result['partition'] == 'calibration'
    assert result['labels'] == case['labels']
    assert result['status'] in {'completed', 'failed'}
    assert type(result['published']) is bool
    assert result['published'] == (result['status'] == 'completed')
    observations = cast('list[dict[str, object]]', result['observations'])
    assert 1 <= len(observations) <= 2 and result['writer_calls'] == len(observations)
    for observation in observations:
        _validate_calibration_checkpoint_observation(
            observation, str(case['id']), criteria
        )
    assert result['http_calls'] == sum(
        cast('int', item['http_calls']) for item in observations
    )
    assert type(result['receipt_count']) is int
    receipts = cast('list[dict[str, object]]', result['usage_receipts'])
    assert len(receipts) == result['receipt_count']


def _validate_calibration_checkpoint_observation(
    observation: dict[str, object], case_id: str, criteria: tuple[str, ...]
) -> None:
    assert 'error_class' not in observation and observation['case_id'] == case_id
    assert type(observation['approved']) is bool
    assert (
        type(observation['http_calls']) is int and 1 <= observation['http_calls'] <= 3
    )
    decisions = TypeAdapter(
        list[tuple[str, Literal['approved', 'rejected', 'inconclusive'], float]]
    ).validate_json(json.dumps(observation['criteria']), strict=True)
    assert len(decisions) == len(criteria) and {item[0] for item in decisions} == set(
        criteria
    )
    assert all(0 <= confidence <= 1 for _, _, confidence in decisions)


def _resume_calibration_checkpoint(
    cases: list[dict[str, object]],
    report: dict[str, object],
    criteria: tuple[str, ...],
) -> list[dict[str, object]]:
    report_path = os.environ.get('SHIFU_MENTOR_REVIEW_CALIBRATION_RESUME_REPORT')
    corpus_path = os.environ.get('SHIFU_MENTOR_REVIEW_CALIBRATION_RESUME_CORPUS')
    if report_path is None and corpus_path is None:
        return []
    assert report_path and corpus_path, 'Resume requires both immutable original files.'
    original_report_bytes = Path(report_path).read_bytes()
    original_report = cast('dict[str, object]', json.loads(original_report_bytes))
    original_corpus_bytes = Path(corpus_path).read_bytes()
    original_corpus = cast('dict[str, object]', json.loads(original_corpus_bytes))
    assert (
        hashlib.sha256(original_corpus_bytes).hexdigest()
        == original_report['corpus_sha256']
    )
    for key in (
        'model',
        'rubric_provider_source_sha256',
        'manifest_sha256',
        'current_thresholds',
        'candidate_grid',
        'minimum_selected',
    ):
        assert original_report[key] == report[key], (
            'Resume changed model, rubric, manifest or protocol.'
        )
    assert original_report['status'] == 'runtime_error'
    assert (
        'selected_thresholds' not in original_report
        and 'held_out_metrics' not in original_report
    )
    original_cases = cast('list[dict[str, object]]', original_corpus['cases'])
    assert [case['id'] for case in original_cases] == [case['id'] for case in cases]
    results = cast('list[dict[str, object]]', original_report['results'])
    assert len(results) == 22, 'Only the diagnosed 22-case completed prefix can resume.'
    calibration = [case for case in cases if case['partition'] == 'calibration']
    original_calibration = [
        case for case in original_cases if case['partition'] == 'calibration'
    ]
    for index, result in enumerate(results):
        assert _calibration_case_digest(calibration[index]) == _calibration_case_digest(
            original_calibration[index]
        ), 'Previously evaluated input or label changed.'
        _validate_calibration_checkpoint_result(result, calibration[index], criteria)
    report['resume_provenance'] = {
        'reason': 'isolated_fixture_history_reply_constraint_recovery_before_case_23',
        'original_corpus_sha256': original_report['corpus_sha256'],
        'original_report_sha256': hashlib.sha256(original_report_bytes).hexdigest(),
        'current_corpus_sha256': report['corpus_sha256'],
        'reused_calibration_case_ids': [result['case_id'] for result in results],
        'reused_case_sha256': {
            str(case['id']): _calibration_case_digest(case)
            for case in calibration[: len(results)]
        },
        'reused_call_count': sum(
            cast('int', result['http_calls']) for result in results
        ),
        'reused_publication_evidence': 'original_disposable_calibration_only_not_current_held_out',
        'held_out_reused': False,
        'resumed_calibration_case_ids': [
            case['id'] for case in calibration[len(results) :]
        ],
        'fresh_held_out_case_ids': [
            case['id'] for case in cases if case['partition'] == 'held_out'
        ],
    }
    return results


class TestAnswerMentorMessageJob:
    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'criterion', tuple(MentorResources().manifest.review_thresholds)
    )
    @pytest.mark.parametrize(
        ('offset', 'choice', 'status'),
        [
            (-0.001, 'approved', 'failed'),
            (0.0, 'approved', 'completed'),
            (0.001, 'approved', 'completed'),
            (0.0, 'rejected', 'failed'),
            (0.0, 'inconclusive', 'failed'),
        ],
        ids=[
            'below-approved',
            'equal-approved',
            'above-approved',
            'equal-rejected',
            'equal-inconclusive',
        ],
    )
    def test_registered_review_threshold_boundary_requires_each_approved_choice(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        criterion: str,
        offset: float,
        choice: str,
        status: str,
    ) -> None:
        thresholds = MentorResources().manifest.review_thresholds
        confidence = round(thresholds[criterion] + offset, 3)
        state, _ = controlled_mentor_endpoint
        state.reset(f'review_boundary:{criterion}:{confidence}:{choice}')
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?', history_pairs=1
        )
        _publish_and_wait(inngest_fixture, attempt_id, status)
        expected_versions = 1 if status == 'completed' else 2
        writer_calls = [
            payload
            for path, payload in state.requests
            if path == '/v1/chat/completions'
        ]
        review_calls = [
            payload for path, payload in state.requests if path == '/decisions'
        ]
        assert len(writer_calls) == len(review_calls) == expected_versions
        for payload in review_calls:
            assert set(cast('dict[str, object]', payload['questions'])) == set(
                thresholds
            )
            assert payload['provider'] == {'zdr': True, 'data_collection': 'deny'}
        first_request = cast(
            'dict[str, object]',
            cast('dict[str, object]', review_calls[0]['state'])['request'],
        )
        assert first_request['correction'] is None
        if expected_versions == 2:
            second_request = cast(
                'dict[str, object]',
                cast('dict[str, object]', review_calls[1]['state'])['request'],
            )
            assert second_request['correction']
            assert second_request['history'] == first_request['history']
            assert second_request['approved_blocks'] == first_request['approved_blocks']
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == status
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert (reply is not None) == (status == 'completed')
            blocks = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
            ).all()
            generated = [
                block
                for block in blocks
                if (block.block_key or '').startswith('generated-')
            ]
            assert len(generated) == int(status == 'completed')
            if generated:
                candidate = cast(
                    'dict[str, object]',
                    cast('dict[str, object]', review_calls[-1]['state'])['candidate'],
                )
                assert generated[0].content == candidate['content']
            usage_calls = attempt.usage_calls or []
            assert len(usage_calls) == expected_versions * 2
            assert (
                sum(cast('int', row['used_tokens']) for row in usage_calls)
                == expected_versions * 180
            )

    @pytest.mark.skipif(
        os.environ.get('SHIFU_RUN_REAL_MENTOR_REVIEW_CALIBRATION') != '1',
        reason='set SHIFU_RUN_REAL_MENTOR_REVIEW_CALIBRATION=1 for real synthetic JEV calibration',
    )
    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_review_calibration_freezes_before_independent_held_out(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        from importlib.resources import files

        corpus_bytes = (
            files('shifu.intelligence.ai.data')
            .joinpath('mentor-review-evaluation.json')
            .read_bytes()
        )
        corpus = cast('dict[str, object]', json.loads(corpus_bytes))
        provenance = cast('dict[str, object]', corpus['provenance'])
        assert provenance['synthetic'] is True
        assert provenance['contains_real_learner_data'] is False
        assert (
            provenance['editorial_review_status']
            == 'two_independent_reviews_complete_frozen_before_model_calls'
        )
        cases = cast('list[dict[str, object]]', corpus['cases'])
        criteria = tuple(MentorResources().manifest.review_thresholds)
        _validate_calibration_matrix(cases, criteria)
        current = dict(MentorResources().manifest.review_thresholds)
        data_root = Path(__file__).resolve().parents[5] / 'src/shifu/intelligence'
        provider_source = (
            data_root
            / 'providers/mentor_review_provider/openrouter/openrouter_jev_mentor_review_provider.py'
        )
        state, _ = controlled_mentor_endpoint
        report: dict[str, object] = {
            'format_version': 1,
            'corpus_sha256': hashlib.sha256(corpus_bytes).hexdigest(),
            'rubric_provider_source_sha256': hashlib.sha256(
                provider_source.read_bytes()
            ).hexdigest(),
            'manifest_sha256': hashlib.sha256(
                (data_root / 'ai/data/mentor-index-manifest.json').read_bytes()
            ).hexdigest(),
            'model': 'typesafe/jev-1.13',
            'current_thresholds': current,
            'candidate_grid': [value / 100 for value in range(50, 96, 5)],
            'minimum_selected': 12,
            'adoption_protocol': 'validate_user_fixed_thresholds',
            'results': [],
            'status': 'running_calibration',
        }
        results = _resume_calibration_checkpoint(cases, report, criteria)
        resumed_ids = {result['case_id'] for result in results}
        report['results'] = results
        _write_calibration_report(report)
        try:
            for case in cases:
                if case['partition'] == 'calibration' and case['id'] not in resumed_ids:
                    results.append(
                        _run_calibration_case(
                            inngest_fixture, state, case, current, report
                        )
                    )
                    _write_calibration_report(report)
            complete = len(results) == 48 and all(
                cast('list[dict[str, object]]', item['observations'])
                and 'criteria'
                in cast('list[dict[str, object]]', item['observations'])[0]
                for item in results
            )
            frozen = (
                _select_calibration_thresholds(results, criteria) if complete else {}
            )
            report['calibration_grid_metrics'] = {
                criterion: {
                    str(hundredths / 100): {
                        **_calibration_metrics(results, criterion, hundredths / 100),
                        'all_versions_safe': _calibration_criterion_versions_safe(
                            results, criterion, hundredths / 100
                        ),
                    }
                    for hundredths in range(50, 96, 5)
                }
                for criterion in criteria
            }
            report['grid_recommendations'] = frozen
            fixed_passes = complete and all(
                cast('int', _calibration_metrics(results, key, threshold)['selected'])
                >= 12
                and _calibration_metrics(results, key, threshold)['false_positives']
                == 0
                and _calibration_criterion_versions_safe(results, key, threshold)
                for key, threshold in current.items()
            )
            joint = _calibration_joint_metrics(results)
            fixed_passes = fixed_passes and (
                cast('int', joint['selected']) >= 12 and joint['false_positives'] == 0
            )
            frozen = dict(current) if fixed_passes else {}
            report['fixed_thresholds_metrics'] = {
                key: {
                    **_calibration_metrics(results, key, threshold),
                    'all_versions_safe': _calibration_criterion_versions_safe(
                        results, key, threshold
                    ),
                }
                for key, threshold in current.items()
            }
            report['selected_thresholds'] = frozen
            report['frozen_thresholds_sha256'] = hashlib.sha256(
                json.dumps(frozen, sort_keys=True, separators=(',', ':')).encode()
            ).hexdigest()
            report['calibration_joint_metrics'] = _calibration_joint_metrics(results)
            report['calibration_metrics'] = {
                key: _calibration_metrics(results, key, threshold)
                for key, threshold in frozen.items()
            }
            report['status'] = (
                'selection_failed'
                if set(frozen) != set(criteria)
                else 'running_held_out'
            )
            _write_calibration_report(report)
            assert set(frozen) == set(criteria), (
                'User-fixed thresholds failed calibration quality gates; held-out was not consumed.'
            )
            held_out: list[dict[str, object]] = []
            for case in cases:
                if case['partition'] == 'held_out':
                    result = _run_calibration_case(
                        inngest_fixture, state, case, frozen, report
                    )
                    results.append(result)
                    held_out.append(result)
                    _write_calibration_report(report)
            report['held_out_joint_metrics'] = _calibration_joint_metrics(held_out)
            report['held_out_metrics'] = {
                key: _calibration_metrics(held_out, key, threshold)
                for key, threshold in frozen.items()
            }
            report['status'] = (
                'passed'
                if _calibration_held_out_passes(held_out, frozen)
                else 'held_out_failed'
            )
            _write_calibration_report(report)
            assert report['status'] == 'passed', (
                'Independent held-out check failed; production thresholds must remain unchanged.'
            )
        except Exception as error:
            report['error_class'] = type(error).__name__
            if report['status'] in {'running_calibration', 'running_held_out'}:
                report['status'] = 'runtime_error'
            try:
                _write_calibration_report(report)
            except Exception as diagnostic_error:  # noqa: BLE001 - Preserve the original exception when best-effort diagnostics fail.
                _note_calibration_diagnostic_failure(error, diagnostic_error, report)
            raise
        finally:
            state.calibration_case = None

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        ('mode', 'status', 'writers', 'reviews'),
        [
            ('approve', 'completed', 1, 1),
            ('correct', 'completed', 2, 2),
            ('reject', 'failed', 2, 2),
            ('malformed_review', 'failed', 1, 1),
            ('review_transient', 'completed', 1, 3),
            ('review_unavailable', 'failed', 1, 3),
        ],
    )
    def test_registered_writer_and_cumulative_review_are_bounded(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
        status: str,
        writers: int,
        reviews: int,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        session_id, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?', history_pairs=34
        )
        _publish_and_wait(inngest_fixture, attempt_id, status)
        writer_calls = [
            payload
            for path, payload in state.requests
            if path == '/v1/chat/completions'
        ]
        review_calls = [
            payload for path, payload in state.requests if path == '/decisions'
        ]
        assert len(writer_calls) == writers
        assert len(review_calls) == reviews
        assert state.native_steps == [
            name for _ in range(writers) for name in ('write-answer', 'review-answer')
        ]
        expected_paths = ['/v1/chat/completions', '/decisions']
        if writers == 2:
            expected_paths.extend(['/v1/chat/completions', '/decisions'])
        elif reviews == 3:
            expected_paths.extend(['/decisions', '/decisions'])
        assert [path for path, _ in state.requests] == expected_paths
        _assert_candidate_review_observations(state, attempt_id, writers)
        request = cast(
            'dict[str, object]',
            cast('dict[str, object]', review_calls[-1]['state'])['request'],
        )
        history = cast('list[dict[str, object]]', request['history'])
        assert len(history) == 69
        assert history[0]['content'] == 'Mensagem anterior privada 0'
        assert history[-1]['content'] == 'Como organizar meus estudos?'
        with inngest_fixture.inspection_session() as session:
            learner = session.get(MentorMessageModel, learner_id)
            assert (
                learner is not None
                and learner.content == 'Como organizar meus estudos?'
            )
            response = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            blocks = session.scalars(
                select(MentorResponseEventModel)
                .where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
                .order_by(MentorResponseEventModel.ordinal)
            ).all()
            progress_events = session.scalars(
                select(MentorResponseEventModel)
                .where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.progress.is_not(None),
                )
                .order_by(MentorResponseEventModel.sequence)
            ).all()
            assert [event.progress for event in progress_events] == [
                step
                for _ in range(writers)
                for step in ('write-answer', 'review-answer')
            ]
            assert all(
                event.kind == 'status'
                and event.status == 'processing'
                and event.consultation is None
                and event.content is None
                for event in progress_events
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(MentorResponseEventModel)
                    .where(
                        MentorResponseEventModel.attempt_id == attempt_id,
                        MentorResponseEventModel.kind == 'consultation',
                    )
                )
                == 0
            )
            assert (response is not None) == (status == 'completed')
            local = [
                block
                for block in blocks
                if not (block.block_key or '').startswith('generated-')
            ]
            prefix = [
                {
                    'block_key': block.block_key,
                    'ordinal': block.ordinal,
                    'intent': block.intent,
                    'content': block.content,
                }
                for block in local
            ]
            for payload in review_calls:
                reviewed = cast(
                    'dict[str, object]',
                    cast('dict[str, object]', payload['state'])['request'],
                )
                assert reviewed['approved_blocks'] == prefix
                assert reviewed['history'] == history
            assert len(blocks) == len(prefix) + (status == 'completed')
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            usage_calls = cast('list[dict[str, object]]', attempt.usage_calls)
            assert (
                sum(cast('int', row['used_tokens']) for row in usage_calls)
                == writers * 120 + reviews * 60
            )
            assert (
                len({cast('str', row['call_key']) for row in usage_calls})
                == writers + reviews
            )
        assert state.accounting_requests
        assert (
            state.accounting_requests[-1]['used_tokens'] == writers * 120 + reviews * 60
        )
        accounted = dict(state.effective_usage)
        _publish_and_wait(inngest_fixture, attempt_id, status)
        assert len(state.requests) == writers + reviews
        assert state.effective_usage == accounted
        with inngest_fixture.inspection_session() as session:
            assert session.scalar(
                select(func.count())
                .select_from(MentorMessageModel)
                .where(MentorMessageModel.session_id == session_id)
            ) == 69 + (status == 'completed')

    def test_resolved_faq_does_not_add_collateral_catalog_results(self) -> None:
        from shifu.intelligence.core.domain.enums.mentor_intent import MentorIntent
        from shifu.intelligence.core.domain.structures.mentor_embedding_match import (
            MentorEmbeddingMatch,
        )
        from shifu.intelligence.core.domain.structures.mentor_indexed_embedding import (
            MentorIndexedEmbedding,
        )
        from shifu.intelligence.providers.routing.local_mentor_route_provider import (
            LocalMentorRouteProvider,
        )
        from shifu.intelligence.providers.text_preprocessing.spacy.spacy_mentor_text_preprocessor_provider import (
            SpacyMentorTextPreprocessorProvider,
        )

        question = (
            'Se eu colocar a mesma habilidade em dois objetivos diferentes, '
            'o que aprendi em um conta automaticamente no outro?'
        )
        answer = next(
            entry
            for entry in MentorResources().answers
            if entry.id == 'shifu_experience_independence'
        )

        class Embeddings:
            @staticmethod
            def embed_queries(
                texts: tuple[str, ...],
            ) -> tuple[tuple[float, ...], ...]:
                return tuple((0.0,) * 384 for _ in texts)

            embed_passages = embed_queries

        class Repository:
            @staticmethod
            def prepare_version(
                version: str, vectors: tuple[MentorIndexedEmbedding, ...]
            ) -> None:
                del version, vectors

            @staticmethod
            def activate_version(version: str) -> None:
                del version

            @staticmethod
            def find_nearest(
                corpus: str,
                version: str,
                query: tuple[float, ...],
                eligible_references: tuple[str, ...],
            ) -> tuple[MentorEmbeddingMatch, ...]:
                del version, query
                if corpus == 'intents':
                    return (
                        MentorEmbeddingMatch(
                            reference_id=MentorIntent.SEARCH_CURRICULUM.value,
                            variation_key='test',
                            similarity=1.0,
                        ),
                    )
                winner = 'shifu_experience_independence'
                runner_up = 'shifu_activity'
                return tuple(
                    MentorEmbeddingMatch(
                        reference_id=reference,
                        variation_key='test',
                        similarity=similarity,
                    )
                    for reference, similarity in ((winner, 0.99), (runner_up, 0.90))
                    if reference in eligible_references
                )

        route = LocalMentorRouteProvider(
            Embeddings(),  # type: ignore[arg-type] - deterministic unit embeddings
            Repository(),  # type: ignore[arg-type] - deterministic route candidates
            SpacyMentorTextPreprocessorProvider(),
            MentorResources(),
        )
        result = route.route(
            question,
            MentorContextSnapshot(
                goal_id=None,
                skill_experience_id=None,
                skill_id=None,
                competency_id=None,
                activity_id=None,
                skill_completed=None,
                diagnostic_in_progress=False,
                facts=(('catalog_summary', 'JavaScript essencial\nReact\nHTML e CSS'),),
                eligible_references=(),
                resolved_references=(),
                unavailable_sources=(),
            ),
        )

        assert MentorIntent.SEARCH_CURRICULUM in {
            match.intent for match in result.intents
        }
        assert [block.content for block in result.local_blocks] == [answer.answer]
        assert result.generation_requests == ()

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_product_faq_questions_and_variations_complete_without_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        answers = [
            answer for answer in MentorResources().answers if 'shifu' in answer.topics
        ]
        assert len(answers) >= 28
        for answer in answers:
            for question in (answer.question, *answer.variations):
                state.reset('approve')
                _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
                print(f'product_faq: {answer.id}: {question}', flush=True)
                _publish_and_wait(inngest_fixture, attempt_id, 'completed')
                assert state.requests == [], question
                with inngest_fixture.inspection_session() as session:
                    response = session.scalar(
                        select(MentorMessageModel).where(
                            MentorMessageModel.in_reply_to_message_id == learner_id
                        )
                    )
                    assert response is not None, question
                    assert response.content == answer.answer, question
                    attempt = session.get(MentorResponseAttemptModel, attempt_id)
                    assert attempt is not None and attempt.usage_calls == []

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'question',
        [
            'oi boa noite, eu tenho uma dúvida, o que significa Objetivo no Shifu?',
            'O que significa Objetivo no Shifu?',
            'Oi, o que é um Objetivo no Shifu?',
            'Boa noite, o que significa Objetivo no Shifu?',
            'Eu tenho uma dúvida: o que significa Objetivo no Shifu?',
        ],
    )
    def test_product_faq_neutral_prefix_preserves_local_goal_answer_without_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        question: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        expected = next(
            answer.answer
            for answer in MentorResources().answers
            if answer.id == 'shifu_goal'
        )
        _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
        with inngest_fixture.inspection_session() as session:
            learner = session.get(MentorMessageModel, learner_id)
            assert learner is not None and learner.content == question
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id,
                )
            )
            assert reply is not None and reply.content == expected
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.usage_calls == []
            blocks = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
            ).all()
            assert len(blocks) == 1 and blocks[0].content == expected
            assert not (blocks[0].block_key or '').startswith('generated-')

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_product_faq_neutral_prefix_preserves_unknown_question_for_generation(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        question = 'Boa noite, explique padrões de arquitetura hexagonal com um exemplo original'
        _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/decisions',
        ]
        writer_messages = cast(
            'list[dict[str, object]]', state.requests[0][1]['messages']
        )
        writer_request = cast(
            'dict[str, object]', json.loads(str(writer_messages[-1]['content']))
        )
        assert writer_request['requested_part'] == question
        reviewed = cast(
            'dict[str, object]',
            cast('dict[str, object]', state.requests[-1][1]['state'])['request'],
        )
        assert reviewed['requested_part'] == question
        history = cast('list[dict[str, object]]', reviewed['history'])
        assert history[-1]['content'] == question
        assert reviewed['approved_blocks'] == []
        with inngest_fixture.inspection_session() as session:
            learner = session.get(MentorMessageModel, learner_id)
            assert learner is not None and learner.content == question
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id,
                )
            )
            assert reply is not None
            assert (
                reply.content
                == 'Observe o conceito e tente organizar seu raciocínio em etapas.'
            )
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.usage_calls is not None
            assert [receipt['used_tokens'] for receipt in attempt.usage_calls] == [
                120,
                60,
            ]
        assert state.accounting_requests[-1]['used_tokens'] == 180

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        ('question', 'answer_id'),
        [
            ('Pode me explicar o papel de um Objetivo dentro do Shifu?', 'shifu_goal'),
            (
                'Gostaria de entender o significado de Habilidade na plataforma Shifu.',
                'shifu_skill',
            ),
            (
                'Por que preciso passar pelo diagnóstico antes de estudar uma Habilidade?',
                'shifu_diagnostic',
            ),
            (
                'Se pratico a mesma Habilidade em outro Objetivo, minhas tentativas são reaproveitadas?',
                'shifu_experience_independence',
            ),
        ],
    )
    def test_faq_pipeline_frozen_held_out_paraphrase_selects_exact_curated_answer(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        question: str,
        answer_id: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        expected = next(
            answer.answer
            for answer in MentorResources().answers
            if answer.id == answer_id
        )
        _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
        with inngest_fixture.inspection_session() as session:
            learner = session.get(MentorMessageModel, learner_id)
            assert learner is not None and learner.content == question
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert reply is not None and reply.content == expected
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.usage_calls == []

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        ('question', 'parts', 'require_generation'),
        [
            ('Como funciona isso no Shifu?', ('Como funciona isso no Shifu',), False),
            (
                'Não quero saber o que é um Objetivo; quero exemplos originais de arquitetura hexagonal.',
                (
                    'Não quero saber o que é um Objetivo',
                    'quero exemplos originais de arquitetura hexagonal.',
                ),
                True,
            ),
            (
                'Explique arquitetura hexagonal com um exemplo original.',
                ('Explique arquitetura hexagonal com um exemplo original.',),
                True,
            ),
            (
                'Meu Objetivo pessoal já foi concluído?',
                ('Meu Objetivo pessoal já foi concluído',),
                False,
            ),
            (
                'O que é um Objetivo na linguagem Prolog?',
                ('O que é um Objetivo na linguagem Prolog',),
                True,
            ),
        ],
    )
    def test_faq_pipeline_preserves_uncertainty_and_original_generation_parts(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        question: str,
        parts: tuple[str, ...],
        require_generation: bool,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        curated = [answer.answer for answer in MentorResources().answers]
        writer_calls = [
            payload
            for path, payload in state.requests
            if path == '/v1/chat/completions'
        ]
        if require_generation:
            assert writer_calls
        for payload in writer_calls:
            messages = cast('list[dict[str, object]]', payload['messages'])
            request = cast(
                'dict[str, object]', json.loads(str(messages[-1]['content']))
            )
            assert request['requested_part'] in parts
        with inngest_fixture.inspection_session() as session:
            learner = session.get(MentorMessageModel, learner_id)
            assert learner is not None and learner.content == question
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert reply is not None
            assert not any(answer in reply.content for answer in curated)
            blocks = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
            ).all()
            assert not any(block.content in curated for block in blocks)

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('unknown_second_part', [False, True])
    def test_faq_pipeline_multipart_keeps_local_and_generated_parts_independent(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        unknown_second_part: bool,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        second = (
            'E explique arquitetura hexagonal com um exemplo original.'
            if unknown_second_part
            else 'E o que o Shifu chama de Habilidade?'
        )
        question = 'O que é um Objetivo no Shifu? ' + second
        _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        resources = {answer.id: answer.answer for answer in MentorResources().answers}
        with inngest_fixture.inspection_session() as session:
            blocks = session.scalars(
                select(MentorResponseEventModel)
                .where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
                .order_by(MentorResponseEventModel.ordinal)
            ).all()
            assert len(blocks) == 2
            assert blocks[0].content == resources['shifu_goal']
            assert blocks[1].content == (
                'Observe o conceito e tente organizar seu raciocínio em etapas.'
                if unknown_second_part
                else resources['shifu_skill']
            )
            reply = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert reply is not None and reply.content == '\n\n'.join(
                cast('str', block.content) for block in blocks
            )
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            if not unknown_second_part:
                assert attempt.usage_calls == []
        if not unknown_second_part:
            assert state.requests == []
            return
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/decisions',
        ]
        messages = cast('list[dict[str, object]]', state.requests[0][1]['messages'])
        request = cast('dict[str, object]', json.loads(str(messages[-1]['content'])))
        assert request['requested_part'] == second
        reviewed = cast(
            'dict[str, object]',
            cast('dict[str, object]', state.requests[-1][1]['state'])['request'],
        )
        prefix = cast('list[dict[str, object]]', reviewed['approved_blocks'])
        assert len(prefix) == 1 and prefix[0]['content'] == resources['shifu_goal']

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'mode',
        ['reranker_missing_cache', 'reranker_invalid_score', 'reranker_over_capacity'],
    )
    def test_faq_pipeline_reranker_sdk_failure_abstains_without_breaking_fast_path(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        tmp_path: Path,
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        state.reranker_cache_folder = str(tmp_path)
        assert list(tmp_path.iterdir()) == []
        inngest_fixture.restart_application()
        try:
            question = 'No Shifu, para que existe um Objetivo de aprendizagem?'
            _, learner_id, attempt_id = _seed_request(inngest_fixture, question)
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
            assert state.requests == []
            with inngest_fixture.inspection_session() as session:
                reply = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert reply is not None
                assert not any(
                    answer.answer in reply.content
                    for answer in MentorResources().answers
                )
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None
                assert all(
                    row['used_tokens'] == 0 for row in (attempt.usage_calls or [])
                )
            assert all(
                receipt['used_tokens'] == 0 for receipt in state.accounting_requests
            )
            # The second terminal attempt exercises the strict semantic fast path
            # while the same failed SDK configuration remains active in the child.
            before = len(state.requests)
            _, faq_learner_id, faq_attempt_id = _seed_request(
                inngest_fixture, 'O que é um Objetivo no Shifu?'
            )
            _publish_and_wait(inngest_fixture, faq_attempt_id, 'completed')
            assert len(state.requests) == before
            with inngest_fixture.inspection_session() as session:
                reply = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == faq_learner_id
                    )
                )
                expected = next(
                    answer.answer
                    for answer in MentorResources().answers
                    if answer.id == 'shifu_goal'
                )
                assert reply is not None and reply.content == expected
                attempt = session.get(MentorResponseAttemptModel, faq_attempt_id)
                assert attempt is not None and attempt.usage_calls == []
        finally:
            state.reset('approve')
            inngest_fixture.restart_application()

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_faq_pipeline_independent_quality_reports_precision_and_coverage(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        from importlib.resources import files

        evaluation = cast(
            'dict[str, list[dict[str, object]]]',
            json.loads(
                files('shifu.intelligence.ai.data')
                .joinpath('mentor-evaluation.json')
                .read_text()
            ),
        )
        rows = evaluation['pipeline_held_out']
        resources = MentorResources()
        answers = {answer.id: answer.answer for answer in resources.answers}
        state, _ = controlled_mentor_endpoint
        selected = correct = positives_selected = 0
        for row in rows:
            state.reset('approve')
            _, learner_id, attempt_id = _seed_request(inngest_fixture, str(row['text']))
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
            with inngest_fixture.inspection_session() as session:
                reply = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert reply is not None
                matched = [
                    key for key, answer in answers.items() if answer in reply.content
                ]
                assert len(matched) <= 1
                if row['answer_id'] is None:
                    assert matched == []
                if matched:
                    selected += 1
                    assert matched == [row['answer_id']]
                    assert reply.content == answers[matched[0]]
                    assert state.requests == []
                    correct += 1
                    positives_selected += 1
        assert selected > 0 and correct / selected >= 0.95
        print(
            f'pipeline independent precision={correct}/{selected}, '
            f'positive_coverage={positives_selected}/8, '
            f'abstentions={len(rows) - selected}/{len(rows)}'
        )

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_held_out_local_precision_and_abstention_through_real_job(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        from importlib.resources import files

        evaluation = cast(
            'dict[str, list[dict[str, object]]]',
            json.loads(
                files('shifu.intelligence.ai.data')
                .joinpath('mentor-evaluation.json')
                .read_text()
            ),
        )
        assert {row['text'] for row in evaluation['held_out']}.isdisjoint(
            {row['text'] for row in evaluation['calibration']}
        )
        resources = MentorResources()
        answers = {answer.id: answer.answer for answer in resources.answers}
        selected, correct = 0, 0
        state, _ = controlled_mentor_endpoint
        for row in evaluation['held_out']:
            state.reset('approve')
            _, learner_id, attempt_id = _seed_request(inngest_fixture, str(row['text']))
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
            with inngest_fixture.inspection_session() as session:
                response = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert response is not None
                match = next(
                    (
                        key
                        for key, answer in answers.items()
                        if answer in response.content
                    ),
                    None,
                )
            if match is not None:
                selected += 1
                assert match == row['answer_id']
                correct += 1
        assert selected > 0
        assert correct / selected >= 0.95
        print(
            f'held_out local_precision={correct}/{selected}, coverage={selected}/{len(evaluation["held_out"])}, abstentions={len(evaluation["held_out"]) - selected}'
        )

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_local_multiple_intents_precede_generation(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _, _, attempt_id = _seed_request(
            inngest_fixture,
            'O que é uma lista em Python? E quantos pontos de XP eu tenho?',
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        with inngest_fixture.inspection_session() as session:
            blocks = session.scalars(
                select(MentorResponseEventModel)
                .where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
                .order_by(MentorResponseEventModel.ordinal)
            ).all()
            assert len(blocks) >= 2
            assert blocks[0].intent == 'explain_concept'
            assert any(block.intent == 'consult_gamification' for block in blocks)
        assert state.requests == []

    def test_registered_job_rejects_extra_payload_before_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        event = MentorResponseRequestedEvent(
            payload=MentorResponseRequestedPayload(
                attempt_id=SystemIdentifierProvider().generate()
            )
        )
        event_id = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            event.name,
            {'attempt_id': event.payload.attempt_id, 'unexpected': True},
            event_id,
        )
        inngest_fixture.wait_for_log(f'mentor_response_job_invalid event_id={event_id}')
        assert state.requests == []
        with inngest_fixture.inspection_session() as session:
            assert (
                session.scalar(
                    select(func.count()).select_from(MentorResponseAttemptModel)
                )
                == 0
            )
            assert (
                session.scalar(
                    select(func.count()).select_from(MentorResponseEventModel)
                )
                == 0
            )

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        ('selected_status', 'completed'), [('learning', False), ('completed', True)]
    )
    def test_generation_uses_current_goal_experience_without_borrowing_completion(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        selected_status: str,
        completed: bool,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        account_id, goal_id, skill_id, experience_id = _seed_experiences(
            inngest_fixture, selected_status
        )
        _, _, attempt_id = _seed_request(
            inngest_fixture,
            'Como organizar meus estudos?',
            account_id=account_id,
            context_hint={
                'goal_id': goal_id,
                'skill_id': skill_id,
                'competency_id': None,
                'material_id': None,
                'activity_id': None,
            },
        )
        try:
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        except Exception as error:
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                if attempt is not None:
                    created = attempt.created_at
                    updated = attempt.updated_at
                    aware = created.tzinfo is not None and updated.tzinfo is not None
                    delta = (updated - created).total_seconds() if aware else None
                    error.add_note(
                        'Mentor timestamp diagnostic: '
                        f'created_aware={created.tzinfo is not None} '
                        f'updated_aware={updated.tzinfo is not None} '
                        f'updated_minus_created_seconds={delta} '
                        f'status={attempt.status}'
                    )
            raise
        review = next(
            payload for path, payload in state.requests if path == '/decisions'
        )
        request = cast(
            'dict[str, object]', cast('dict[str, object]', review['state'])['request']
        )
        context = cast('dict[str, object]', request['context'])
        assert context['goal_id'] == goal_id
        assert context['skill_experience_id'] == experience_id
        assert context['skill_completed'] is completed
        assert context['diagnostic_in_progress'] is False
        with inngest_fixture.inspection_session() as session:
            from shifu.learning.database.sqlalchemy.models import SkillExperienceModel

            experiences = session.scalars(
                select(SkillExperienceModel).where(
                    SkillExperienceModel.skill_id == skill_id
                )
            ).all()
            assert sorted(experience.status for experience in experiences) == sorted(
                ['completed', selected_status]
            )

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_current_diagnostic_blocks_assistance_without_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        account_id, goal_id, skill_id, _ = _seed_experiences(
            inngest_fixture, 'diagnosing'
        )
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture,
            'Me dê uma dica para a atividade diagnóstica em andamento',
            account_id=account_id,
            context_hint={
                'goal_id': goal_id,
                'skill_id': skill_id,
                'competency_id': None,
                'material_id': None,
                'activity_id': None,
            },
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        with inngest_fixture.inspection_session() as session:
            response = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert response is not None
            assert 'Não posso ajudar com a Atividade diagnóstica' in response.content

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('released', [True, False])
    def test_learning_released_material_is_eligible_and_blocked_material_never_reaches_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        released: bool,
    ) -> None:
        from shifu.shared.database.seed_data import (
            SEED_ACCOUNT_ID,
            SEED_ADAPTIVE_LAB_GOAL_ID,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID,
        )

        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _seed_learning_matrix(inngest_fixture)
        competency_id = (
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID
            if released
            else SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID
        )
        material_id = (
            SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID
            if released
            else SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID
        )
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture,
            'Como organizar meus estudos?',
            account_id=SEED_ACCOUNT_ID,
            context_hint={
                'goal_id': SEED_ADAPTIVE_LAB_GOAL_ID,
                'skill_id': SEED_ADAPTIVE_LAB_SKILL_ID,
                'competency_id': competency_id,
                'material_id': material_id,
                'activity_id': None,
            },
        )
        _publish_and_wait(
            inngest_fixture, attempt_id, 'completed' if released else 'failed'
        )
        assert state.requests == []
        if released:
            with inngest_fixture.inspection_session() as session:
                response = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert response is not None
                assert 'MENTOR_DIAGNOSTIC_PRIVATE_CANARY' not in response.content
                assert 'MENTOR_MATERIAL_BODY_PRIVATE_CANARY' not in response.content
        else:
            with inngest_fixture.inspection_session() as session:
                assert (
                    session.scalar(
                        select(MentorMessageModel).where(
                            MentorMessageModel.in_reply_to_message_id == learner_id
                        )
                    )
                    is None
                )

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('ambiguous', [False, True])
    def test_explicit_goal_overrides_old_lower_hints_or_clarifies_multiple_ids(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        ambiguous: bool,
    ) -> None:
        from shifu.shared.database.seed_data import (
            SEED_ACCOUNT_ID,
            SEED_ADAPTIVE_LAB_GOAL_ID,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SEED_INITIAL_DIAGNOSTIC_GOAL_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS,
        )

        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _seed_learning_matrix(inngest_fixture)
        official_before = _official_snapshot(inngest_fixture)
        content = (
            f'Como organizar meus estudos no Objetivo {SEED_ADAPTIVE_LAB_GOAL_ID}?'
        )
        if ambiguous:
            content += f' Ou no Objetivo {SEED_INITIAL_DIAGNOSTIC_GOAL_ID}?'
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture,
            content,
            account_id=SEED_ACCOUNT_ID,
            context_hint={
                'goal_id': SEED_INITIAL_DIAGNOSTIC_GOAL_ID,
                'skill_id': SEED_ADAPTIVE_LAB_SKILL_ID,
                'competency_id': SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
                'activity_id': SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS[0],
                'material_id': None,
            },
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert _official_snapshot(inngest_fixture) == official_before
        if ambiguous:
            assert state.requests == []
            with inngest_fixture.inspection_session() as session:
                response = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert response is not None
                assert 'um único Objetivo' in response.content
                assert 'uma única Habilidade' in response.content
                assert (
                    SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS[0] not in response.content
                )
                assert 'MENTOR_DIAGNOSTIC_PRIVATE_CANARY' not in response.content
                assert 'MENTOR_MATERIAL_BODY_PRIVATE_CANARY' not in response.content
        else:
            assert state.requests == []
            with inngest_fixture.inspection_session() as session:
                response = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert response is not None
                assert (
                    SEED_ADAPTIVE_LAB_PRIORITY_ACTIVITY_IDS[0] not in response.content
                )
                assert 'MENTOR_DIAGNOSTIC_PRIVATE_CANARY' not in response.content
                assert 'MENTOR_MATERIAL_BODY_PRIVATE_CANARY' not in response.content

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_actual_diagnostic_activity_hint_refuses_before_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        from shifu.curriculum.database.sqlalchemy.models import ActivityModel
        from shifu.learning.database.sqlalchemy.models import SkillExperienceModel
        from shifu.shared.database.seed_data import (
            SEED_ACCOUNT_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_GOAL_ID,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
        )

        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _seed_learning_matrix(inngest_fixture)
        with inngest_fixture.inspection_session() as session:
            experience = session.get(
                SkillExperienceModel, SEED_ADAPTIVE_LAB_EXPERIENCE_ID
            )
            assert experience is not None
            experience.status = 'diagnosing'
            session.commit()
            activity = session.scalar(
                select(ActivityModel).where(
                    ActivityModel.activity_type == 'diagnostic',
                    ActivityModel.competency_id
                    == SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
                )
            )
            assert activity is not None
            activity_id, competency_id = activity.id, activity.competency_id
        official_before = _official_snapshot(inngest_fixture)
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture,
            'Como resolver esta atividade?',
            account_id=SEED_ACCOUNT_ID,
            context_hint={
                'goal_id': SEED_ADAPTIVE_LAB_GOAL_ID,
                'skill_id': SEED_ADAPTIVE_LAB_SKILL_ID,
                'competency_id': competency_id,
                'activity_id': activity_id,
                'material_id': None,
            },
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        assert state.accounting_requests
        assert all(receipt['used_tokens'] == 0 for receipt in state.accounting_requests)
        assert set(state.effective_usage.values()) == {0}
        assert _official_snapshot(inngest_fixture) == official_before
        with inngest_fixture.inspection_session() as session:
            experience = session.get(
                SkillExperienceModel, SEED_ADAPTIVE_LAB_EXPERIENCE_ID
            )
            assert experience is not None and experience.status == 'diagnosing'
            response = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert response is not None
            assert 'diagnóstica' in response.content
            assert 'MENTOR_DIAGNOSTIC_PRIVATE_CANARY' not in response.content
            assert 'MENTOR_MATERIAL_BODY_PRIVATE_CANARY' not in response.content

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_curriculum_paraphrase_ranks_only_released_references(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mentor_local_embeddings: SentenceTransformersEmbeddingsProvider,
    ) -> None:
        from sqlalchemy import create_engine
        from shifu.curriculum.database.sqlalchemy.curriculum_database import (
            SqlalchemyCurriculumDatabase,
        )
        from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
            CurriculumMentorCatalogProvider,
        )
        from shifu.shared.database.seed_data import (
            SEED_ACCOUNT_ID,
            SEED_ADAPTIVE_LAB_GOAL_ID,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID,
        )

        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _seed_learning_matrix(inngest_fixture)
        engine = create_engine(inngest_fixture.database_url)
        try:
            prepare_indexes(
                mentor_local_embeddings,
                MentorEmbeddingsDatabaseRepository(
                    SqlalchemyIntelligenceDatabase(engine)
                ),
                CurriculumMentorCatalogProvider(SqlalchemyCurriculumDatabase(engine)),
                MentorResources(),
            )
        finally:
            engine.dispose()
        content = 'Encontre uma Habilidade sobre decisões condicionais; como organizar meus estudos?'
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture,
            content,
            account_id=SEED_ACCOUNT_ID,
            context_hint={
                'goal_id': SEED_ADAPTIVE_LAB_GOAL_ID,
                'skill_id': SEED_ADAPTIVE_LAB_SKILL_ID,
                'competency_id': None,
                'material_id': None,
                'activity_id': None,
            },
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            assert (
                f'proposal:{SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID}'
                in attempt.resolved_reference_ids
            )
            assert all(
                SEED_ADAPTIVE_LAB_PRIORITY_MATERIAL_ID not in reference
                for reference in attempt.resolved_reference_ids
            )
            assert (
                session.scalar(
                    select(MentorResponseEventModel).where(
                        MentorResponseEventModel.attempt_id == attempt_id,
                        MentorResponseEventModel.kind == 'block',
                        MentorResponseEventModel.intent == 'search_curriculum',
                    )
                )
                is not None
            )
            response = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert response is not None
            assert 'MENTOR_DIAGNOSTIC_PRIVATE_CANARY' not in response.content
            assert 'MENTOR_MATERIAL_BODY_PRIVATE_CANARY' not in response.content

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        ('mode', 'tokens', 'paths'),
        [
            ('pause_failure', 40, ['/v1/chat/completions']),
            ('pause_quality', 180, ['/v1/chat/completions', '/decisions']),
            ('pause_review_retry', 180, ['/v1/chat/completions', '/decisions']),
        ],
    )
    def test_cancelled_transport_cannot_start_fallback_correction_or_review_retry(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
        tokens: int,
        paths: list[str],
    ) -> None:
        from sqlalchemy import create_engine
        from shifu.intelligence.core.use_cases.cancel_mentor_response_use_case import (
            CancelMentorResponseUseCase,
        )
        from shifu.shared.providers.system_clock_provider import SystemClockProvider

        state, endpoint = controlled_mentor_endpoint
        state.reset(mode)
        session_id, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        event_id = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            event_id,
        )
        assert state.writer_entered.wait(timeout=30)
        engine = create_engine(inngest_fixture.database_url)
        try:
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None
                account_id = attempt.account_id
            CancelMentorResponseUseCase(
                SqlalchemyIntelligenceDatabase(engine),
                SystemClockProvider(),
                _Access(endpoint),
            ).execute(account_id, session_id, attempt_id, str(uuid4()))
        finally:
            state.writer_release.set()
            engine.dispose()
        inngest_fixture.wait_for_log(
            f'mentor_response_job_completed event_id={event_id}'
        )
        assert [path for path, _ in state.requests] == paths
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'cancelled'
            rows = cast('list[dict[str, object]]', attempt.usage_calls)
            assert sum(cast('int', row['used_tokens']) for row in rows) == tokens
            assert (
                session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                is None
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(MentorResponseEventModel)
                    .where(
                        MentorResponseEventModel.attempt_id == attempt_id,
                        MentorResponseEventModel.kind == 'block',
                    )
                )
                == 0
            )
        assert state.accounting_requests[-1]['used_tokens'] == tokens
        assert state.accounting_requests[-1]['cancelled'] is True

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('invalidate', ['cancel', 'revoke'])
    def test_worker_waiting_for_shared_writer_lock_rechecks_before_transport(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        invalidate: str,
    ) -> None:
        from sqlalchemy import create_engine
        from shifu.intelligence.core.use_cases.cancel_mentor_response_use_case import (
            CancelMentorResponseUseCase,
        )
        from shifu.shared.providers.system_clock_provider import SystemClockProvider

        state, endpoint = controlled_mentor_endpoint
        state.reset('pause_writer')
        _, _, first_id = _seed_request(inngest_fixture, 'Como organizar meus estudos?')
        first_event = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': first_id},
            first_event,
        )
        assert state.writer_entered.wait(timeout=30)
        session_id, learner_id, second_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        second_event = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': second_id},
            second_event,
        )

        def waiting(session: 'SqlalchemySession') -> bool:
            attempt = session.get(MentorResponseAttemptModel, second_id)
            return (
                attempt is not None
                and attempt.status == 'processing'
                and len(attempt.generation_keys) == 1
            )

        engine = create_engine(inngest_fixture.database_url)
        try:
            inngest_fixture.wait_for_database(waiting, timeout=20)
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, second_id)
                assert attempt is not None
                account_id = attempt.account_id
            if invalidate == 'cancel':
                CancelMentorResponseUseCase(
                    SqlalchemyIntelligenceDatabase(engine),
                    SystemClockProvider(),
                    _Access(endpoint),
                ).execute(account_id, session_id, second_id, str(uuid4()))
            else:
                with state.lock:
                    state.revoked_accounts.add(account_id)
        finally:
            state.writer_release.set()
            engine.dispose()
        inngest_fixture.wait_for_log(
            f'mentor_response_job_completed event_id={first_event}'
        )
        inngest_fixture.wait_for_log(
            f'mentor_response_job_completed event_id={second_event}'
        )
        with inngest_fixture.inspection_session() as session:
            first = session.get(MentorResponseAttemptModel, first_id)
            second = session.get(MentorResponseAttemptModel, second_id)
            assert first is not None and first.status == 'completed'
            assert second is not None and second.status == (
                'cancelled' if invalidate == 'cancel' else 'failed'
            )
            assert second.usage_calls == []
            assert (
                session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                is None
            )
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/decisions',
        ]

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_crash_after_first_approved_part_replays_prefix_without_resetting_budget(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        from datetime import timedelta

        state, _ = controlled_mentor_endpoint
        state.reset('pause_second_writer')
        session_id, learner_id, attempt_id = _seed_request(
            inngest_fixture,
            'Como organizar meus estudos? Como organizar meus estudos com pouco tempo?',
        )
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            SystemIdentifierProvider().generate(),
        )
        assert state.writer_entered.wait(timeout=30)
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'processing'
            assert attempt.generation_keys == ['generated-0', 'generated-1']
            blocks = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
            ).all()
            persisted_prefix = sorted(
                [
                    {
                        'block_key': row.block_key,
                        'ordinal': row.ordinal,
                        'intent': row.intent,
                        'content': row.content,
                    }
                    for row in blocks
                ],
                key=lambda row: cast('int', row['ordinal']),
            )
            generated = [row for row in blocks if row.block_key == 'generated-0']
            assert len(generated) == 1
            prefix_key, prefix_sequence, prefix_content = (
                generated[0].block_key,
                generated[0].sequence,
                generated[0].content,
            )
            assert prefix_key == 'generated-0'
        writers = [
            payload
            for path, payload in state.requests
            if path == '/v1/chat/completions'
        ]
        assert len(writers) == 2
        second_input = cast('list[dict[str, object]]', writers[1]['messages'])[-1][
            'content'
        ]
        request = cast('dict[str, object]', json.loads(cast('str', second_input)))
        approved = cast('list[dict[str, object]]', request['approved_blocks'])
        assert approved == persisted_prefix
        try:
            inngest_fixture.crash_and_restart_application()
        finally:
            state.writer_release.set()
        with state.lock:
            state.mode = 'approve'
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            attempt.execution_until = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        assert sum(path == '/v1/chat/completions' for path, _ in state.requests) == 2
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and len(attempt.generation_keys) == 2
            blocks = session.scalars(
                select(MentorResponseEventModel).where(
                    MentorResponseEventModel.attempt_id == attempt_id,
                    MentorResponseEventModel.kind == 'block',
                )
            ).all()
            assert (
                sorted(
                    [
                        {
                            'block_key': row.block_key,
                            'ordinal': row.ordinal,
                            'intent': row.intent,
                            'content': row.content,
                        }
                        for row in blocks
                    ],
                    key=lambda row: cast('int', row['ordinal']),
                )
                == persisted_prefix
            )
            generated = [row for row in blocks if row.block_key == 'generated-0']
            assert len(generated) == 1
            assert (
                generated[0].block_key,
                generated[0].sequence,
                generated[0].content,
            ) == (
                prefix_key,
                prefix_sequence,
                prefix_content,
            )
            assert (
                session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.session_id == session_id,
                        MentorMessageModel.in_reply_to_message_id == learner_id,
                    )
                )
                is None
            )
            assert all(
                'Como organizar meus estudos?' not in (row.content or '')
                for row in blocks
            )

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_actual_durable_trigger_and_step_outputs_contain_no_private_inference(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?', history_pairs=34
        )
        event_id = SystemIdentifierProvider().generate()
        ids = inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            event_id,
        )
        assert len(ids) == 1
        inngest_fixture.wait_for_database(
            lambda session: _has_status(session, attempt_id, 'completed')
        )
        inngest_fixture.wait_for_log(
            f'mentor_response_job_completed event_id={event_id}'
        )
        event: dict[str, object] = {}
        runs: list[dict[str, object]] = []
        deadline = monotonic() + 30
        while monotonic() < deadline:
            value = inngest_fixture.query_inngest(
                'query($id:ULID!){eventV2(id:$id){id raw runs{id status output}}}',
                {'id': ids[0]},
            )
            event = cast('dict[str, object]', value.get('eventV2') or {})
            runs = cast('list[dict[str, object]]', event.get('runs') or [])
            if runs and all(str(run['status']).upper() == 'COMPLETED' for run in runs):
                break
            Event().wait(0.1)
        assert runs and all(str(run['status']).upper() == 'COMPLETED' for run in runs)
        durable: list[object] = [event]
        outputs: list[object] = []
        for run in runs:
            run_id = cast('str', run['id'])
            durable.append(
                inngest_fixture.query_inngest(
                    'query($id:String!){runTrigger(runID:$id){eventName IDs payloads}}',
                    {'id': run_id},
                )
            )
            fields = 'name stepID stepType outputID'
            for _ in range(8):
                fields = f'name stepID stepType outputID childrenSpans{{{fields}}}'
            trace: dict[str, object] = {}
            trace_deadline = monotonic() + 30
            while monotonic() < trace_deadline:
                trace = inngest_fixture.query_inngest(
                    f'query($id:String!){{runTrace(runID:$id){{{fields}}}}}',
                    {'id': run_id},
                )
                if _trace_output_ids(trace):
                    break
                Event().wait(0.1)
            assert _trace_output_ids(trace)
            durable.append(trace)
            for output_id in _trace_output_ids(trace):
                output = inngest_fixture.query_inngest(
                    'query($id:String!){runTraceSpanOutputByID(outputID:$id){input data error{message name stack cause}}}',
                    {'id': output_id},
                )
                outputs.append(output)
                durable.append(output)
        assert outputs
        assert any(
            cast(
                'dict[str, object]',
                cast('dict[str, object]', output)['runTraceSpanOutputByID'],
            ).get('data')
            is not None
            for output in outputs
        )
        decoded = '\n'.join(_durable_text(value) for value in durable)
        for private in (
            'Como organizar meus estudos?',
            'Mensagem anterior privada',
            'Dica anterior aprovada',
            'Observe o conceito',
            'request_adherence',
            'disposable-test-key',
        ):
            assert private not in decoded
        assert attempt_id in decoded
        assert 'completed' in decoded.lower()

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('checkpoint', ['writer', 'accounting', 'finalize'])
    def test_crashed_worker_cannot_restart_committed_generation_budget(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        checkpoint: str,
    ) -> None:
        from datetime import timedelta

        state, _ = controlled_mentor_endpoint
        state.reset(
            {
                'writer': 'pause_writer',
                'accounting': 'pause_accounting',
                'finalize': 'pause_finalize',
            }[checkpoint]
        )
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            SystemIdentifierProvider().generate(),
        )
        barrier = (
            state.writer_entered if checkpoint == 'writer' else state.accounting_entered
        )
        assert barrier.wait(timeout=30)
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == (
                'completed' if checkpoint == 'finalize' else 'processing'
            )
            assert len(attempt.generation_keys) == 1
            if checkpoint == 'accounting':
                rows = cast('list[dict[str, object]]', attempt.usage_calls)
                assert len(rows) == 1 and rows[0]['used_tokens'] == 120
        try:
            inngest_fixture.crash_and_restart_application()
        finally:
            state.writer_release.set()
            state.accounting_release.set()
        with state.lock:
            state.mode = 'approve'
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            attempt.execution_until = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
        _publish_and_wait(
            inngest_fixture,
            attempt_id,
            'completed' if checkpoint == 'finalize' else 'failed',
        )
        assert sum(path == '/v1/chat/completions' for path, _ in state.requests) == 1
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and len(attempt.generation_keys) == 1
            response = session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            assert (response is not None) is (checkpoint == 'finalize')
        if checkpoint == 'accounting':
            assert list(state.effective_usage.values()) == [120]
        elif checkpoint == 'finalize':
            assert list(state.effective_usage.values()) == [180]
        else:
            assert state.effective_usage == {}

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_registered_pending_inference_renews_its_real_execution_lease(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('pause_lease')
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        event_id = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            event_id,
        )
        try:
            assert state.writer_entered.wait(timeout=30)
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None and attempt.execution_until is not None
                initial_expiration = attempt.execution_until
                initial_owner = attempt.execution_owner
                account_id = attempt.account_id
                session_id = attempt.session_id

            engine = create_engine(inngest_fixture.database_url)
            try:
                with SqlalchemyIntelligenceDatabase(
                    engine
                ).transaction() as repositories:
                    snapshot = repositories.mentor_response_events.snapshot(
                        account_id, session_id
                    )
                    assert snapshot is not None
                    assert snapshot.status.value == 'processing'
                    assert (
                        snapshot.progress is not None
                        and snapshot.progress.value == 'write-answer'
                    )
                    assert snapshot.consultations == ()
            finally:
                engine.dispose()

            def renewed(session: 'SqlalchemySession') -> bool:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                return (
                    attempt is not None
                    and attempt.status == 'processing'
                    and attempt.execution_owner == initial_owner
                    and attempt.execution_until is not None
                    and attempt.execution_until > initial_expiration
                )

            inngest_fixture.wait_for_database(renewed, timeout=40)
            assert [path for path, _ in state.requests] == ['/v1/chat/completions']
        finally:
            state.writer_release.set()
        inngest_fixture.wait_for_database(
            lambda session: _has_status(session, attempt_id, 'completed')
        )
        assert state.accounting_requests[-1]['used_tokens'] == 180
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and len(attempt.generation_keys) == 1
        engine = create_engine(inngest_fixture.database_url)
        try:
            with SqlalchemyIntelligenceDatabase(engine).transaction() as repositories:
                snapshot = repositories.mentor_response_events.snapshot(
                    account_id, session_id
                )
                assert snapshot is not None and snapshot.progress is None
        finally:
            engine.dispose()

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('action', ['redeliver', 'retry', 'delete'])
    def test_paused_registered_worker_cannot_duplicate_or_recreate_attempt(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        action: str,
    ) -> None:
        from sqlalchemy import create_engine
        from shifu.intelligence.core.use_cases.cancel_mentor_response_use_case import (
            CancelMentorResponseUseCase,
        )
        from shifu.intelligence.core.use_cases.retry_mentor_response_use_case import (
            RetryMentorResponseUseCase,
        )
        from shifu.intelligence.core.use_cases.remove_mentor_session_use_case import (
            RemoveMentorSessionUseCase,
        )
        from shifu.shared.providers.system_clock_provider import SystemClockProvider

        state, endpoint = controlled_mentor_endpoint
        state.reset('pause_writer')
        session_id, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        event_id = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            event_id,
        )
        assert state.writer_entered.wait(timeout=30)
        engine = create_engine(inngest_fixture.database_url)
        retry_id: str | None = None
        try:
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None and attempt.status == 'processing'
                account_id = attempt.account_id
                original_session = session.get(MentorSessionModel, session_id)
                assert original_session is not None
                original_submission_key = original_session.submission_key
            database = SqlalchemyIntelligenceDatabase(engine)
            clock = SystemClockProvider()
            access = _Access(endpoint)
            if action == 'redeliver':
                _publish_and_wait(inngest_fixture, attempt_id, 'processing')
                assert [path for path, _ in state.requests] == ['/v1/chat/completions']
            elif action == 'delete':
                RemoveMentorSessionUseCase(database, clock).execute(
                    account_id, session_id
                )
            else:
                CancelMentorResponseUseCase(database, clock, access).execute(
                    account_id, session_id, attempt_id, str(uuid4())
                )
                retry = RetryMentorResponseUseCase(
                    database, SystemIdentifierProvider(), clock, access
                ).execute(account_id, session_id, attempt_id, str(uuid4()))
                retry_id = retry.attempt_id
                assert retry_id != attempt_id
        finally:
            state.writer_release.set()
            engine.dispose()
        inngest_fixture.wait_for_log(
            f'mentor_response_job_completed event_id={event_id}'
        )
        if retry_id is not None:
            _publish_and_wait(inngest_fixture, retry_id, 'completed')
        elif action == 'redeliver':
            inngest_fixture.wait_for_database(
                lambda session: _has_status(session, attempt_id, 'completed')
            )
        with inngest_fixture.inspection_session() as session:
            responses = session.scalars(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            ).all()
            if action == 'delete':
                tombstone = session.get(MentorSessionModel, session_id)
                assert tombstone is not None and tombstone.deleted_at is not None
                assert tombstone.id == session_id
                assert tombstone.account_id == account_id
                assert tombstone.submission_key == original_submission_key
                assert (
                    tombstone.title,
                    tombstone.title_search,
                    tombstone.content_fingerprint,
                    tombstone.created_at,
                    tombstone.updated_at,
                    tombstone.last_activity_at,
                ) == (None, None, None, None, None, None)
                with database.transaction() as repositories:
                    assert (
                        repositories.mentor_sessions.find_by_id(account_id, session_id)
                        is None
                    )
                assert session.get(MentorResponseAttemptModel, attempt_id) is None
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(MentorMessageModel)
                        .where(MentorMessageModel.session_id == session_id)
                    )
                    == 0
                )
                assert responses == []
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(MentorResponseEventModel)
                        .where(MentorResponseEventModel.session_id == session_id)
                    )
                    == 0
                )
            else:
                assert len(responses) == 1
                attempts = session.scalars(
                    select(MentorResponseAttemptModel).where(
                        MentorResponseAttemptModel.session_id == session_id
                    )
                ).all()
                assert sorted(row.status for row in attempts) == (
                    ['cancelled', 'completed'] if action == 'retry' else ['completed']
                )
                assert sum(len(row.generation_keys) for row in attempts) == (
                    2 if action == 'retry' else 1
                )
        assert sum(path == '/v1/chat/completions' for path, _ in state.requests) == (
            2 if action == 'retry' else 1
        )

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_cancel_during_writer_accounts_consumption_without_late_publication(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        from sqlalchemy import create_engine
        from shifu.intelligence.core.use_cases.cancel_mentor_response_use_case import (
            CancelMentorResponseUseCase,
        )
        from shifu.shared.providers.system_clock_provider import SystemClockProvider

        state, endpoint = controlled_mentor_endpoint
        state.reset('pause_writer')
        session_id, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        event_id = SystemIdentifierProvider().generate()
        inngest_fixture.publish(
            'intelligence/mentor.response.requested',
            {'attempt_id': attempt_id},
            event_id,
        )
        assert state.writer_entered.wait(timeout=30)
        engine = create_engine(inngest_fixture.database_url)
        try:
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None and attempt.status == 'processing'
                account_id = attempt.account_id
            CancelMentorResponseUseCase(
                SqlalchemyIntelligenceDatabase(engine),
                SystemClockProvider(),
                _Access(endpoint),
            ).execute(account_id, session_id, attempt_id, str(uuid4()))
        finally:
            state.writer_release.set()
            engine.dispose()
        inngest_fixture.wait_for_log(
            f'mentor_response_job_completed event_id={event_id}'
        )
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None and attempt.status == 'cancelled'
            rows = cast('list[dict[str, object]]', attempt.usage_calls)
            total = sum(cast('int', row['used_tokens']) for row in rows)
            assert total == 120
            assert (
                session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                is None
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(MentorResponseEventModel)
                    .where(
                        MentorResponseEventModel.attempt_id == attempt_id,
                        MentorResponseEventModel.kind == 'block',
                    )
                )
                == 0
            )
        assert state.accounting_requests[-1]['used_tokens'] == total
        assert state.accounting_requests[-1]['cancelled'] is True
        assert [path for path, _ in state.requests] == ['/v1/chat/completions']
        consumed = dict(state.effective_usage)
        calls = len(state.requests)
        _publish_and_wait(inngest_fixture, attempt_id, 'cancelled')
        assert len(state.requests) == calls
        assert state.effective_usage == consumed

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize('released_origin', [True, False])
    def test_duplicate_material_origins_require_at_least_one_released_origin(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mentor_local_embeddings: SentenceTransformersEmbeddingsProvider,
        released_origin: bool,
    ) -> None:
        from sqlalchemy import create_engine
        from shifu.curriculum.database.sqlalchemy.curriculum_database import (
            SqlalchemyCurriculumDatabase,
        )
        from shifu.curriculum.database.sqlalchemy.models import CurriculumSequenceModel
        from shifu.curriculum.providers.curriculum_mentor_catalog_provider import (
            CurriculumMentorCatalogProvider,
        )
        from shifu.learning.database.sqlalchemy.models import CompetencyProgressModel
        from shifu.shared.database.seed_data import (
            SEED_ACCOUNT_ID,
            SEED_ADAPTIVE_LAB_GOAL_ID,
            SEED_ADAPTIVE_LAB_SKILL_ID,
            SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID,
            SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID,
        )

        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _seed_learning_matrix(inngest_fixture)
        with inngest_fixture.inspection_session() as session:
            released = session.get(
                CurriculumSequenceModel, SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID
            )
            blocked = session.get(
                CurriculumSequenceModel, SEED_ADAPTIVE_LAB_PRIORITY_COMPETENCY_ID
            )
            assert released is not None and blocked is not None
            material = next(
                item
                for item in cast('list[dict[str, object]]', released.items)
                if item.get('material_id') == SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID
            )
            blocked_items = cast('list[dict[str, object]]', blocked.items)
            shared_material = dict(material)
            shared_material['position'] = (
                max(cast('int', item['position']) for item in blocked_items) + 1
            )
            blocked.items = [*blocked_items, shared_material]
            progress = session.scalar(
                select(CompetencyProgressModel).where(
                    CompetencyProgressModel.skill_experience_id
                    == SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
                    CompetencyProgressModel.competency_id
                    == SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
                )
            )
            assert progress is not None
            progress.content_released = released_origin
            session.commit()
        engine = create_engine(inngest_fixture.database_url)
        try:
            prepare_indexes(
                mentor_local_embeddings,
                MentorEmbeddingsDatabaseRepository(
                    SqlalchemyIntelligenceDatabase(engine)
                ),
                CurriculumMentorCatalogProvider(SqlalchemyCurriculumDatabase(engine)),
                MentorResources(),
            )
        finally:
            engine.dispose()
        _, _, attempt_id = _seed_request(
            inngest_fixture,
            'Encontre uma Habilidade sobre decisões condicionais; como organizar meus estudos?',
            account_id=SEED_ACCOUNT_ID,
            context_hint={
                'goal_id': SEED_ADAPTIVE_LAB_GOAL_ID,
                'skill_id': SEED_ADAPTIVE_LAB_SKILL_ID,
                'competency_id': None,
                'material_id': None,
                'activity_id': None,
            },
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        review = next(
            payload for path, payload in state.requests if path == '/decisions'
        )
        request = cast(
            'dict[str, object]', cast('dict[str, object]', review['state'])['request']
        )
        context = cast('dict[str, object]', request['context'])
        assert (
            SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID
            in cast('list[str]', context['eligible_references'])
        ) is released_origin
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            assert (
                f'proposal:{SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID}'
                in attempt.resolved_reference_ids
            ) is released_origin

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'mode',
        [
            'writer_usage_body_list',
            'writer_usage_list',
            'writer_usage_bool',
            'writer_usage_negative',
            'writer_usage_sum',
            'writer_usage_invalid_json',
            'writer_success_usage_missing',
        ],
    )
    def test_actual_writer_invalid_receipts_are_unknown_and_never_charge_fabricated_zero(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        expected_paths = ['/v1/chat/completions', '/decisions']
        expected_tokens: list[int | None] = [None, 60]
        if mode != 'writer_success_usage_missing':
            expected_paths.insert(1, '/fallback/v1/chat/completions')
            expected_tokens.insert(1, 120)
        assert [path for path, _ in state.requests] == expected_paths
        rows = _failed_inference_receipts(inngest_fixture, learner_id, attempt_id)
        assert [row['used_tokens'] for row in rows] == expected_tokens
        assert state.accounting_requests == []
        assert state.effective_usage == {}

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'mode', ['writer_bad_request', 'writer_unauthorized', 'fallback_failure']
    )
    def test_actual_ineligible_primary_and_failed_fallback_preserve_known_usage(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        paths = ['/v1/chat/completions']
        tokens = [40]
        if mode == 'fallback_failure':
            paths.append('/fallback/v1/chat/completions')
            tokens.append(70)
        assert [path for path, _ in state.requests] == paths
        rows = _failed_inference_receipts(inngest_fixture, learner_id, attempt_id)
        assert [row['used_tokens'] for row in rows] == tokens
        assert state.accounting_requests[-1]['used_tokens'] == sum(tokens)
        assert set(state.effective_usage.values()) == {sum(tokens)}

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'mode',
        [
            'writer_invalid_json',
            'writer_blank_content',
            'writer_wrong_key',
            'writer_wrong_ordinal',
        ],
    )
    def test_actual_writer_invalid_output_is_private_and_never_reviewed(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        assert [path for path, _ in state.requests] == ['/v1/chat/completions']
        rows = _failed_inference_receipts(inngest_fixture, learner_id, attempt_id)
        assert [row['used_tokens'] for row in rows] == [120]
        assert state.accounting_requests[-1]['used_tokens'] == 120
        assert set(state.effective_usage.values()) == {120}

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'mode',
        [
            'review_invalid_confidence',
            'review_invalid_probabilities',
            'review_probability_sum',
            'review_extra_criterion',
            'review_bad_request',
        ],
    )
    def test_actual_invalid_review_is_private_and_never_retried_or_corrected(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/decisions',
        ]
        rows = _failed_inference_receipts(inngest_fixture, learner_id, attempt_id)
        assert [row['used_tokens'] for row in rows] == [120, 60]
        assert state.accounting_requests[-1]['used_tokens'] == 180
        assert set(state.effective_usage.values()) == {180}

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_unknown_primary_usage_is_journaled_without_fabricated_zero(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('writer_usage_unknown')
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        assert state.accounting_requests == []
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/fallback/v1/chat/completions',
            '/decisions',
        ]
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            rows = cast('list[dict[str, object]]', attempt.usage_calls)
            assert len(rows) == 3
            assert rows[0]['used_tokens'] is None
            assert sorted(cast('int', row['used_tokens']) for row in rows[1:]) == [
                60,
                120,
            ]

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_only_technical_failure_uses_verified_fallback(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('writer_failure')
        output_offset = len(inngest_fixture.output)
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/fallback/v1/chat/completions',
            '/decisions',
        ]
        assert state.accounting_requests[-1]['used_tokens'] == 40 + 120 + 60
        output = inngest_fixture.output[output_offset:]
        private_output_present = any(
            _PRIVATE_SDK_ERROR_CANARY in line for line in output
        )
        assert not private_output_present, 'Private SDK error body reached worker logs'
        public_marker_present = any(_PUBLIC_SDK_LOG_MARKER in line for line in output)
        assert public_marker_present, 'Unrelated SDK logging was suppressed'

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_actual_review_usage_mismatch_keeps_consumption_unknown(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('review_usage_sum_mismatch')
        _, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'failed')
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/decisions',
        ]
        rows = _failed_inference_receipts(inngest_fixture, learner_id, attempt_id)
        assert [row['used_tokens'] for row in rows] == [120, None]
        assert state.accounting_requests[-1]['used_tokens'] == 120
        assert set(state.effective_usage.values()) == {120}

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_legacy_optional_observer_preserves_native_generation_and_accounting(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('legacy_optional_observer')
        inngest_fixture.restart_application()
        try:
            _, learner_id, attempt_id = _seed_request(
                inngest_fixture, 'Como organizar meus estudos?'
            )
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
            assert [path for path, _ in state.requests] == [
                '/v1/chat/completions',
                '/decisions',
            ]
            assert state.accounting_requests[-1]['used_tokens'] == 180
            assert set(state.effective_usage.values()) == {180}
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None and attempt.status == 'completed'
                receipts = cast('list[dict[str, object]]', attempt.usage_calls)
                assert [row['used_tokens'] for row in receipts] == [120, 60]
                reply = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id == learner_id
                    )
                )
                assert reply is not None and reply.content.strip()
                events = session.scalars(
                    select(MentorResponseEventModel)
                    .where(MentorResponseEventModel.attempt_id == attempt_id)
                    .order_by(MentorResponseEventModel.sequence)
                ).all()
                assert not any(event.progress is not None for event in events)
                assert any(
                    event.kind == 'status' and event.status == 'processing'
                    for event in events
                )
                assert any(event.kind == 'completed' for event in events)
                generated = [
                    event
                    for event in events
                    if event.kind == 'block'
                    and (event.block_key or '').startswith('generated-')
                ]
                assert len(generated) == 1
                review_state = cast('dict[str, object]', state.requests[1][1]['state'])
                candidate = cast('dict[str, object]', review_state['candidate'])
                assert generated[0].content == candidate['content']
                assert str(candidate['content']) in reply.content
        finally:
            state.reset('approve')
            inngest_fixture.restart_application()

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'mode', ['telemetry_disabled', 'telemetry_metadata_only', 'review_key_missing']
    )
    def test_optional_telemetry_and_missing_review_key_at_native_job_boundary(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        mode: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset(mode)
        inngest_fixture.restart_application()
        try:
            _, learner_id, attempt_id = _seed_request(
                inngest_fixture, 'Como organizar meus estudos?'
            )
            disabled = mode != 'review_key_missing'
            _publish_and_wait(
                inngest_fixture, attempt_id, 'completed' if disabled else 'failed'
            )
            expected_paths = ['/v1/chat/completions']
            if disabled:
                expected_paths.append('/decisions')
            assert [path for path, _ in state.requests] == expected_paths
            if disabled:
                if mode == 'telemetry_disabled':
                    assert state.metadata_requests == []
                else:
                    assert state.metadata_requests
                    assert all(
                        row['name'] not in {'mentor-answer', 'mentor-review'}
                        and 'input' not in row
                        and 'output' not in row
                        for row in state.metadata_requests
                    )
                with inngest_fixture.inspection_session() as session:
                    attempt = session.get(MentorResponseAttemptModel, attempt_id)
                    assert attempt is not None and attempt.status == 'completed'
                    rows = cast('list[dict[str, object]]', attempt.usage_calls)
                    reply = session.scalar(
                        select(MentorMessageModel).where(
                            MentorMessageModel.in_reply_to_message_id == learner_id
                        )
                    )
                    assert reply is not None and reply.content.strip()
                    assert any(
                        event.kind == 'completed'
                        for event in session.scalars(
                            select(MentorResponseEventModel).where(
                                MentorResponseEventModel.attempt_id == attempt_id
                            )
                        )
                    )
            else:
                rows = _failed_inference_receipts(
                    inngest_fixture, learner_id, attempt_id
                )
            tokens = [120, 60] if disabled else [120]
            assert [row['used_tokens'] for row in rows] == tokens
            assert state.accounting_requests[-1]['used_tokens'] == sum(tokens)
            assert set(state.effective_usage.values()) == {sum(tokens)}
        finally:
            state.reset('approve')
            inngest_fixture.restart_application()

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_optional_failing_telemetry_limits_content_to_candidate_and_review(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?', history_pairs=2
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert {row['name'] for row in state.metadata_requests} >= {
            'route',
            'generate',
            'review',
        }
        _assert_candidate_review_observations(state, attempt_id, 1)
        for row in state.metadata_requests:
            if row['name'] in {'mentor-answer', 'mentor-review'}:
                continue
            assert 'input' not in row and 'output' not in row
            metadata = cast('dict[str, object]', row['metadata'])
            assert set(metadata) <= {
                'correlation_id',
                'profile',
                'duration_ms',
                'outcome',
                'blocks',
            }
            encoded = json.dumps(row, ensure_ascii=False)
            assert 'Mensagem anterior privada' not in encoded
            assert 'Como organizar meus estudos?' not in encoded

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_registered_job_preserves_monotonic_attempt_timestamps_when_host_clock_is_ahead(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        account_id, _, _, _ = _seed_experiences(inngest_fixture, 'learning')
        session_id, learner_id, attempt_id = _seed_request(
            inngest_fixture, 'Como organizar meus estudos?', account_id=account_id
        )
        future_stamp = datetime.now(UTC) + timedelta(seconds=60)
        with inngest_fixture.inspection_session() as session:
            mentor_session = session.get(MentorSessionModel, session_id)
            learner = session.get(MentorMessageModel, learner_id)
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert (
                mentor_session is not None
                and learner is not None
                and attempt is not None
            )
            for record in (mentor_session, attempt):
                record.created_at = future_stamp
                record.updated_at = future_stamp
            learner.created_at = future_stamp
            mentor_session.last_activity_at = future_stamp
            session.commit()
        official_before = _official_snapshot(inngest_fixture)
        try:
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        except Exception as error:
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None
                error.add_note(
                    'Mentor clock regression diagnostic: '
                    f'created_aware={attempt.created_at.tzinfo is not None} '
                    f'updated_aware={attempt.updated_at.tzinfo is not None} '
                    'updated_minus_created_seconds='
                    f'{(attempt.updated_at - attempt.created_at).total_seconds()} '
                    f'status={attempt.status}'
                )
            raise
        assert any(path == '/v1/chat/completions' for path, _ in state.requests)
        assert any(path == '/decisions' for path, _ in state.requests)
        assert _official_snapshot(inngest_fixture) == official_before
        with inngest_fixture.inspection_session() as session:
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert attempt is not None
            assert attempt.created_at == future_stamp
            assert attempt.updated_at >= attempt.created_at

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_production_lazy_route_refuses_stale_catalog_until_cli_rebuild_and_restart(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('lazy_catalog')
        inngest_fixture.restart_application()
        try:
            _, _, warm_id = _seed_request(
                inngest_fixture, 'O que é uma lista em Python?'
            )
            _publish_and_wait(inngest_fixture, warm_id, 'completed')
            before = _index_snapshot(inngest_fixture)
            _seed_experiences(inngest_fixture, 'learning')
            _, learner_id, stale_id = _seed_request(
                inngest_fixture, 'O que é uma lista em Python?'
            )
            _publish_and_wait(inngest_fixture, stale_id, 'failed')
            assert _index_snapshot(inngest_fixture) == before
            assert state.requests == []
            with inngest_fixture.inspection_session() as session:
                assert (
                    session.scalar(
                        select(MentorMessageModel).where(
                            MentorMessageModel.in_reply_to_message_id == learner_id
                        )
                    )
                    is None
                )
            prepared = _run_preparation_cli(inngest_fixture)
            assert prepared.returncode == 0
            after = _index_snapshot(inngest_fixture)
            assert after[0] != before[0]
            assert f'Mentor index activated: {after[0]}' in prepared.stdout
            _assert_prepared_vectors(inngest_fixture)
            # Rebuilding cannot silently switch a live process's cached corpus.
            _, _, still_stale = _seed_request(
                inngest_fixture, 'O que é uma lista em Python?'
            )
            _publish_and_wait(inngest_fixture, still_stale, 'failed')
            inngest_fixture.restart_application()
            _, _, recovered = _seed_request(
                inngest_fixture, 'O que é uma lista em Python?'
            )
            _publish_and_wait(inngest_fixture, recovered, 'completed')
            assert state.requests == []
            assert _index_snapshot(inngest_fixture) == after
        finally:
            state.reset('approve')
            inngest_fixture.restart_application()

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_unsupported_local_question_abstains_without_inference_or_accounting(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('telemetry_metadata_only')
        inngest_fixture.restart_application()
        try:
            _, _, attempt_id = _seed_request(
                inngest_fixture, 'Como organizar meus estudos?'
            )
            _publish_and_wait(inngest_fixture, attempt_id, 'completed')
            assert state.requests == []
            assert state.accounting_requests
            assert all(row['used_tokens'] == 0 for row in state.accounting_requests)
            with inngest_fixture.inspection_session() as session:
                attempt = session.get(MentorResponseAttemptModel, attempt_id)
                assert attempt is not None
                assert attempt.generation_keys == []
                assert attempt.usage_calls == []
                assert any(
                    event.kind == 'completed'
                    for event in session.scalars(
                        select(MentorResponseEventModel).where(
                            MentorResponseEventModel.attempt_id == attempt_id
                        )
                    )
                )
                reply = session.scalar(
                    select(MentorMessageModel).where(
                        MentorMessageModel.in_reply_to_message_id
                        == attempt.learner_message_id
                    )
                )
                assert reply is not None
                assert (
                    'Ainda não encontrei uma resposta local confiável' in reply.content
                )
        finally:
            state.reset('approve')
            inngest_fixture.restart_application()

    @pytest.mark.usefixtures('prepared_mentor_index')
    @pytest.mark.parametrize(
        'invalid_resource',
        [
            'missing_label',
            'incompatible_manifest',
            'empty_examples',
            'duplicate_answers',
            'invalid_threshold',
        ],
    )
    def test_offline_cli_invalid_resources_preserve_active_index_and_registered_faq(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
        tmp_path: Path,
        invalid_resource: str,
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        before = _index_snapshot(inngest_fixture)
        _assert_prepared_vectors(inngest_fixture)
        package = tmp_path / 'shifu'
        shutil.copytree(
            Path(__file__).resolve().parents[5] / 'src' / 'shifu',
            package,
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
        )
        resource_name = {
            'missing_label': 'mentor-intents.json',
            'empty_examples': 'mentor-intents.json',
            'duplicate_answers': 'mentor-answers.json',
            'incompatible_manifest': 'mentor-index-manifest.json',
            'invalid_threshold': 'mentor-index-manifest.json',
        }[invalid_resource]
        resource = package / 'intelligence' / 'ai' / 'data' / resource_name
        payload: object = json.loads(resource.read_text())
        if invalid_resource == 'duplicate_answers':
            answers = cast('list[dict[str, object]]', payload)
            answers.append(dict(answers[0]))
        else:
            mapping = cast('dict[str, object]', payload)
            if invalid_resource == 'missing_label':
                mapping.pop(next(iter(mapping)))
            elif invalid_resource == 'empty_examples':
                mapping[next(iter(mapping))] = []
            elif invalid_resource == 'invalid_threshold':
                thresholds = cast('dict[str, float]', mapping['intent_thresholds'])
                thresholds[next(iter(thresholds))] = 0.0
            else:
                mapping['dimension'] = 383
        resource.write_text(json.dumps(payload), encoding='utf-8')
        invalid = _run_preparation_cli(inngest_fixture, tmp_path)
        assert invalid.returncode != 0
        assert 'Mentor index activated:' not in invalid.stdout
        assert 'ValueError' in invalid.stderr
        assert _index_snapshot(inngest_fixture) == before
        _, _, attempt_id = _seed_request(
            inngest_fixture, 'O que é uma lista em Python?'
        )
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert state.requests == []

    @pytest.mark.usefixtures('prepared_mentor_index')
    def test_registered_oversized_query_reaches_generation_without_truncation(
        self,
        inngest_fixture: 'InngestFixture',
        controlled_mentor_endpoint: tuple[_ControlledInference, str],
    ) -> None:
        state, _ = controlled_mentor_endpoint
        state.reset('approve')
        # Public content contract has min_length=1 and no maximum; this valid
        # single clause exceeds pinned E5's 512-token capacity without splitting.
        content = 'aprender ' * 700 + 'MENTOR_QUERY_TAIL_PRIVATE_CANARY'
        _, learner_id, attempt_id = _seed_request(inngest_fixture, content)
        _publish_and_wait(inngest_fixture, attempt_id, 'completed')
        assert [path for path, _ in state.requests] == [
            '/v1/chat/completions',
            '/decisions',
        ]
        writer = state.requests[0][1]
        assert content in json.dumps(writer, ensure_ascii=False)
        review = state.requests[1][1]
        request = cast(
            'dict[str, object]', cast('dict[str, object]', review['state'])['request']
        )
        assert request['requested_part'] == content
        assert state.accounting_requests[-1]['used_tokens'] == 180
        with inngest_fixture.inspection_session() as session:
            learner = session.get(MentorMessageModel, learner_id)
            attempt = session.get(MentorResponseAttemptModel, attempt_id)
            assert learner is not None and learner.content == content
            assert attempt is not None and len(attempt.generation_keys or []) == 1
            assert len(attempt.usage_calls or []) == 2


def _failed_inference_receipts(
    fixture: 'InngestFixture', learner_id: str, attempt_id: str
) -> list[dict[str, object]]:
    with fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        assert attempt is not None and attempt.status == 'failed'
        assert len(attempt.generation_keys or []) == 1
        assert (
            session.scalar(
                select(MentorMessageModel).where(
                    MentorMessageModel.in_reply_to_message_id == learner_id
                )
            )
            is None
        )
        events = session.scalars(
            select(MentorResponseEventModel).where(
                MentorResponseEventModel.attempt_id == attempt_id
            )
        ).all()
        assert any(event.kind == 'failed' for event in events)
        assert all(event.kind != 'completed' for event in events)
        assert all(
            not (event.block_key or '').startswith('generated-') for event in events
        )
        assert all(
            _PRIVATE_SDK_ERROR_CANARY not in (event.content or '') for event in events
        )
        return cast('list[dict[str, object]]', attempt.usage_calls)


def _index_snapshot(fixture: 'InngestFixture') -> tuple[str, tuple[str, ...]]:
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


def _official_snapshot(fixture: 'InngestFixture') -> dict[str, tuple[str, ...]]:
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


def _assert_prepared_vectors(fixture: 'InngestFixture') -> None:
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


def _trace_output_ids(value: object) -> tuple[str, ...]:
    found: list[str] = []
    if isinstance(value, dict):
        data = cast('dict[str, object]', value)
        if isinstance(data.get('outputID'), str):
            found.append(cast('str', data['outputID']))
        for child in data.values():
            found.extend(_trace_output_ids(child))
    elif isinstance(value, list):
        for child in cast('list[object]', value):
            found.extend(_trace_output_ids(child))
    return tuple(dict.fromkeys(found))


def _durable_text(value: object) -> str:
    if isinstance(value, str):
        try:
            decoded = base64.b64decode(value, validate=True).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError):
            return value
        return value + '\n' + decoded
    if isinstance(value, dict):
        return '\n'.join(
            _durable_text(child) for child in cast('dict[str, object]', value).values()
        )
    if isinstance(value, list):
        return '\n'.join(_durable_text(child) for child in cast('list[object]', value))
    return str(value)


def _seed_experiences(
    fixture: 'InngestFixture', selected_status: str
) -> tuple[str, str, str, str]:
    from shifu.curriculum.database.sqlalchemy.models import SkillModel
    from shifu.learning.database.sqlalchemy.models import (
        GoalModel,
        SkillExperienceModel,
    )

    ids = SystemIdentifierProvider()
    account_id, skill_id = ids.generate(), ids.generate()
    goal_ids = (ids.generate(), ids.generate())
    experience_ids = (ids.generate(), ids.generate())
    now = datetime.now(UTC)
    with fixture.inspection_session() as session:
        session.add(
            SkillModel(
                id=skill_id,
                name=f'Habilidade contextual {skill_id}',
                description='Projeção curricular não pessoal.',
                initial_diagnostic_activity_ids=[],
            )
        )
        for index, (goal_id, experience_id, status) in enumerate(
            zip(goal_ids, experience_ids, ('completed', selected_status), strict=True)
        ):
            session.add(
                GoalModel(
                    id=goal_id,
                    account_id=account_id,
                    title=f'Objetivo {index}',
                    description='Objetivo sintético.',
                    created_at=now,
                    updated_at=now,
                )
            )
            session.flush()
            session.add(
                SkillExperienceModel(
                    id=experience_id,
                    goal_id=goal_id,
                    skill_id=skill_id,
                    inclusion_reason='Experiência sintética',
                    status=status,
                    created_at=now,
                    updated_at=now,
                    started_at=now,
                    completed_at=now if status == 'completed' else None,
                    completion_summary=None,
                    recommended_concept_id=None,
                    diagnostic_run_id=None,
                )
            )
        session.commit()
    return account_id, goal_ids[1], skill_id, experience_ids[1]


def _seed_learning_matrix(fixture: 'InngestFixture') -> None:
    from sqlalchemy import create_engine
    from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
    from shifu.curriculum.database.sqlalchemy.models import ActivityModel, MaterialModel
    from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
    from shifu.learning.database.sqlalchemy.models import (
        SkillExperienceModel,
        CompetencyProgressModel,
    )
    from shifu.shared.database.seed_data import (
        build_development_seed,
        SEED_ADAPTIVE_LAB_EXPERIENCE_ID,
        SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
        SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID,
    )

    seed = build_development_seed()
    engine = create_engine(fixture.database_url)
    try:
        with SqlalchemyCurriculumDatabase(engine).transaction() as repositories:
            repositories.skills.add_many(list(seed.skills))
            repositories.skill_foundations.add_many(list(seed.skill_foundations))
            repositories.competencies.add_many(list(seed.competencies))
            repositories.concepts.add_many(list(seed.concepts))
            repositories.materials.add_many(list(seed.materials))
            repositories.activities.add_many(list(seed.activities))
            repositories.curriculum_sequences.add_many(list(seed.curriculum_sequences))
        with SqlalchemyLearningDatabase(engine).transaction() as repositories:
            repositories.goals.add_many(list(seed.goals))
            repositories.skill_experiences.add_many(list(seed.skill_experiences))
            repositories.competency_progresses.add_many(
                list(seed.competency_progresses)
            )
            repositories.activity_attempts.add_many(list(seed.activity_attempts))
            repositories.activity_evaluations.add_many(list(seed.activity_evaluations))
        with fixture.inspection_session() as session:
            experience = session.get(
                SkillExperienceModel, SEED_ADAPTIVE_LAB_EXPERIENCE_ID
            )
            assert experience is not None
            experience.status = 'learning'
            progress = session.scalar(
                select(CompetencyProgressModel).where(
                    CompetencyProgressModel.skill_experience_id == experience.id,
                    CompetencyProgressModel.competency_id
                    == SEED_ADAPTIVE_LAB_CONDITIONS_COMPETENCY_ID,
                )
            )
            assert progress is not None and progress.content_released is False
            progress.content_released = True
            material = session.get(
                MaterialModel, SEED_ADAPTIVE_LAB_CONDITIONS_MATERIAL_ID
            )
            assert material is not None
            material.content = 'MENTOR_MATERIAL_BODY_PRIVATE_CANARY'
            diagnostics = session.scalars(
                select(ActivityModel).where(ActivityModel.activity_type == 'diagnostic')
            ).all()
            assert diagnostics
            for activity in diagnostics:
                activity.objective = 'MENTOR_DIAGNOSTIC_PRIVATE_CANARY'
            session.commit()
    finally:
        engine.dispose()
