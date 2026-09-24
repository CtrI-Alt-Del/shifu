"""Evaluate a submitted choice attempt from its durable outbox event."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
import logging
from typing import TYPE_CHECKING, ClassVar, TypedDict, cast

from inngest import Context, Function, Inngest, TriggerEvent
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from shifu.learning.core.domain.enums import ActivityEvaluationStatus
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase


LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from shifu.learning.core.domain.entities import ActivityEvaluation
    from shifu.learning.core.interfaces import LearningDatabase
    from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider


class EvaluationJobPayload(TypedDict):
    attempt_id: str
    run_id: str
    skill_experience_id: str
    activity_id: str
    kind: str
    requested_at: str


class _Payload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra='forbid', frozen=True, strict=True
    )

    attempt_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    skill_experience_id: str = Field(min_length=1)
    activity_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    requested_at: str = Field(min_length=1)

    @field_validator('requested_at')
    @classmethod
    def validate_requested_at(cls, value: str) -> str:
        try:
            parsed_time = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError('Job event time must be an ISO-8601 string') from error
        if parsed_time.tzinfo is None or parsed_time.utcoffset() != UTC.utcoffset(
            parsed_time
        ):
            raise ValueError('Job event time must be UTC')
        return value


class EvaluateChoiceActivityJob:
    FUNCTION_ID: ClassVar[str] = 'learning-evaluate-choice-activity'
    _EVENT_NAME: ClassVar[str] = 'learning/activity-submission.requested'

    @staticmethod
    def handle(
        inngest: Inngest,
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
        curriculum_content_provider: CurriculumContentProvider | None = None,
    ) -> Function[None]:
        async def on_failure(context: Context) -> None:
            failure_data = cast('dict[str, object]', dict(context.event.data))
            original_event = failure_data.get('event')
            if not isinstance(original_event, Mapping):
                return
            original_data = cast('Mapping[str, object]', original_event).get('data')
            if not isinstance(original_data, Mapping):
                return
            try:
                payload = await EvaluateChoiceActivityJob._normalize_payload(
                    cast('Mapping[str, object]', original_data)
                )
            except (ValidationError, ValueError):
                return
            await context.step.run(
                'mark_evaluation_failed',
                EvaluateChoiceActivityJob._mark_failed,
                learning_database,
                payload,
            )
            LOGGER.info(
                'choice_activity_job_failure_handled attempt_id=%s run_id=%s',
                payload['attempt_id'],
                payload['run_id'],
            )

        @inngest.create_function(
            fn_id=EvaluateChoiceActivityJob.FUNCTION_ID,
            trigger=TriggerEvent(event=EvaluateChoiceActivityJob._EVENT_NAME),
            retries=0,
            on_failure=on_failure,
        )
        async def _(context: Context) -> None:
            event_data = cast('dict[str, object]', dict(context.event.data))
            payload = await context.step.run(
                'validate_submission_event',
                EvaluateChoiceActivityJob._normalize_payload,
                event_data,
            )
            is_current = await context.step.run(
                'resolve_current_run',
                EvaluateChoiceActivityJob._is_current,
                learning_database,
                payload,
            )
            if not is_current:
                LOGGER.info(
                    'choice_activity_job_stale_run attempt_id=%s run_id=%s',
                    payload['attempt_id'],
                    payload['run_id'],
                )
                return
            await context.step.run(
                'evaluate_and_apply_official_effect',
                EvaluateChoiceActivityJob._evaluate,
                learning_database,
                clock_provider,
                curriculum_content_provider,
                payload,
            )
            LOGGER.info(
                'choice_activity_job_completed attempt_id=%s run_id=%s',
                payload['attempt_id'],
                payload['run_id'],
            )

        return _

    @staticmethod
    async def _normalize_payload(
        data: Mapping[str, object],
    ) -> EvaluationJobPayload:
        payload = _Payload.model_validate(dict(data))
        if payload.kind not in {'learning', 'diagnostic', 'review'}:
            raise ValueError('Only choice activity submissions can be evaluated')
        return EvaluationJobPayload(
            attempt_id=payload.attempt_id,
            run_id=payload.run_id,
            skill_experience_id=payload.skill_experience_id,
            activity_id=payload.activity_id,
            kind=payload.kind,
            requested_at=payload.requested_at,
        )

    @staticmethod
    async def _is_current(
        learning_database: LearningDatabase,
        payload: EvaluationJobPayload,
    ) -> bool:
        return await asyncio.to_thread(
            EvaluateChoiceActivityJob._is_current_sync,
            learning_database,
            payload,
        )

    @staticmethod
    def _is_current_sync(
        learning_database: LearningDatabase,
        payload: EvaluationJobPayload,
    ) -> bool:
        with learning_database.transaction() as repositories:
            attempt = repositories.activity_attempts.find_by_id(payload['attempt_id'])
            if (
                attempt is None
                or attempt.skill_experience_id != payload['skill_experience_id']
                or attempt.activity_id != payload['activity_id']
            ):
                return False
            evaluation = repositories.activity_evaluations.find_by_attempt_id(
                attempt.id
            )
            return (
                evaluation is not None
                and evaluation.status is ActivityEvaluationStatus.PENDING
                and evaluation.run_id == payload['run_id']
            )

    @staticmethod
    async def _evaluate(
        learning_database: LearningDatabase,
        clock_provider: ClockProvider,
        curriculum_content_provider: CurriculumContentProvider | None,
        payload: EvaluationJobPayload,
    ) -> None:
        await asyncio.to_thread(
            EvaluateChoiceActivityUseCase(
                learning_database, clock_provider, curriculum_content_provider
            ).execute,
            payload['attempt_id'],
            payload['run_id'],
        )

    @staticmethod
    async def _mark_failed(
        learning_database: LearningDatabase,
        payload: EvaluationJobPayload,
    ) -> None:
        await asyncio.to_thread(
            EvaluateChoiceActivityJob._mark_failed_sync,
            learning_database,
            payload,
        )

    @staticmethod
    def _mark_failed_sync(
        learning_database: LearningDatabase,
        payload: EvaluationJobPayload,
    ) -> None:
        with learning_database.transaction() as repositories:
            evaluation: ActivityEvaluation | None = (
                repositories.activity_evaluations.find_by_attempt_id_for_update(
                    payload['attempt_id']
                )
            )
            if (
                evaluation is None
                or evaluation.status is not ActivityEvaluationStatus.PENDING
                or evaluation.run_id != payload['run_id']
            ):
                return
            evaluation.fail('evaluation_failed')
            repositories.activity_evaluations.update(evaluation)
