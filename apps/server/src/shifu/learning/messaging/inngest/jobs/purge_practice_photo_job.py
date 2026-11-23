"""Delete one removed practice photo object from private storage."""

import asyncio
from collections.abc import Mapping
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.events import PracticePhotoCleanupRequestedEvent
from shifu.learning.core.use_cases import PurgePracticePhotosUseCase
from shifu.shared.core.interfaces.telemetry_provider import TelemetryProvider
from shifu.shared.messaging.inngest.job_lifecycle_telemetry import (
    job_lifecycle_telemetry,
)


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid',
        frozen=True,
        strict=True,
    )

    photo_id: str = Field(min_length=1)
    object_key: str = Field(min_length=1)


class PurgePracticePhotoJob:
    FUNCTION_ID: ClassVar[str] = 'learning-purge-practice-photo'
    _EVENT_NAME: ClassVar[str] = PracticePhotoCleanupRequestedEvent.EVENT_NAME
    _MAX_ATTEMPTS: ClassVar[int] = 6

    @staticmethod
    def handle(
        inngest: Inngest,
        use_case: PurgePracticePhotosUseCase,
        *,
        telemetry_provider: TelemetryProvider,
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=PurgePracticePhotoJob.FUNCTION_ID,
            trigger=TriggerEvent(event=PurgePracticePhotoJob._EVENT_NAME),
            retries=PurgePracticePhotoJob._MAX_ATTEMPTS - 1,
        )
        @job_lifecycle_telemetry(
            telemetry_provider,
            function_id=PurgePracticePhotoJob.FUNCTION_ID,
            max_attempts=PurgePracticePhotoJob._MAX_ATTEMPTS,
        )
        async def _(context: Context) -> None:
            data = cast('dict[str, object]', dict(context.event.data))
            payload = await context.step.run(
                'normalize_payload',
                PurgePracticePhotoJob._normalize_payload,
                data,
            )
            await context.step.run(
                'delete_practice_photo_object',
                PurgePracticePhotoJob._purge,
                use_case,
                payload['photo_id'],
                payload['object_key'],
            )

        return _

    @staticmethod
    async def _normalize_payload(data: Mapping[str, object]) -> dict[str, str]:
        try:
            payload = _Payload.model_validate(dict(data))
        except ValidationError as error:
            raise NonRetriableError('Invalid practice photo cleanup payload') from error

        return {'photo_id': payload.photo_id, 'object_key': payload.object_key}

    @staticmethod
    async def _purge(
        use_case: PurgePracticePhotosUseCase, photo_id: str, object_key: str
    ) -> None:
        try:
            await asyncio.to_thread(use_case.execute, photo_id, object_key)
        except InvalidAttemptError as error:
            raise NonRetriableError('Invalid practice photo object key') from error
