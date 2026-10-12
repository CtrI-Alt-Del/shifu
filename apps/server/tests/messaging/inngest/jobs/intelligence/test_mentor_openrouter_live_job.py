"""Explicitly opt-in paid OpenRouter proof with synthetic registered-job data.

Run only with SHIFU_RUN_LIVE_OPENROUTER_TESTS=1 and the normal real-Inngest
opt-in. Credentials and the privacy attestation come from existing Settings.
This disposable access grant does not establish production quota/fence proof.
"""

import json
import logging
import os
import sys
from collections.abc import Iterator
from functools import partial
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from sqlalchemy import select
import pytest

from shifu.intelligence.core.domain.events.mentor_response_requested_event import (
    MentorResponseRequestedEvent,
    MentorResponseRequestedPayload,
)
from shifu.intelligence.database.sqlalchemy.models import (
    MentorMessageModel,
    MentorResponseAttemptModel,
    MentorResponseEventModel,
)
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from shifu.intelligence.providers.mentor_review_provider.openrouter.openrouter_jev_mentor_review_provider import (
    OpenrouterJevMentorReviewProvider,
)
from tests.messaging.inngest.jobs.intelligence.test_answer_mentor_message_job import (
    _Access,  # pyright: ignore[reportPrivateUsage] - Disposable synthetic access/accounting only.
    _ControlledInference,  # pyright: ignore[reportPrivateUsage] - Reuse the actual fixture-owned accounting endpoint.
    _official_snapshot,  # pyright: ignore[reportPrivateUsage] - Preserve official module state assertions.
    _seed_request,  # pyright: ignore[reportPrivateUsage] - Seed only synthetic own-session data.
    controlled_mentor_endpoint as controlled_mentor_endpoint,
    prepared_mentor_index as prepared_mentor_index,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session as SqlalchemySession
    from tests.fixtures.inngest_fixture import InngestFixture


pytestmark = pytest.mark.skipif(
    os.environ.get('SHIFU_RUN_LIVE_OPENROUTER_TESTS') != '1',
    reason='Live paid OpenRouter execution requires explicit opt-in.',
)


def _criterion_metadata(
    key: str, answer: object, threshold: float
) -> dict[str, object]:
    row = cast('dict[str, object]', answer) if isinstance(answer, dict) else {}
    confidence = row.get('confidence')
    valid_confidence = (
        isinstance(confidence, (float, int))
        and not isinstance(confidence, bool)
        and 0 <= confidence <= 1
    )
    choice = row.get('choice')
    return {
        'criterion': key,
        'choice': choice
        if choice in ('approved', 'rejected', 'inconclusive')
        else None,
        'confidence': confidence if valid_confidence else None,
        'threshold': threshold,
    }


def _review_metadata(response: httpx.Response, *, thresholds: dict[str, float]) -> None:
    response.read()
    try:
        body: object = response.json()
    except ValueError:
        return
    if not isinstance(body, dict):
        return
    answers = cast('dict[str, object]', body).get('answers')
    if not isinstance(answers, dict):
        return
    answer_values = cast('dict[str, object]', answers)
    rows = [
        cast('dict[str, object]', answer)
        for answer in cast('dict[str, object]', answers).values()
        if isinstance(answer, dict)
    ]
    confidence = [
        float(value)
        for row in rows
        if isinstance(value := row.get('confidence'), (float, int))
        and not isinstance(value, bool)
        and 0 <= value <= 1
    ]
    print(
        json.dumps(
            {
                'live_review_metadata': {
                    'status': response.status_code,
                    'answer_count': len(rows),
                    'missing_confidence': sum('confidence' not in row for row in rows),
                    'missing_probabilities': sum(
                        'probabilities' not in row for row in rows
                    ),
                    'minimum_confidence': min(confidence) if confidence else None,
                    'criteria': [
                        _criterion_metadata(key, answer_values.get(key), threshold)
                        for key, threshold in thresholds.items()
                    ],
                    'approved_choices': sum(
                        row.get('choice') == 'approved' for row in rows
                    ),
                    'rejected_choices': sum(
                        row.get('choice') == 'rejected' for row in rows
                    ),
                    'inconclusive_choices': sum(
                        row.get('choice') == 'inconclusive' for row in rows
                    ),
                }
            },
            sort_keys=True,
        ),
        flush=True,
    )


class _ObservedReviewer(OpenrouterJevMentorReviewProvider):
    def __init__(
        self,
        client: httpx.Client,
        api_key: str | None,
        decisions_url: str,
        thresholds: dict[str, float],
    ) -> None:
        super().__init__(client, api_key, decisions_url, thresholds)
        client.event_hooks['response'].append(
            partial(_review_metadata, thresholds=dict(thresholds))
        )


def create_live_openrouter_mentor_app() -> FastAPI:
    from shifu.app import FastAPIApp
    from shifu.shared.database.sqlalchemy.session import Session
    from shifu.shared.settings import get_settings

    settings = get_settings()
    if (
        not settings.openrouter_api_key
        or not settings.openrouter_prompt_logging_disabled
    ):
        raise RuntimeError(
            'Live Mentor requires configured credentials and privacy attestation.'
        )
    logger = logging.getLogger(
        'shifu.intelligence.messaging.inngest.jobs.answer_mentor_message_job'
    )
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Route, context, native writer/reviewer and runtime cleanup are production defaults.
    with patch(
        'shifu.composition.mentor_answer_runtime.OpenrouterJevMentorReviewProvider',
        _ObservedReviewer,
    ):
        return FastAPIApp.register(
            database_engine=Session.create_database_engine(),
            mentor_access_provider=_Access(os.environ['SHIFU_MENTOR_TEST_ENDPOINT']),
        )


@pytest.fixture(scope='session')
def live_runtime_environment() -> Iterator[None]:
    previous = os.environ.get('MENTOR_TELEMETRY_ENABLED')
    os.environ['MENTOR_TELEMETRY_ENABLED'] = 'false'
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('MENTOR_TELEMETRY_ENABLED', None)
        else:
            os.environ['MENTOR_TELEMETRY_ENABLED'] = previous


@pytest.fixture(scope='session')
def inngest_app_target(
    controlled_mentor_endpoint: tuple[_ControlledInference, str],
    live_runtime_environment: None,
) -> tuple[str, bool]:
    del controlled_mentor_endpoint, live_runtime_environment
    return (
        'tests.messaging.inngest.jobs.intelligence.test_mentor_openrouter_live_job:create_live_openrouter_mentor_app',
        True,
    )


@pytest.mark.usefixtures('prepared_mentor_index')
def test_live_production_openrouter_runtime_completes_synthetic_registered_request(
    inngest_fixture: 'InngestFixture',
    controlled_mentor_endpoint: tuple[_ControlledInference, str],
) -> None:
    state, _ = controlled_mentor_endpoint
    state.reset('approve')
    official_before = _official_snapshot(inngest_fixture)
    _, learner_id, attempt_id = _seed_request(
        inngest_fixture, 'Como organizar meus estudos?'
    )
    event = MentorResponseRequestedEvent(
        payload=MentorResponseRequestedPayload(attempt_id=attempt_id)
    )
    event_id = SystemIdentifierProvider().generate()
    inngest_fixture.publish(event.name, {'attempt_id': attempt_id}, event_id)

    def terminal(session: 'SqlalchemySession') -> bool:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        return attempt is not None and attempt.status in {'completed', 'failed'}

    inngest_fixture.wait_for_database(terminal)
    inngest_fixture.wait_for_log(f'mentor_response_job_completed event_id={event_id}')
    for line in inngest_fixture.output:
        if line.startswith('{"live_review_metadata":'):
            print(line.strip())
    assert state.requests == [], (
        'Commercial inference unexpectedly used the controlled endpoint'
    )
    with inngest_fixture.inspection_session() as session:
        attempt = session.get(MentorResponseAttemptModel, attempt_id)
        assert attempt is not None
        rows = cast('list[dict[str, object]]', attempt.usage_calls)
        events = session.scalars(
            select(MentorResponseEventModel).where(
                MentorResponseEventModel.attempt_id == attempt_id
            )
        ).all()
        reply = session.scalar(
            select(MentorMessageModel).where(
                MentorMessageModel.in_reply_to_message_id == learner_id
            )
        )
        # Print only closed status/profile/count metadata, never responses or credentials.
        print(
            json.dumps(
                {
                    'live_mentor_status': attempt.status,
                    'receipts': [
                        {'profile': row['profile'], 'used_tokens': row['used_tokens']}
                        for row in rows
                    ],
                    'generation_parts': len(attempt.generation_keys or []),
                    'approved_generated_blocks': sum(
                        row.kind == 'block'
                        and (row.block_key or '').startswith('generated-')
                        for row in events
                    ),
                },
                sort_keys=True,
            )
        )
        if attempt.status == 'failed':
            assert reply is None
            assert all(
                not (row.block_key or '').startswith('generated-') for row in events
            )
        assert attempt.status == 'completed', (
            'Actual provider did not approve the synthetic request; inspect safe receipt metadata.'
        )
        assert reply is not None and reply.content.strip()
        assert any(row.kind == 'completed' for row in events)
        assert any(
            row.kind == 'block' and (row.block_key or '').startswith('generated-')
            for row in events
        )
        assert rows and all(
            isinstance(row['used_tokens'], int)
            and not isinstance(row['used_tokens'], bool)
            and row['used_tokens'] >= 0
            for row in rows
        ), 'Actual live receipt unavailable; no consumption is invented.'
        assert {row['profile'] for row in rows} >= {'gpt-6-luna', 'jev'}
        assert sum(row['profile'] == 'jev' for row in rows) <= 6
        assert sum(row['profile'] != 'jev' for row in rows) <= 4
        assert sum(cast('int', row['used_tokens']) for row in rows) > 0
    assert _official_snapshot(inngest_fixture) == official_before
    assert state.accounting_requests[-1]['used_tokens'] == sum(
        cast('int', row['used_tokens']) for row in rows
    )
