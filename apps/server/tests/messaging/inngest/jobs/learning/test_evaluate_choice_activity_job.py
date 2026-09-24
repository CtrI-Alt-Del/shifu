from datetime import UTC, datetime
from decimal import Decimal
import time
from typing import cast

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine

from shifu.curriculum.core.domain.entities import Activity
from shifu.curriculum.core.domain.enums import ActivityDifficulty
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    MultipleSelectionQuestion,
    SingleChoiceQuestion,
)
from shifu.curriculum.providers.curriculum_content_provider import (
    DatabaseCurriculumContentProvider,
)
from shifu.curriculum.database.sqlalchemy import SqlalchemyCurriculumDatabase
from shifu.fakers.curriculum.entities import (
    ActivityFaker,
    CompetencyFaker,
    SkillFaker,
)
from shifu.fakers.identity.entities import AccountFaker
from shifu.fakers.learning.entities import (
    CompetencyProgressFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.identity.database.sqlalchemy import SqlalchemyIdentityDatabase
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    SkillExperience,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.domain.structures import (
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.database.sqlalchemy.models import (
    CompetencyProgressModel,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.database.sqlalchemy.serialization import Serialization
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.inngest_fixture import InngestFixture


class TestEvaluateChoiceActivityJob:
    def test_registered_job_processes_outbox_duplicate_stale_failure_and_deletion(
        self,
        inngest_fixture: InngestFixture,
    ) -> None:
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database, provider, ids, activity, experience = _seed(engine)
            now = SystemClockProvider().now()

            delivery_started_at = time.monotonic()
            valid_attempt, valid_evaluation, valid_event = _add_attempt(
                database,
                provider,
                ids,
                activity.id,
                experience.id,
                now,
                valid_answers=True,
                publish_to_outbox=True,
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_completed attempt_id={valid_attempt.id} '
                f'run_id={valid_evaluation.run_id}',
                timeout=10,
            )
            assert time.monotonic() - delivery_started_at < 10
            completed = _evaluation(database, valid_attempt.id)
            assert completed.status is ActivityEvaluationStatus.COMPLETED
            assert completed.score == 100
            assert completed.effect_applied_at is not None
            progress_after_completion = _progress_current(engine)
            assert progress_after_completion > 0
            assert _evaluated_event_count(engine) == 1
            assert _outbox_status(engine, valid_event.name) == 'published'

            duplicate = ActivitySubmissionRequestedEvent(payload=valid_event.payload)
            inngest_fixture.publish(
                duplicate.name,
                cast(
                    'dict[str, object]',
                    Serialization.serialize_value(duplicate.payload),
                ),
                event_id=ids.generate(),
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_stale_run attempt_id={valid_attempt.id} '
                f'run_id={valid_evaluation.run_id}'
            )
            assert _evaluated_event_count(engine) == 1
            assert _evaluation(database, valid_attempt.id).score == 100
            assert _progress_current(engine) == progress_after_completion

            stale_attempt, stale_evaluation, stale_event = _add_attempt(
                database,
                provider,
                ids,
                activity.id,
                experience.id,
                now,
                valid_answers=True,
                publish_to_outbox=False,
            )
            stale_payload = ActivitySubmissionRequestedPayload(
                attempt_id=stale_attempt.id,
                run_id=ids.generate(),
                skill_experience_id=experience.id,
                activity_id=activity.id,
                kind=ActivityAttemptKind.LEARNING,
                requested_at=now.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
            )
            stale_event = ActivitySubmissionRequestedEvent(payload=stale_payload)
            inngest_fixture.publish(
                stale_event.name,
                cast(
                    'dict[str, object]',
                    Serialization.serialize_value(stale_event.payload),
                ),
                event_id=ids.generate(),
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_stale_run attempt_id={stale_attempt.id} '
                f'run_id={stale_payload.run_id}'
            )
            still_pending = _evaluation(database, stale_attempt.id)
            assert still_pending.status is ActivityEvaluationStatus.PENDING
            assert still_pending.run_id == stale_evaluation.run_id
            assert still_pending.score is None

            failed_attempt, failed_evaluation, _ = _add_attempt(
                database,
                provider,
                ids,
                activity.id,
                experience.id,
                now,
                valid_answers=False,
                publish_to_outbox=True,
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_failure_handled attempt_id={failed_attempt.id} '
                f'run_id={failed_evaluation.run_id}'
            )
            failed = _evaluation(database, failed_attempt.id)
            assert failed.status is ActivityEvaluationStatus.FAILED
            assert failed.failure_code == 'evaluation_failed'
            assert failed.score is None
            assert failed.effect_applied_at is None
            assert _evaluated_event_count(engine) == 1

            deleted_attempt, deleted_evaluation, _ = _add_attempt(
                database,
                provider,
                ids,
                activity.id,
                experience.id,
                now,
                valid_answers=True,
                publish_to_outbox=False,
            )
            with engine.begin() as connection:
                connection.execute(
                    text(
                        'DELETE FROM learning_skill_experiences '
                        'WHERE id = :experience_id'
                    ),
                    {'experience_id': experience.id},
                )
            deleted_payload = ActivitySubmissionRequestedPayload(
                attempt_id=deleted_attempt.id,
                run_id=deleted_evaluation.run_id or '',
                skill_experience_id=experience.id,
                activity_id=activity.id,
                kind=ActivityAttemptKind.LEARNING,
                requested_at=now.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
            )
            deleted_event = ActivitySubmissionRequestedEvent(payload=deleted_payload)
            inngest_fixture.publish(
                deleted_event.name,
                cast(
                    'dict[str, object]',
                    Serialization.serialize_value(deleted_event.payload),
                ),
                event_id=ids.generate(),
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_stale_run attempt_id={deleted_attempt.id} '
                f'run_id={deleted_payload.run_id}'
            )
            assert _experience_count(engine, experience.id) == 0
            assert _evaluated_event_count(engine) == 1
        finally:
            engine.dispose()


def _seed(
    engine: Engine,
) -> tuple[
    SqlalchemyLearningDatabase,
    DatabaseCurriculumContentProvider,
    SystemIdentifierProvider,
    Activity,
    SkillExperience,
]:
    ids = SystemIdentifierProvider()
    now = SystemClockProvider().now()
    account = AccountFaker.fake(created_at=now)
    skill = SkillFaker.fake()
    competency = CompetencyFaker.fake(skill_id=skill.id)
    activity = ActivityFaker.fake(
        competency_id=competency.id,
        difficulty=ActivityDifficulty.EASY,
        questions=(
            SingleChoiceQuestion(
                key='question-one',
                prompt='Pergunta um?',
                options=(
                    ChoiceOption(key='correct', text='Correta', is_correct=True),
                    ChoiceOption(key='incorrect', text='Incorreta', is_correct=False),
                ),
                correct_explanation='Correta',
                incorrect_explanation='Incorreta',
            ),
            MultipleSelectionQuestion(
                key='question-two',
                prompt='Pergunta dois?',
                options=(
                    ChoiceOption(key='correct', text='Correta', is_correct=True),
                    ChoiceOption(
                        key='correct-two', text='Também correta', is_correct=True
                    ),
                    ChoiceOption(key='incorrect', text='Incorreta', is_correct=False),
                ),
                correct_explanation='Correta',
                incorrect_explanation='Incorreta',
            ),
            SingleChoiceQuestion(
                key='question-three',
                prompt='Pergunta três?',
                options=(
                    ChoiceOption(key='correct', text='Correta', is_correct=True),
                    ChoiceOption(key='incorrect', text='Incorreta', is_correct=False),
                ),
                correct_explanation='Correta',
                incorrect_explanation='Incorreta',
            ),
        ),
    )
    goal = GoalFaker.fake(account_id=account.id, created_at=now, updated_at=now)
    experience = SkillExperienceFaker.fake(
        goal_id=goal.id,
        skill_id=skill.id,
        created_at=now,
        updated_at=now,
    )
    progress = CompetencyProgressFaker.fake(
        skill_experience_id=experience.id,
        competency_id=competency.id,
        content_released=True,
        initial_progress=Decimal('0'),
        current_progress=Decimal('0'),
        status=CompetencyProgressStatus.LEARNING,
        created_at=now,
        updated_at=now,
    )
    identity_database = SqlalchemyIdentityDatabase(engine, id_provider=ids)
    with identity_database.transaction() as repositories:
        repositories.accounts.add(account)
    curriculum_database = SqlalchemyCurriculumDatabase(engine)
    with curriculum_database.transaction() as repositories:
        repositories.skills.add_many([skill])
        repositories.competencies.add_many([competency])
        repositories.activities.add_many([activity])
    learning_database = SqlalchemyLearningDatabase(engine, id_provider=ids)
    with learning_database.transaction() as repositories:
        repositories.goals.add(goal)
        repositories.skill_experiences.add_many([experience])
        repositories.competency_progresses.add(progress)
    provider = DatabaseCurriculumContentProvider(curriculum_database)
    assert provider.get_choice_activity(activity.id) is not None
    return learning_database, provider, ids, activity, experience


def _add_attempt(
    database: SqlalchemyLearningDatabase,
    provider: DatabaseCurriculumContentProvider,
    ids: SystemIdentifierProvider,
    activity_id: str,
    experience_id: str,
    now: datetime,
    *,
    valid_answers: bool,
    publish_to_outbox: bool,
) -> tuple[
    ActivityAttempt,
    ActivityEvaluation,
    ActivitySubmissionRequestedEvent,
]:
    snapshot = provider.get_choice_activity(activity_id)
    assert snapshot is not None
    answers = (
        tuple(
            (
                MultipleSelectionAnswer(
                    question_key=question.key,
                    selected_option_keys=('correct', 'correct-two'),
                )
                if question.kind == 'multiple_selection'
                else SingleChoiceAnswer(
                    question_key=question.key,
                    selected_option_key='correct',
                )
            )
            for question in snapshot.questions
        )
        if valid_answers
        else ()
    )
    attempt = ActivityAttempt.create(
        id=ids.generate(),
        skill_experience_id=experience_id,
        competency_id=snapshot.competency_id,
        activity_id=activity_id,
        kind=ActivityAttemptKind.LEARNING,
        answers=answers,
        submitted_at=now,
        submission_key=ids.generate(),
        grading_snapshot=snapshot,
    )
    evaluation = ActivityEvaluation.create(
        id=ids.generate(),
        attempt_id=attempt.id,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=now,
        run_id=ids.generate(),
    )
    event = ActivitySubmissionRequestedEvent(
        payload=ActivitySubmissionRequestedPayload(
            attempt_id=attempt.id,
            run_id=evaluation.run_id or '',
            skill_experience_id=experience_id,
            activity_id=activity_id,
            kind=ActivityAttemptKind.LEARNING,
            requested_at=now.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
        )
    )
    with database.transaction() as repositories:
        repositories.activity_attempts.add(attempt)
        repositories.activity_evaluations.add(evaluation)
        if publish_to_outbox:
            repositories.events.add(event)
    return attempt, evaluation, event


def _evaluation(
    database: SqlalchemyLearningDatabase,
    attempt_id: str,
) -> ActivityEvaluation:
    with database.transaction() as repositories:
        evaluation = repositories.activity_evaluations.find_by_attempt_id(attempt_id)
        assert evaluation is not None
        return evaluation


def _progress_current(engine: Engine) -> Decimal:
    with engine.connect() as connection:
        return connection.scalar(
            select(CompetencyProgressModel.current_progress)
        ) or Decimal('0')


def _evaluated_event_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return (
            connection.scalar(
                select(func.count())
                .select_from(EventModel)
                .where(EventModel.name == 'learning/activity-evaluated')
            )
            or 0
        )


def _outbox_status(engine: Engine, event_name: str) -> str | None:
    with engine.connect() as connection:
        return connection.scalar(
            select(EventModel.status)
            .where(EventModel.name == event_name)
            .order_by(EventModel.created_at.desc())
            .limit(1)
        )


def _experience_count(engine: Engine, experience_id: str) -> int:
    with engine.connect() as connection:
        return (
            connection.scalar(
                text('SELECT COUNT(*) FROM learning_skill_experiences WHERE id = :id'),
                {'id': experience_id},
            )
            or 0
        )
