from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
import atexit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time
from threading import Thread
from typing import ClassVar, cast

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine

from shifu.curriculum.core.domain.entities import Activity, Concept
from shifu.curriculum.core.domain.enums import ActivityDifficulty, ActivityType
from shifu.curriculum.core.domain.structures import (
    ChoiceOption,
    CodeInconclusiveComment,
    CodeRubricComment,
    CodeRubricCriterion,
    CodeRubricEvaluationPart,
    ChoiceConceptCriterion,
    ActivitySequenceItem,
    CorrectnessEvaluationPart,
    CurriculumSequence,
    EvaluationRule,
    JavascriptInitialFile,
    JavascriptStdinQuestion,
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
    SkillExperienceStatus,
)
from shifu.learning.core.domain.events.activity_submission_requested_event import (
    ActivitySubmissionRequestedEvent,
    ActivitySubmissionRequestedPayload,
)
from shifu.learning.core.domain.structures import (
    CodeAnswer,
    CodeSubmittedFile,
    MultipleSelectionAnswer,
    SingleChoiceAnswer,
)
from shifu.learning.database.sqlalchemy import SqlalchemyLearningDatabase
from shifu.learning.core.use_cases import RemoveSkillFromGoalUseCase
from shifu.learning.database.sqlalchemy.models import (
    CompetencyProgressModel,
)
from shifu.shared.database.sqlalchemy.models import EventModel
from shifu.shared.database.sqlalchemy.serialization import Serialization
from shifu.shared.providers.system_clock_provider import SystemClockProvider
from shifu.shared.providers.system_identifier_provider import SystemIdentifierProvider
from tests.fixtures.inngest_fixture import InngestFixture


class _DecisionsHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, object]]] = []

    def do_POST(self) -> None:
        size = int(self.headers.get('Content-Length', '0'))
        payload = cast('dict[str, object]', json.loads(self.rfile.read(size)))
        type(self).requests.append(payload)
        state = cast('dict[str, object]', payload['state'])
        project_files = cast('list[dict[str, object]]', state['project_files'])
        if any('request-failure' in str(item['content']) for item in project_files):
            self.send_response(503)
            self.end_headers()
            return
        questions = cast('dict[str, dict[str, object]]', payload['questions'])
        answers = {
            key: {
                'type': 'choice',
                'choice': next(
                    (
                        option
                        for option in cast('dict[str, str]', question['criteria'])
                        if option.endswith('75')
                    ),
                    next(iter(cast('dict[str, str]', question['criteria']))),
                ),
            }
            for key, question in questions.items()
        }
        response = json.dumps({'answers': answers}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def _stop_decisions_api() -> None:
    _DECISIONS_SERVER.shutdown()
    _DECISIONS_SERVER.server_close()
    _DECISIONS_THREAD.join(timeout=5)
    for name, value in _PREVIOUS_OPENROUTER_ENV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


# The shared session Inngest runtime may be started by an earlier job module.
# Configure the local Decisions endpoint during collection so the app subprocess
# always starts with this test's safe endpoint and key.
_PREVIOUS_OPENROUTER_ENV = {
    name: os.environ.get(name)
    for name in ('OPENROUTER_API_KEY', 'OPENROUTER_DECISIONS_URL')
}
_DECISIONS_SERVER = ThreadingHTTPServer(('127.0.0.1', 0), _DecisionsHandler)
_DECISIONS_THREAD = Thread(target=_DECISIONS_SERVER.serve_forever, daemon=True)
_DECISIONS_THREAD.start()
os.environ['OPENROUTER_API_KEY'] = 'controlled-test-key'
os.environ['OPENROUTER_DECISIONS_URL'] = (
    f'http://127.0.0.1:{_DECISIONS_SERVER.server_port}/api/alpha/decisions'
)
atexit.register(_stop_decisions_api)


class TestEvaluateChoiceActivityJob:
    def test_registered_job_processes_outbox_duplicate_stale_failure_and_deletion(
        self,
        inngest_fixture: InngestFixture,
    ) -> None:
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database, provider, ids, activity, experience, account_id = _seed(engine)
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

            concept_id = ids.generate()
            diagnostic_activity = ActivityFaker.fake(
                competency_id=activity.competency_id,
                activity_type=ActivityType.DIAGNOSTIC,
                difficulty=ActivityDifficulty.EASY,
                questions=tuple(
                    replace(
                        question,
                        concept_criteria=(
                            ChoiceConceptCriterion(
                                concept_id=concept_id,
                                criterion='Identifies the concept rule.',
                                examples='Expected answer',
                                limits='Choice responses do not assess code.',
                                correct_score=100,
                                incorrect_score=0,
                            ),
                        ),
                    )
                    for question in activity.questions
                ),
            )
            curriculum_database = SqlalchemyCurriculumDatabase(engine)
            with curriculum_database.transaction() as repositories:
                repositories.concepts.add_many(
                    [
                        Concept(
                            id=concept_id,
                            competency_id=activity.competency_id,
                            name='Diagnostic concept',
                            description='A concept used to verify provisional scoring.',
                            position=1,
                            observation_criteria='Observe the correct choice.',
                        )
                    ]
                )
                repositories.activities.add_many([diagnostic_activity])
                repositories.curriculum_sequences.add_many(
                    [
                        CurriculumSequence(
                            competency_id=activity.competency_id,
                            items=(
                                ActivitySequenceItem(
                                    activity_id=diagnostic_activity.id,
                                    position=1,
                                ),
                            ),
                        )
                    ]
                )

            diagnostic_run_id = ids.generate()
            with database.transaction() as repositories:
                diagnostic_experience = repositories.skill_experiences.find_by_id(
                    experience.id
                )
                assert diagnostic_experience is not None
                diagnostic_experience.status = SkillExperienceStatus.DIAGNOSING
                diagnostic_experience.diagnostic_run_id = diagnostic_run_id
                repositories.skill_experiences.update(diagnostic_experience)

            diagnostic_attempt, diagnostic_evaluation, diagnostic_event = _add_attempt(
                database,
                provider,
                ids,
                diagnostic_activity.id,
                experience.id,
                now,
                valid_answers=True,
                publish_to_outbox=True,
                kind=ActivityAttemptKind.DIAGNOSTIC,
                diagnostic_run_id=diagnostic_run_id,
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_completed attempt_id={diagnostic_attempt.id} '
                f'run_id={diagnostic_evaluation.run_id}'
            )
            provisional = _evaluation(database, diagnostic_attempt.id)
            assert provisional.status is ActivityEvaluationStatus.COMPLETED
            assert provisional.score == 100
            assert provisional.effect_applied_at is None
            assert _progress_current(engine) == progress_after_completion
            assert _evaluated_event_count(engine) == 1
            assert _outbox_status(engine, diagnostic_event.name) == 'published'

            stale_diagnostic_run_id = ids.generate()
            stale_diagnostic_attempt, stale_diagnostic_evaluation, _ = _add_attempt(
                database,
                provider,
                ids,
                diagnostic_activity.id,
                experience.id,
                now,
                valid_answers=True,
                publish_to_outbox=False,
                kind=ActivityAttemptKind.DIAGNOSTIC,
                diagnostic_run_id=stale_diagnostic_run_id,
            )
            with database.transaction() as repositories:
                diagnostic_experience = repositories.skill_experiences.find_by_id(
                    experience.id
                )
                assert diagnostic_experience is not None
                diagnostic_experience.diagnostic_run_id = ids.generate()
                repositories.skill_experiences.update(diagnostic_experience)
            stale_diagnostic_event = ActivitySubmissionRequestedEvent(
                payload=ActivitySubmissionRequestedPayload(
                    attempt_id=stale_diagnostic_attempt.id,
                    run_id=stale_diagnostic_evaluation.run_id or '',
                    skill_experience_id=experience.id,
                    activity_id=diagnostic_activity.id,
                    kind=ActivityAttemptKind.DIAGNOSTIC,
                    requested_at=now.astimezone(UTC).isoformat().replace('+00:00', 'Z'),
                )
            )
            inngest_fixture.publish(
                stale_diagnostic_event.name,
                cast(
                    'dict[str, object]',
                    Serialization.serialize_value(stale_diagnostic_event.payload),
                ),
                event_id=ids.generate(),
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_stale_run '
                f'attempt_id={stale_diagnostic_attempt.id} '
                f'run_id={stale_diagnostic_evaluation.run_id}'
            )
            stale_diagnostic = _evaluation(database, stale_diagnostic_attempt.id)
            assert stale_diagnostic.status is ActivityEvaluationStatus.PENDING
            assert stale_diagnostic.score is None
            assert _progress_current(engine) == progress_after_completion
            assert _evaluated_event_count(engine) == 1

            failed_diagnostic_attempt, failed_diagnostic_evaluation, _ = _add_attempt(
                database,
                provider,
                ids,
                diagnostic_activity.id,
                experience.id,
                now,
                valid_answers=False,
                publish_to_outbox=True,
                kind=ActivityAttemptKind.DIAGNOSTIC,
                diagnostic_run_id=diagnostic_experience.diagnostic_run_id,
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_failure_handled '
                f'attempt_id={failed_diagnostic_attempt.id} '
                f'run_id={failed_diagnostic_evaluation.run_id}'
            )
            failed_diagnostic = _evaluation(database, failed_diagnostic_attempt.id)
            assert failed_diagnostic.status is ActivityEvaluationStatus.FAILED
            assert failed_diagnostic.failure_code == 'evaluation_failed'
            assert failed_diagnostic.score is None
            assert failed_diagnostic.effect_applied_at is None
            assert _progress_current(engine) == progress_after_completion
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
            RemoveSkillFromGoalUseCase(database).execute(
                account_id=account_id,
                goal_id=experience.goal_id,
                skill_id=experience.skill_id,
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

    def test_registered_job_assesses_saved_mixed_source_and_applies_effect_once(
        self,
        inngest_fixture: InngestFixture,
    ) -> None:
        _DecisionsHandler.requests.clear()
        engine = create_engine(inngest_fixture.database_url, pool_pre_ping=True)
        try:
            database, provider, ids, activity, experience = _seed_mixed(engine)
            now = SystemClockProvider().now()
            attempt, evaluation, event = _add_mixed_attempt(
                database,
                provider,
                ids,
                activity,
                experience.id,
                now,
                source_code='console.log("official source")',
                publish_to_outbox=True,
            )
            try:
                inngest_fixture.wait_for_log(
                    f'choice_activity_job_completed attempt_id={attempt.id} '
                    f'run_id={evaluation.run_id}',
                    timeout=30,
                )
            except AssertionError as error:
                failure_log = (
                    f'choice_activity_job_failure_handled attempt_id={attempt.id} '
                    f'run_id={evaluation.run_id}'
                )
                try:
                    inngest_fixture.wait_for_log(failure_log, timeout=2)
                except AssertionError:
                    raise error from None
                failed = _evaluation(database, attempt.id)
                raise AssertionError(
                    'Mixed official evaluation failed: '
                    f'failure_code={failed.failure_code!r}; '
                    f'controlled_decisions_requests={_DecisionsHandler.requests!r}'
                ) from error

            completed = _evaluation(database, attempt.id)
            assert completed.status is ActivityEvaluationStatus.COMPLETED
            assert completed.score == Decimal('90')
            assert completed.effect_applied_at is not None
            assert _progress_current(engine) > 0
            with database.transaction() as repositories:
                saved_attempt = repositories.activity_attempts.find_by_id(attempt.id)
            assert saved_attempt is not None
            saved_code_answer = saved_attempt.answers[-1]
            assert isinstance(saved_code_answer, CodeAnswer)
            assert saved_code_answer.files == (
                CodeSubmittedFile(
                    path='src/main.js', content='console.log("official source")'
                ),
            )

            progress_after_completion = _progress_current(engine)
            duplicate = ActivitySubmissionRequestedEvent(payload=event.payload)
            inngest_fixture.publish(
                duplicate.name,
                cast(
                    'dict[str, object]',
                    Serialization.serialize_value(duplicate.payload),
                ),
                event_id=ids.generate(),
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_stale_run attempt_id={attempt.id} '
                f'run_id={evaluation.run_id}'
            )
            assert _evaluated_event_count(engine) == 1
            assert _evaluation(database, attempt.id).score == Decimal('90')
            assert _progress_current(engine) == progress_after_completion

            failed_attempt, failed_evaluation, _ = _add_mixed_attempt(
                database,
                provider,
                ids,
                activity,
                experience.id,
                now,
                source_code='// request-failure',
                publish_to_outbox=True,
            )
            inngest_fixture.wait_for_log(
                f'choice_activity_job_failure_handled attempt_id={failed_attempt.id} '
                f'run_id={failed_evaluation.run_id}',
                timeout=30,
            )
            failed = _evaluation(database, failed_attempt.id)
            assert failed.status is ActivityEvaluationStatus.FAILED
            assert failed.score is None
            assert failed.effect_applied_at is None
            assert _evaluated_event_count(engine) == 1
            assert _progress_current(engine) == progress_after_completion
            assert len(_DecisionsHandler.requests) == 2
            request_state = cast(
                'dict[str, object]', _DecisionsHandler.requests[0]['state']
            )
            request_files = cast(
                'list[dict[str, object]]', request_state['project_files']
            )
            assert request_files == [
                {
                    'path': 'src/main.js',
                    'content': 'console.log("official source")',
                }
            ]
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
    str,
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
    return learning_database, provider, ids, activity, experience, account.id


def _seed_mixed(
    engine: Engine,
) -> tuple[
    SqlalchemyLearningDatabase,
    DatabaseCurriculumContentProvider,
    SystemIdentifierProvider,
    Activity,
    SkillExperience,
]:
    database, provider, ids, base_activity, experience, _account_id = _seed(engine)
    choice_questions = tuple(
        SingleChoiceQuestion(
            key=f'q{number}',
            prompt=f'Pergunta {number}?',
            options=(
                ChoiceOption(key='correct', text='Correta', is_correct=True),
                ChoiceOption(key='incorrect', text='Incorreta', is_correct=False),
            ),
            correct_explanation='Correta',
            incorrect_explanation='Incorreta',
        )
        for number in (1, 2)
    )
    code_question = JavascriptStdinQuestion(
        key='q3',
        prompt='Leia stdin e produza a saída esperada.',
        initial_files=(
            JavascriptInitialFile(
                path='src/main.js', content='console.log(0)', editable=True
            ),
        ),
        entrypoint='src/main.js',
        fixed_dependencies=(),
        permitted_commands=(),
        concept_criteria=(),
    )
    criterion = CodeRubricCriterion(
        key='correctness',
        name='Correção',
        description='A saída corresponde à especificação.',
        weight_percentage=100,
        required=True,
        fixed_comments=tuple(
            CodeRubricComment(
                id=f'comment-{level}', level=level, text=f'Comment {level}'
            )
            for level in (0, 25, 50, 75, 100)
        ),
        inconclusive_comment=CodeInconclusiveComment(
            id='comment-inconclusive', text='Inconclusivo'
        ),
    )
    activity = Activity.create(
        id=ids.generate(),
        competency_id=base_activity.competency_id,
        activity_type=ActivityType.LEARNING,
        difficulty=ActivityDifficulty.EASY,
        title='Atividade mista de integração',
        objective='Avaliar escolha e código.',
        questions=(*choice_questions, code_question),
        evaluation_rule=EvaluationRule(
            parts=(
                CorrectnessEvaluationPart(question_key='q1', weight_percentage=30),
                CorrectnessEvaluationPart(question_key='q2', weight_percentage=30),
                CodeRubricEvaluationPart(
                    question_key='q3',
                    weight_percentage=40,
                    criteria=(criterion,),
                ),
            )
        ),
    )
    curriculum_database = SqlalchemyCurriculumDatabase(engine)
    with curriculum_database.transaction() as repositories:
        repositories.activities.add_many([activity])
    provider = DatabaseCurriculumContentProvider(curriculum_database)
    assert provider.get_learning_activity(activity.id) is not None
    return database, provider, ids, activity, experience


def _add_mixed_attempt(
    database: SqlalchemyLearningDatabase,
    provider: DatabaseCurriculumContentProvider,
    ids: SystemIdentifierProvider,
    activity: Activity,
    experience_id: str,
    now: datetime,
    *,
    source_code: str,
    publish_to_outbox: bool,
) -> tuple[
    ActivityAttempt,
    ActivityEvaluation,
    ActivitySubmissionRequestedEvent,
]:
    snapshot = provider.get_learning_activity(activity.id)
    assert snapshot is not None
    attempt = ActivityAttempt.create(
        id=ids.generate(),
        skill_experience_id=experience_id,
        competency_id=activity.competency_id,
        activity_id=activity.id,
        kind=ActivityAttemptKind.LEARNING,
        answers=(
            SingleChoiceAnswer(question_key='q1', selected_option_key='correct'),
            SingleChoiceAnswer(question_key='q2', selected_option_key='correct'),
            CodeAnswer(
                question_key='q3',
                files=(CodeSubmittedFile(path='src/main.js', content=source_code),),
            ),
        ),
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
            activity_id=activity.id,
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
    kind: ActivityAttemptKind = ActivityAttemptKind.LEARNING,
    diagnostic_run_id: str | None = None,
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
        kind=kind,
        answers=answers,
        submitted_at=now,
        submission_key=ids.generate(),
        diagnostic_run_id=diagnostic_run_id,
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
            kind=kind,
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
