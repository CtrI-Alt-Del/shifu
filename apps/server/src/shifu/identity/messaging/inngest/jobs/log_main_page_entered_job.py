"""Logging-only Inngest consumer for authenticated main-page entries."""

from collections.abc import Mapping
from datetime import UTC, datetime
import json
import logging
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, field_validator


LOGGER = logging.getLogger(__name__)


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    event_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)

    @field_validator('occurred_at')
    @classmethod
    def validate_occurred_at(cls, value: str) -> str:
        try:
            parsed_time = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(
                'Main-page event time must be an ISO-8601 string'
            ) from error
        if parsed_time.tzinfo is None or parsed_time.utcoffset() != UTC.utcoffset(
            parsed_time
        ):
            raise ValueError('Main-page event time must be UTC')
        return value


def _validate_payload(data: Mapping[str, object]) -> _Payload:
    return _Payload.model_validate(dict(data))


class LogMainPageEnteredJob:
    FUNCTION_ID: str = 'identity-log-main-page-entered'
    _EVENT_NAME: ClassVar[str] = 'app/main-page.entered'

    @staticmethod
    def handle(inngest: Inngest) -> Function[None]:
        @inngest.create_function(
            fn_id=LogMainPageEnteredJob.FUNCTION_ID,
            trigger=TriggerEvent(event=LogMainPageEnteredJob._EVENT_NAME),
            retries=0,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            normalized_data = await context.step.run(
                'normalize_payload',
                LogMainPageEnteredJob._normalize_payload,
                data,
            )
            await context.step.run(
                'log_main_page_entered',
                lambda: LogMainPageEnteredJob._log_payload(normalized_data),
            )

        return _

    @staticmethod
    async def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        payload = _validate_payload(data)
        return {
            'event_id': payload.event_id,
            'account_id': payload.account_id,
            'occurred_at': payload.occurred_at,
        }

    @staticmethod
    async def _log_payload(payload: Mapping[str, str]) -> None:
        log_data = {
            'event': 'identity.main_page_entered',
            'event_id': payload['event_id'],
            'account_id': payload['account_id'],
            'occurred_at': payload['occurred_at'],
        }
        LOGGER.info(
            json.dumps(log_data, sort_keys=True),
            extra=log_data,
        )
