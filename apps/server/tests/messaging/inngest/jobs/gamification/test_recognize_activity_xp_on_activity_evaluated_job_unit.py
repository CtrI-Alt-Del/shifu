"""Unit-level coverage for the job's own validation and dispatch logic.

The sibling real-runtime test drives the job through a durable Inngest
worker in an owned subprocess (see `inngest_fixture`), which this repo's
coverage tooling cannot trace. These tests call the job's static methods
directly so its payload validation and use-case dispatch stay covered.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from inngest import Inngest, NonRetriableError

from shifu.gamification.messaging.inngest.jobs.recognize_activity_xp_on_activity_evaluated_job import (
    RecognizeActivityXpOnActivityEvaluatedJob,
)

pytestmark = pytest.mark.anyio

VALID_PAYLOAD: dict[str, object] = {
    'account_id': '01SHF00000000000000ACCOUNT',
    'goal_id': '01SHF00000000000000GOAL',
    'skill_experience_id': '01SHF00000000000000SKILLEX',
    'skill_id': '01SHF00000000000000SKILL',
    'competency_id': '01SHF00000000000000COMP',
    'activity_id': '01SHF00000000000000ACTIVITY',
    'attempt_id': '01SHF00000000000000ATTEMPT',
    'evaluation_id': '01SHF00000000000000EVALUAT',
    'kind': 'learning',
    'difficulty': 'easy',
    'score': '67',
    'evaluated_at': '2026-01-01T00:00:00+00:00',
    'submitted_at': '2026-01-01T00:00:00+00:00',
    'time_zone': 'America/Sao_Paulo',
}


class TestNormalizePayload:
    async def test_keeps_only_the_fields_the_use_case_needs(self) -> None:
        normalized = await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            VALID_PAYLOAD
        )

        assert normalized == {
            'account_id': VALID_PAYLOAD['account_id'],
            'goal_id': VALID_PAYLOAD['goal_id'],
            'skill_experience_id': VALID_PAYLOAD['skill_experience_id'],
            'activity_id': VALID_PAYLOAD['activity_id'],
            'attempt_id': VALID_PAYLOAD['attempt_id'],
            'difficulty': VALID_PAYLOAD['difficulty'],
            'score': VALID_PAYLOAD['score'],
            'evaluated_at': VALID_PAYLOAD['evaluated_at'],
        }

    async def test_rejects_a_blank_identifier(self) -> None:
        payload = {**VALID_PAYLOAD, 'account_id': '   '}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_an_unsupported_difficulty(self) -> None:
        payload = {**VALID_PAYLOAD, 'difficulty': 'impossible'}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_non_decimal_score(self) -> None:
        payload = {**VALID_PAYLOAD, 'score': 'not-a-number'}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_an_out_of_range_score(self) -> None:
        payload = {**VALID_PAYLOAD, 'score': '150'}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_non_iso_evaluated_at(self) -> None:
        payload = {**VALID_PAYLOAD, 'evaluated_at': 'not-a-date'}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_naive_evaluated_at(self) -> None:
        payload = {**VALID_PAYLOAD, 'evaluated_at': '2026-01-01T00:00:00'}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_non_utc_offset_evaluated_at(self) -> None:
        payload = {**VALID_PAYLOAD, 'evaluated_at': '2026-01-01T00:00:00-03:00'}

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_missing_field(self) -> None:
        payload = {
            key: value for key, value in VALID_PAYLOAD.items() if key != 'goal_id'
        }

        with pytest.raises(NonRetriableError):
            await RecognizeActivityXpOnActivityEvaluatedJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )


async def test_recognize_dispatches_to_the_use_case_off_the_event_loop() -> None:
    use_case = MagicMock()
    clock_provider = MagicMock()
    now = datetime(2026, 1, 2, tzinfo=UTC)
    clock_provider.now.return_value = now
    normalized: dict[str, str] = {
        'account_id': '01SHF00000000000000ACCOUNT',
        'goal_id': '01SHF00000000000000GOAL',
        'skill_experience_id': '01SHF00000000000000SKILLEX',
        'activity_id': '01SHF00000000000000ACTIVITY',
        'attempt_id': '01SHF00000000000000ATTEMPT',
        'difficulty': 'easy',
        'score': '67',
        'evaluated_at': '2026-01-01T00:00:00+00:00',
    }

    await RecognizeActivityXpOnActivityEvaluatedJob._recognize(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        use_case, clock_provider, normalized
    )

    use_case.execute.assert_called_once_with(
        normalized['account_id'],
        normalized['activity_id'],
        normalized['attempt_id'],
        normalized['goal_id'],
        normalized['skill_experience_id'],
        difficulty=normalized['difficulty'],
        score=Decimal('67'),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        now=now,
    )


def test_handle_registers_the_inngest_function() -> None:
    client = Inngest(app_id='gamification-test', is_production=False)
    use_case = MagicMock()
    clock_provider = MagicMock()

    function = RecognizeActivityXpOnActivityEvaluatedJob.handle(
        client, use_case, clock_provider
    )

    assert function.id.endswith(RecognizeActivityXpOnActivityEvaluatedJob.FUNCTION_ID)
