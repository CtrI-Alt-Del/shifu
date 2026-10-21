import math
from datetime import datetime
from sqlalchemy import delete, select, update, func
from sqlalchemy.orm import Session

from shifu.intelligence.core.domain.entities import MentorResponseAttempt
from shifu.intelligence.core.domain.enums import MentorResponseStatus
from shifu.intelligence.core.domain.structures import MentorInferenceUsage
from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.intelligence.database.sqlalchemy.models import (
    MentorResponseAttemptModel,
    MentorResponseSubmissionModel,
)
from shifu.intelligence.database.sqlalchemy.mappers import MentorResponseAttemptMapper


class SqlalchemyMentorResponseAttemptsRepository:
    def __init__(self, session: Session) -> None:
        self._session: Session = session

    def journal_usage(
        self,
        attempt_id: str,
        owner: str,
        access_revision: str,
        usage: MentorInferenceUsage,
    ) -> bool:
        model = self._session.scalar(
            select(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.id == attempt_id,
                MentorResponseAttemptModel.execution_owner == owner,
                MentorResponseAttemptModel.access_revision == access_revision,
            )
            .with_for_update()
        )
        if model is None or model.usage_calls is None:
            return False
        existing = next(
            (call for call in model.usage_calls if call['call_key'] == usage.call_key),
            None,
        )
        value = {
            'call_key': usage.call_key,
            'profile': usage.profile,
            'used_tokens': usage.used_tokens,
            'input_tokens': usage.input_tokens,
            'output_tokens': usage.output_tokens,
            'cost_usd': usage.cost_usd,
        }
        if existing is not None:
            if any(
                existing.get(key) != value[key]
                for key in ('call_key', 'profile', 'used_tokens')
            ) or any(
                existing.get(key) is not None and existing.get(key) != value[key]
                for key in ('input_tokens', 'output_tokens', 'cost_usd')
            ):
                raise ServiceUnavailableError
            if any(
                existing.get(key) is None and value[key] is not None
                for key in ('input_tokens', 'output_tokens', 'cost_usd')
            ):
                model.usage_calls = [
                    value if call['call_key'] == usage.call_key else call
                    for call in model.usage_calls
                ]
            return True
        model.usage_calls = [*model.usage_calls, value]
        return True

    def read_usage(self, attempt_id: str) -> tuple[MentorInferenceUsage, ...] | None:
        model = self._session.get(MentorResponseAttemptModel, attempt_id)
        if model is None or model.usage_calls is None:
            return None
        calls: list[MentorInferenceUsage] = []
        for call in model.usage_calls:
            key, profile, tokens = (
                call['call_key'],
                call['profile'],
                call['used_tokens'],
            )
            input_tokens = call.get('input_tokens')
            output_tokens = call.get('output_tokens')
            cost_usd = call.get('cost_usd')
            if (
                not isinstance(key, str)
                or not isinstance(profile, str)
                or (
                    tokens is not None
                    and (
                        not isinstance(tokens, int)
                        or isinstance(tokens, bool)
                        or tokens < 0
                    )
                )
                or (
                    input_tokens is not None
                    and (
                        not isinstance(input_tokens, int)
                        or isinstance(input_tokens, bool)
                        or input_tokens < 0
                    )
                )
                or (
                    output_tokens is not None
                    and (
                        not isinstance(output_tokens, int)
                        or isinstance(output_tokens, bool)
                        or output_tokens < 0
                    )
                )
                or (
                    cost_usd is not None
                    and (
                        not isinstance(cost_usd, (int, float))
                        or isinstance(cost_usd, bool)
                        or not math.isfinite(cost_usd)
                        or cost_usd < 0
                    )
                )
            ):
                raise ServiceUnavailableError
            calls.append(
                MentorInferenceUsage(
                    call_key=key,
                    profile=profile,
                    used_tokens=tokens,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=float(cost_usd) if cost_usd is not None else None,
                )
            )
        return tuple(calls)

    def inference_started(self, attempt_id: str) -> bool:
        model = self._session.get(MentorResponseAttemptModel, attempt_id)
        return model is None or bool(model.generation_keys)

    def claim(
        self,
        attempt_id: str,
        owner: str,
        now: datetime,
        expires_at: datetime,
        access_revision: str,
    ) -> bool:
        claimed = self._session.scalar(
            update(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.id == attempt_id,
                MentorResponseAttemptModel.status.in_(['queued', 'processing']),
                MentorResponseAttemptModel.access_revision == access_revision,
                (
                    MentorResponseAttemptModel.execution_owner.is_(None)
                    | (MentorResponseAttemptModel.execution_until <= now)
                    | (MentorResponseAttemptModel.execution_owner == owner)
                ),
            )
            .values(execution_owner=owner, execution_until=expires_at)
            .returning(MentorResponseAttemptModel.id)
        )
        return claimed is not None

    def renew_claim(
        self,
        attempt_id: str,
        owner: str,
        now: datetime,
        expires_at: datetime,
        access_revision: str,
    ) -> bool:
        renewed = self._session.scalar(
            update(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.id == attempt_id,
                MentorResponseAttemptModel.execution_owner == owner,
                MentorResponseAttemptModel.execution_until > now,
                MentorResponseAttemptModel.status.in_(['queued', 'processing']),
                MentorResponseAttemptModel.access_revision == access_revision,
            )
            .values(execution_until=expires_at)
            .returning(MentorResponseAttemptModel.id)
        )
        return renewed is not None

    def has_claim(self, attempt_id: str, owner: str, now: datetime) -> bool:
        return (
            self._session.scalar(
                select(MentorResponseAttemptModel.id).where(
                    MentorResponseAttemptModel.id == attempt_id,
                    MentorResponseAttemptModel.execution_owner == owner,
                    MentorResponseAttemptModel.execution_until > now,
                )
            )
            is not None
        )

    def release_claim(self, attempt_id: str, owner: str) -> None:
        self._session.execute(
            update(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.id == attempt_id,
                MentorResponseAttemptModel.execution_owner == owner,
            )
            .values(execution_owner=None, execution_until=None)
        )

    def find_continuity(self, account_id: str, session_id: str) -> tuple[str, ...]:
        model = self._session.scalar(
            select(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.account_id == account_id,
                MentorResponseAttemptModel.session_id == session_id,
                MentorResponseAttemptModel.status == 'completed',
            )
            .order_by(
                MentorResponseAttemptModel.created_at.desc(),
                MentorResponseAttemptModel.id.desc(),
            )
            .limit(1)
        )
        return tuple(model.resolved_reference_ids) if model else ()

    def update_references(
        self, attempt_id: str, reference_ids: tuple[str, ...], access_revision: str
    ) -> bool:
        updated = self._session.scalar(
            update(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.id == attempt_id,
                MentorResponseAttemptModel.status == 'processing',
                MentorResponseAttemptModel.access_revision == access_revision,
            )
            .values(resolved_reference_ids=list(reference_ids))
            .returning(MentorResponseAttemptModel.id)
        )
        return updated is not None

    def find_by_id(self, attempt_id: str) -> MentorResponseAttempt | None:
        model = self._session.get(MentorResponseAttemptModel, attempt_id)
        return MentorResponseAttemptMapper.to_entity(model) if model else None

    def find_current(
        self, account_id: str, session_id: str
    ) -> MentorResponseAttempt | None:
        model = self._session.scalar(
            select(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.account_id == account_id,
                MentorResponseAttemptModel.session_id == session_id,
            )
            .order_by(
                MentorResponseAttemptModel.created_at.desc(),
                MentorResponseAttemptModel.id.desc(),
            )
            .limit(1)
        )
        return MentorResponseAttemptMapper.to_entity(model) if model else None

    def find_by_id_for_update(self, attempt_id: str) -> MentorResponseAttempt | None:
        model = self._session.scalar(
            select(MentorResponseAttemptModel)
            .where(MentorResponseAttemptModel.id == attempt_id)
            .with_for_update()
        )
        return MentorResponseAttemptMapper.to_entity(model) if model else None

    def find_submission(
        self, account_id: str, session_id: str, submission_key: str
    ) -> tuple[MentorResponseAttempt, str] | None:
        model = self._session.scalar(
            select(MentorResponseSubmissionModel).where(
                MentorResponseSubmissionModel.account_id == account_id,
                MentorResponseSubmissionModel.session_id == session_id,
                MentorResponseSubmissionModel.submission_key == submission_key,
            )
        )
        if model is None:
            return None
        attempt = self._session.get(MentorResponseAttemptModel, model.attempt_id)
        return (
            (MentorResponseAttemptMapper.to_entity(attempt), model.fingerprint)
            if attempt
            else None
        )

    def add(self, attempt: MentorResponseAttempt) -> None:
        self._session.add(MentorResponseAttemptMapper.to_model(attempt))
        self._session.flush()

    def add_submission(
        self,
        account_id: str,
        session_id: str,
        submission_key: str,
        attempt_id: str,
        fingerprint: str,
    ) -> None:
        self._session.add(
            MentorResponseSubmissionModel(
                account_id=account_id,
                session_id=session_id,
                submission_key=submission_key,
                attempt_id=attempt_id,
                fingerprint=fingerprint,
            )
        )
        self._session.flush()

    def transition(
        self,
        attempt_id: str,
        expected_status: MentorResponseStatus,
        new_status: MentorResponseStatus,
        access_revision: str,
    ) -> bool:
        updated = self._session.scalar(
            update(MentorResponseAttemptModel)
            .where(
                MentorResponseAttemptModel.id == attempt_id,
                MentorResponseAttemptModel.status == expected_status.value,
                MentorResponseAttemptModel.access_revision == access_revision,
            )
            .values(
                status=new_status.value,
                updated_at=func.greatest(
                    func.now(), MentorResponseAttemptModel.updated_at
                ),
            )
            .returning(MentorResponseAttemptModel.id)
        )
        return updated is not None

    def reserve_generation(
        self, attempt_id: str, block_key: str, access_revision: str
    ) -> bool:
        model = self._session.scalar(
            select(MentorResponseAttemptModel)
            .where(MentorResponseAttemptModel.id == attempt_id)
            .with_for_update()
        )
        if (
            model is None
            or model.status != MentorResponseStatus.PROCESSING.value
            or model.access_revision != access_revision
            or block_key in model.generation_keys
        ):
            return False
        model.generation_keys = [*model.generation_keys, block_key]
        self._session.flush()
        return True

    def remove_by_session_id(self, session_id: str) -> None:
        self._session.execute(
            delete(MentorResponseAttemptModel).where(
                MentorResponseAttemptModel.session_id == session_id
            )
        )
