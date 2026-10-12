import asyncio
import logging
from pathlib import Path
from typing import ClassVar, cast

from inngest import Context, Function, Inngest, NonRetriableError, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from shifu.intelligence.core.use_cases.process_mentor_response_use_case import (
    ProcessMentorResponseUseCase,
)
from shifu.intelligence.providers.telemetry.langfuse.langfuse_mentor_telemetry_provider import (
    mentor_telemetry_correlation,
)


LOGGER = logging.getLogger(__name__)


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', strict=True, frozen=True
    )
    attempt_id: str = Field(pattern=r'^[0-7][0-9A-HJKMNP-TV-Z]{25}$')


class AnswerMentorMessageJob:
    FUNCTION_ID: ClassVar[str] = 'intelligence-answer-mentor-message'
    _EVENT_NAME: ClassVar[str] = 'intelligence/mentor.response.requested'

    @staticmethod
    def handle(
        inngest: Inngest, use_case: ProcessMentorResponseUseCase
    ) -> Function[None]:
        @inngest.create_function(
            fn_id=AnswerMentorMessageJob.FUNCTION_ID,
            trigger=TriggerEvent(event=AnswerMentorMessageJob._EVENT_NAME),
            retries=0,
        )
        async def _(context: Context) -> None:
            try:
                normalized = AnswerMentorMessageJob._normalize_payload(
                    cast('dict[str, object]', dict(context.event.data))
                )
            except NonRetriableError:
                LOGGER.warning(
                    'mentor_response_job_invalid event_id=%s', context.event.id
                )
                raise

            # Input/output are IDs and a closed status only. Private inference and review
            # execute in process memory; approved blocks are persisted by Core.
            async def process(attempt_id: str) -> str:
                return await AnswerMentorMessageJob._process(use_case, attempt_id)

            status = await context.step.run(
                'process_response',
                process,
                normalized['attempt_id'],
            )
            LOGGER.info(
                'mentor_response_job_completed event_id=%s status=%s',
                context.event.id,
                status,
            )

        return _

    @staticmethod
    def _normalize_payload(data: dict[str, object]) -> dict[str, str]:
        try:
            payload = _Payload.model_validate(data)
        except ValidationError:
            raise NonRetriableError('Evento do Mentor inválido.') from None
        return {'attempt_id': payload.attempt_id}

    @staticmethod
    async def _process(use_case: ProcessMentorResponseUseCase, attempt_id: str) -> str:
        def execute() -> str:
            with mentor_telemetry_correlation():
                try:
                    return use_case.execute(attempt_id).value
                except Exception as error:  # noqa: BLE001 - Sanitize every failure at the durable boundary.
                    frame = error.__traceback__
                    while frame is not None and frame.tb_next is not None:
                        frame = frame.tb_next
                    location = (
                        f'{Path(frame.tb_frame.f_code.co_filename).name}:{frame.tb_frame.f_code.co_name}:{frame.tb_lineno}'
                        if frame is not None
                        else 'unknown'
                    )
                    LOGGER.error(  # noqa: TRY400 - Tracebacks may contain private model state.
                        'mentor_response_job_error kind=%s location=%s',
                        type(error).__name__,
                        location,
                    )
                    raise NonRetriableError(
                        'Execução do Mentor indisponível.'
                    ) from None

        return await asyncio.to_thread(execute)
