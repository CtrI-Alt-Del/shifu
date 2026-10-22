"""Unit-level coverage for the job's own validation and dispatch logic.

The sibling real-runtime test drives the job through a durable Inngest
worker in an owned subprocess (see `inngest_fixture`), which this repo's
coverage tooling cannot trace. These tests call the job's static methods
directly so its payload validation and use-case dispatch stay covered.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from inngest import Inngest, NonRetriableError

from shifu.gamification.messaging.inngest.jobs.recognize_competency_mastered_job import (
    RecognizeCompetencyMasteredJob,
)

pytestmark = pytest.mark.anyio

VALID_PAYLOAD: dict[str, object] = {
    'account_id': '01SHF00000000000000ACCOUNT',
    'goal_id': '01SHF00000000000000GOAL',
    'skill_experience_id': '01SHF00000000000000SKILLEX',
    'skill_id': '01SHF00000000000000SKILL',
    'competency_id': '01SHF00000000000000COMP',
    'progress': 'mastered',
    'mastered_at': '2026-01-01T00:00:00+00:00',
}


class TestNormalizePayload:
    async def test_keeps_only_the_fields_the_use_case_needs(self) -> None:
        normalized = await RecognizeCompetencyMasteredJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            VALID_PAYLOAD
        )

        assert normalized == {
            'account_id': VALID_PAYLOAD['account_id'],
            'competency_id': VALID_PAYLOAD['competency_id'],
            'skill_id': VALID_PAYLOAD['skill_id'],
            'skill_experience_id': VALID_PAYLOAD['skill_experience_id'],
            'mastered_at': VALID_PAYLOAD['mastered_at'],
        }

    async def test_rejects_a_blank_identifier(self) -> None:
        payload = {**VALID_PAYLOAD, 'account_id': '   '}

        with pytest.raises(NonRetriableError):
            await RecognizeCompetencyMasteredJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_non_iso_mastered_at(self) -> None:
        payload = {**VALID_PAYLOAD, 'mastered_at': 'not-a-date'}

        with pytest.raises(NonRetriableError):
            await RecognizeCompetencyMasteredJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_naive_mastered_at(self) -> None:
        payload = {**VALID_PAYLOAD, 'mastered_at': '2026-01-01T00:00:00'}

        with pytest.raises(NonRetriableError):
            await RecognizeCompetencyMasteredJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_non_utc_offset_mastered_at(self) -> None:
        payload = {**VALID_PAYLOAD, 'mastered_at': '2026-01-01T00:00:00-03:00'}

        with pytest.raises(NonRetriableError):
            await RecognizeCompetencyMasteredJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )

    async def test_rejects_a_missing_field(self) -> None:
        payload = {
            key: value for key, value in VALID_PAYLOAD.items() if key != 'goal_id'
        }

        with pytest.raises(NonRetriableError):
            await RecognizeCompetencyMasteredJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
                payload
            )


async def test_recognize_dispatches_to_the_use_case_off_the_event_loop() -> None:
    use_case = MagicMock()
    clock_provider = MagicMock()
    now = datetime(2026, 1, 2, tzinfo=UTC)
    clock_provider.now.return_value = now
    normalized: dict[str, str] = {
        'account_id': '01SHF00000000000000ACCOUNT',
        'competency_id': '01SHF00000000000000COMP',
        'skill_id': '01SHF00000000000000SKILL',
        'skill_experience_id': '01SHF00000000000000SKILLEX',
        'mastered_at': '2026-01-01T00:00:00+00:00',
    }

    await RecognizeCompetencyMasteredJob._recognize(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        use_case, clock_provider, normalized
    )

    use_case.execute.assert_called_once_with(
        normalized['account_id'],
        normalized['competency_id'],
        normalized['skill_id'],
        normalized['skill_experience_id'],
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        now=now,
    )


def test_handle_registers_the_inngest_function() -> None:
    client = Inngest(app_id='gamification-test', is_production=False)
    use_case = MagicMock()
    clock_provider = MagicMock()

    function = RecognizeCompetencyMasteredJob.handle(client, use_case, clock_provider)

    assert function.id.endswith(RecognizeCompetencyMasteredJob.FUNCTION_ID)
