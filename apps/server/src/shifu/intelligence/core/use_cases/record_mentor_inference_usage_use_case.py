import re
from contextlib import suppress
from math import isfinite
from typing import Any

from shifu.intelligence.core.domain.enums import (
    AiQuotaRequestKind,
    MentorResponseStatus,
)
from shifu.intelligence.core.domain.structures import (
    AiQuotaPolicy,
    AiTokenCount,
    MentorInferenceUsage,
)
from shifu.intelligence.core.interfaces import (
    AiQuotaCalendarProvider,
    IntelligenceDatabase,
    MentorTelemetryProvider,
)
from shifu.intelligence.core.use_cases.ai_quota_ledger import AiQuotaLedger
from shifu.intelligence.core.use_cases.mentor_response_phase_helpers import (
    assert_response_access,
)
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorAccessGrant, MentorUsage
from shifu.shared.core.interfaces import ClockProvider, MentorAccessProvider


class RecordMentorInferenceUsageUseCase:
    _CALL_KEY = re.compile(r'^[a-z][a-z0-9:_-]{0,119}$')

    def __init__(
        self,
        database: IntelligenceDatabase,
        clock_provider: ClockProvider,
        access_provider: MentorAccessProvider,
        quota_policy: AiQuotaPolicy,
        quota_calendar: AiQuotaCalendarProvider,
        telemetry: MentorTelemetryProvider | None = None,
    ) -> None:
        self._database = database
        self._clock_provider = clock_provider
        self._access_provider = access_provider
        self._ledger: AiQuotaLedger = AiQuotaLedger(
            quota_policy, quota_calendar, clock_provider
        )
        self._telemetry = telemetry

    def execute(
        self,
        attempt_id: str,
        execution_owner: str,
        usage: MentorInferenceUsage,
    ) -> None:
        self._validate(usage)
        with self._database.transaction() as repositories:
            attempt = repositories.mentor_response_attempts.find_by_id(attempt_id)
            # A cancel keeps the usage that occurred, including calls that finish
            # while the cancelled execution winds down; its claim is still held.
            if attempt is None or attempt.status not in (
                MentorResponseStatus.PROCESSING,
                MentorResponseStatus.CANCELLED,
            ):
                raise ServiceUnavailableError
            if not repositories.mentor_response_attempts.has_claim(
                attempt_id, execution_owner, self._clock_provider.now()
            ):
                raise ServiceUnavailableError
            assert_response_access(self._access_provider, attempt)
            if not repositories.mentor_response_attempts.journal_usage(
                attempt_id,
                execution_owner,
                attempt.access_revision,
                usage,
            ):
                raise ServiceUnavailableError
            calls = repositories.mentor_response_attempts.read_usage(attempt_id)
            if calls:
                # The charge shares the journal transaction, so the journal and the
                # month never disagree. The attempt row is already locked here.
                self._ledger.charge(
                    repositories,
                    AiQuotaRequestKind.MENTOR_RESPONSE,
                    attempt_id,
                    tuple(
                        AiTokenCount(
                            input_tokens=call.input_tokens,
                            output_tokens=call.output_tokens,
                            used_tokens=call.used_tokens,
                        )
                        for call in calls
                    ),
                )
        if self._telemetry is not None:
            with suppress(Exception):
                self._telemetry.record_inference(
                    usage.profile,
                    usage.used_tokens,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.cost_usd,
                )
        if calls is None or not calls:
            raise ServiceUnavailableError
        if any(call.used_tokens is None for call in calls):
            return
        total = sum(call.used_tokens or 0 for call in calls)
        self._access_provider.record_usage(
            MentorAccessGrant(
                account_id=attempt.account_id,
                access_revision=attempt.access_revision,
                operation_key=attempt.operation_key,
            ),
            MentorUsage(
                operation_key=attempt.operation_key,
                attempt_id=attempt.id,
                used_tokens=total,
                cancelled=attempt.status is MentorResponseStatus.CANCELLED,
            ),
        )

    @classmethod
    def _validate(cls, usage: MentorInferenceUsage) -> None:
        call_key: Any = usage.call_key
        profile: Any = usage.profile
        if (
            not isinstance(call_key, str)
            or not cls._CALL_KEY.fullmatch(call_key)
            or not isinstance(profile, str)
            or not profile.strip()
            or any(
                value is not None and (type(value) is not int or value < 0)
                for value in (
                    usage.used_tokens,
                    usage.input_tokens,
                    usage.output_tokens,
                )
            )
            or (
                usage.cost_usd is not None
                and (
                    type(usage.cost_usd) not in (int, float)
                    or not isfinite(usage.cost_usd)
                    or usage.cost_usd < 0
                )
            )
            or (
                usage.input_tokens is not None
                and usage.output_tokens is not None
                and usage.used_tokens is not None
                and usage.input_tokens + usage.output_tokens != usage.used_tokens
            )
        ):
            raise ServiceUnavailableError
