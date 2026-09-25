import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.learning.core.domain.entities import (
    ActivityAttempt,
    ActivityEvaluation,
    CompetencyProgress,
)
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityEvaluationStatus,
    CompetencyProgressStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.structures import SingleChoiceAnswer
from shifu.learning.core.domain.structures import AvailableCompetencyDetail
from shifu.learning.core.domain.errors import CurriculumGapError
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases.create_goal_use_case import CreateGoalUseCase
from shifu.learning.core.use_cases.evaluate_choice_activity_use_case import (
    EvaluateChoiceActivityUseCase,
)
from shifu.learning.core.use_cases.get_diagnostic_use_case import GetDiagnosticUseCase
from shifu.learning.core.use_cases.get_competency_detail_use_case import (
    GetCompetencyDetailUseCase,
)
from shifu.learning.core.use_cases.retry_choice_evaluation_use_case import (
    RetryChoiceEvaluationUseCase,
)
from shifu.learning.core.use_cases.start_skill_use_case import StartSkillUseCase
from shifu.learning.messaging.inngest.jobs.evaluate_choice_activity_job import (
    EvaluateChoiceActivityJob,
)
from shifu.shared.core.domain.errors import NotFoundError
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumChoiceActivitySnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumContentProvider,
    IdentifierProvider,
)

NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


def catalog(gaps: tuple[str, ...] = ()) -> CurriculumSkillSnapshot:
    return CurriculumSkillSnapshot(
        id='skill',
        name='Skill',
        v2_coverage_gaps=gaps,
        competencies=(
            CurriculumCompetencySnapshot(
                id='competency',
                skill_id='skill',
                name='Competência',
                position=1,
                items=(),
                concepts=(
                    CurriculumConceptSnapshot(
                        id='concept',
                        competency_id='competency',
                        name='Conceito',
                        position=1,
                        prerequisite_ids=(),
                        observation_criteria='Critério',
                    ),
                ),
                diagnostic_activities=tuple(
                    CurriculumActivitySnapshot(
                        id=f'diagnostic-{level}',
                        title=level,
                        activity_type='diagnostic',
                        difficulty=level,
                        position=index,
                        concept_ids=('concept',),
                        question_count_by_concept=(('concept', 1),),
                        maximum_evidence_by_concept=(('concept', 1),),
                        executable_concept_evidence=True,
                    )
                    for index, level in enumerate(('easy', 'medium', 'hard'), 1)
                ),
            ),
        ),
    )


def attempt(level: str) -> ActivityAttempt:
    question = CurriculumChoiceQuestionSnapshot(
        key='q',
        kind='single_choice',
        prompt='Pergunta?',
        options=(
            CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
            CurriculumChoiceOptionSnapshot(key='b', text='B', is_correct=False),
        ),
        correct_explanation='Correta',
        incorrect_explanation='Incorreta',
        concept_criteria=(
            CurriculumChoiceConceptCriterionSnapshot(
                concept_id='concept',
                criterion='Critério',
                examples='Exemplos',
                limits='Limites',
                correct_score=Decimal('90'),
                incorrect_score=Decimal('10'),
            ),
        ),
    )
    snapshot = CurriculumChoiceActivitySnapshot(
        id=f'diagnostic-{level}',
        competency_id='competency',
        difficulty=level,
        title='Diagnóstico',
        activity_type='diagnostic',
        required_concept_ids=('concept',),
        questions=(question,),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key='q', weight_percentage=Decimal('100')
            ),
        ),
    )
    return ActivityAttempt.create(
        id=f'attempt-{level}',
        skill_experience_id='experience',
        competency_id='competency',
        activity_id=f'diagnostic-{level}',
        kind=ActivityAttemptKind.DIAGNOSTIC,
        answers=(SingleChoiceAnswer(question_key='q', selected_option_key='a'),),
        submitted_at=NOW,
        submission_key=f'key-{level}',
        grading_snapshot=snapshot,
    )


@pytest.fixture
def rig():
    database = create_autospec(LearningDatabase, instance=True)
    repositories = create_autospec(LearningDatabaseRepositories, instance=True)
    database.transaction.return_value.__enter__.return_value = repositories
    curriculum = create_autospec(CurriculumContentProvider, instance=True)
    curriculum.get_skill_content.return_value = catalog()
    clock = create_autospec(ClockProvider, instance=True)
    clock.now.return_value = NOW
    ids = create_autospec(IdentifierProvider, instance=True)
    goal = GoalFaker.fake(id='goal', account_id='account')
    experience = SkillExperienceFaker.fake(
        id='experience',
        goal_id='goal',
        skill_id='skill',
        status=SkillExperienceStatus.DIAGNOSING,
    )
    experience.policy_id = 'learning-adaptive-v2'
    progress = CompetencyProgress(
        id='progress',
        skill_experience_id='experience',
        competency_id='competency',
        content_released=False,
        created_at=NOW,
        updated_at=NOW,
        status=CompetencyProgressStatus.LEARNING,
    )
    repositories.goals.find_by_id.return_value = goal
    repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = (
        experience
    )
    repositories.skill_experiences.find_by_id_for_update.return_value = experience
    repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = progress
    repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
        progress
    ]
    return database, repositories, curriculum, clock, ids, experience, progress


def test_goal_pins_v2_only_for_eligible_catalog(rig: Any) -> None:
    database, repositories, curriculum, clock, ids, *_ = rig
    ids.generate.side_effect = ('goal-new', 'experience-new', 'progress-new')
    goal = CreateGoalUseCase(database, curriculum, clock, ids).execute(
        'account', 'Meta', 'Descrição', ('skill',)
    )
    assert goal.id == 'goal-new'
    created = repositories.skill_experiences.add_many.call_args.args[0][0]
    assert created.policy_id == 'learning-adaptive-v2'
    assert created.status is SkillExperienceStatus.NOT_STARTED
    assert (
        repositories.competency_progresses.add_many.call_args.args[0][
            0
        ].initial_progress
        is None
    )
    curriculum.get_skill_content.return_value = catalog(('coverage-gap',))
    with pytest.raises(CurriculumGapError):
        CreateGoalUseCase(database, curriculum, clock, ids).execute(
            'account', 'Meta', 'Descrição', ('skill',)
        )


def test_start_reports_safe_catalog_drift_after_owned_goal(rig: Any) -> None:
    database, repositories, curriculum, clock, _, experience, _ = rig
    experience.status = SkillExperienceStatus.NOT_STARTED
    curriculum.get_skill_content.return_value = catalog(('new-gap',))
    with pytest.raises(CurriculumGapError):
        StartSkillUseCase(database, curriculum, clock).execute(
            'account', 'goal', 'skill'
        )
    repositories.skill_experiences.update.assert_not_called()
    repositories.goals.find_by_id.return_value.account_id = 'other-account'
    with pytest.raises(NotFoundError):
        StartSkillUseCase(database, curriculum, clock).execute(
            'account', 'goal', 'skill'
        )


def test_diagnostic_failure_retry_order_and_initial_summary(rig: Any) -> None:
    database, repositories, curriculum, clock, ids, experience, progress = rig
    first = attempt('easy')
    failed = ActivityEvaluation.create(
        id='evaluation-easy',
        attempt_id=first.id,
        status=ActivityEvaluationStatus.FAILED,
        parts=(),
        started_at=NOW,
        failure_code='temporary',
        run_id='old-run',
    )
    repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
        first
    ]
    repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [failed]
    overview = GetDiagnosticUseCase(database, curriculum, clock).execute(
        'account', 'goal', 'skill'
    )
    assert (
        overview.next_activity_id,
        overview.pending_attempt_id,
        overview.pending_attempt_status,
    ) == ('diagnostic-easy', first.id, ActivityEvaluationStatus.FAILED)
    repositories.activity_attempts.find_by_id.return_value = first
    repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = (
        failed
    )
    ids.generate.return_value = 'new-run'
    RetryChoiceEvaluationUseCase(database, clock, ids).execute(
        'account', 'goal', 'skill', 'competency', first.activity_id, first.id
    )
    assert failed.run_id == 'new-run'
    assert (
        GetDiagnosticUseCase(database, curriculum, clock)
        .execute('account', 'goal', 'skill')
        .pending_attempt_status
        is ActivityEvaluationStatus.PENDING
    )
    repositories.concept_observations.find_many_by_attempt_id.return_value = []
    EvaluateChoiceActivityUseCase(database, clock, curriculum).execute(
        first.id, 'new-run'
    )
    assert failed.status is ActivityEvaluationStatus.COMPLETED
    assert failed.effect_applied_at == NOW
    repositories.events.add.assert_called_once()
    assert (
        repositories.events.add.call_args.args[0].name
        == 'learning/activity-submission.requested'
    )
    assert (
        GetDiagnosticUseCase(database, curriculum, clock)
        .execute('account', 'goal', 'skill')
        .next_activity_id
        == 'diagnostic-medium'
    )
    progress.initial_progress = Decimal('30')
    progress.current_progress = Decimal('95')
    experience.status = SkillExperienceStatus.LEARNING
    completed = GetDiagnosticUseCase(database, curriculum, clock).execute(
        'account', 'goal', 'skill'
    )
    assert completed.competencies[0].progress == Decimal('30')
    assert completed.focus_competency_id == 'competency'
    with pytest.raises(NotFoundError):
        GetDiagnosticUseCase(database, curriculum, clock).execute(
            'intruder', 'goal', 'skill'
        )
    experience.policy_id = 'learning-v1'
    with pytest.raises(NotFoundError):
        GetDiagnosticUseCase(database, curriculum, clock).execute(
            'account', 'goal', 'skill'
        )


def test_stale_pending_diagnostic_becomes_retryable_without_result_leak(
    rig: Any,
) -> None:
    database, repositories, curriculum, clock, ids, _, _ = rig
    first = attempt('easy')
    pending = ActivityEvaluation.create(
        id='evaluation-easy',
        attempt_id=first.id,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=NOW - timedelta(minutes=6),
        run_id='old-run',
    )
    repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
        first
    ]
    repositories.activity_evaluations.find_many_by_attempt_ids.return_value = [pending]
    repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = (
        pending
    )
    overview = GetDiagnosticUseCase(database, curriculum, clock).execute(
        'account', 'goal', 'skill'
    )
    assert overview.pending_attempt_status is ActivityEvaluationStatus.FAILED
    assert not hasattr(overview, 'score')
    assert pending.failure_code == 'evaluation_timeout'
    repositories.activity_attempts.find_by_id.return_value = first
    ids.generate.return_value = 'new-run'
    retry = RetryChoiceEvaluationUseCase(database, clock, ids).execute(
        'account', 'goal', 'skill', 'competency', first.activity_id, first.id
    )
    assert retry.status is ActivityEvaluationStatus.PENDING
    assert pending.run_id == 'new-run'


def test_competency_detail_keeps_unknown_progress_and_viable_previous_target(
    rig: Any,
) -> None:
    database, repositories, curriculum, _, _, experience, progress = rig
    experience.status = SkillExperienceStatus.LEARNING
    experience.recommended_concept_id = 'second'
    progress.content_released = True
    competency = CurriculumCompetencySnapshot(
        id='competency',
        skill_id='skill',
        name='Competência',
        position=1,
        concepts=tuple(
            CurriculumConceptSnapshot(
                id=concept_id,
                competency_id='competency',
                name=concept_id,
                position=index,
                prerequisite_ids=(),
                observation_criteria='Critério',
            )
            for index, concept_id in enumerate(('first', 'second'), 1)
        ),
        items=tuple(
            CurriculumActivitySnapshot(
                id=f'activity-{concept_id}',
                title=concept_id,
                activity_type='learning',
                difficulty='easy',
                position=index,
                concept_ids=(concept_id,),
                question_count_by_concept=((concept_id, 1),),
                executable_concept_evidence=True,
            )
            for index, concept_id in enumerate(('first', 'second'), 1)
        ),
    )
    curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
        id='skill', name='Skill', competencies=(competency,)
    )
    repositories.concept_observations.find_many_by_skill_experience_id.return_value = []
    repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = None
    repositories.activity_attempts.find_many_by_skill_experience_id.return_value = []
    repositories.activity_evaluations.find_many_by_attempt_ids.return_value = []
    detail = GetCompetencyDetailUseCase(database, curriculum).execute(
        'account', 'goal', 'skill', 'competency'
    )
    assert isinstance(detail, AvailableCompetencyDetail)
    assert detail.progress is None
    assert detail.adaptive is not None
    assert detail.adaptive.target_concept_id == 'second'


def test_diagnostic_resumes_in_second_competency_and_hides_scores_until_consolidated(
    rig: Any,
) -> None:
    database, repositories, curriculum, clock, _, experience, first_progress = rig
    first_competency = catalog().competencies[0]
    second_competency = CurriculumCompetencySnapshot(
        id='competency-two',
        skill_id='skill',
        name='Segunda competência',
        position=2,
        items=(),
        concepts=(
            CurriculumConceptSnapshot(
                id='concept-two',
                competency_id='competency-two',
                name='Outro conceito',
                position=1,
                prerequisite_ids=(),
                observation_criteria='Critério',
            ),
        ),
        diagnostic_activities=tuple(
            CurriculumActivitySnapshot(
                id=f'diagnostic-two-{level}',
                title=level,
                activity_type='diagnostic',
                difficulty=level,
                position=index,
                concept_ids=('concept-two',),
                question_count_by_concept=(('concept-two', 1),),
                maximum_evidence_by_concept=(('concept-two', 1),),
                executable_concept_evidence=True,
            )
            for index, level in enumerate(('easy', 'medium', 'hard'), 1)
        ),
    )
    curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
        id='skill', name='Skill', competencies=(first_competency, second_competency)
    )
    completed_attempts: list[ActivityAttempt] = []
    completed_evaluations: list[ActivityEvaluation] = []
    expected = tuple(
        (competency.id, activity.id)
        for competency in (first_competency, second_competency)
        for activity in competency.diagnostic_activities
    )
    for competency_id, activity_id in expected:
        repositories.activity_attempts.find_many_by_skill_experience_id.return_value = (
            completed_attempts
        )
        repositories.activity_evaluations.find_many_by_attempt_ids.return_value = (
            completed_evaluations
        )
        overview = GetDiagnosticUseCase(database, curriculum, clock).execute(
            'account', 'goal', 'skill'
        )
        assert (overview.next_competency_id, overview.next_activity_id) == (
            competency_id,
            activity_id,
        )
        assert overview.competencies == ()
        item = ActivityAttempt.create(
            id=f'attempt-{activity_id}',
            skill_experience_id='experience',
            competency_id=competency_id,
            activity_id=activity_id,
            kind=ActivityAttemptKind.DIAGNOSTIC,
            answers=(),
            submitted_at=NOW,
        )
        completed_attempts.append(item)
        completed_evaluations.append(
            ActivityEvaluation.create(
                id=f'evaluation-{activity_id}',
                attempt_id=item.id,
                status=ActivityEvaluationStatus.COMPLETED,
                parts=(),
                started_at=NOW,
                score=Decimal('90'),
                completed_at=NOW,
            )
        )
    second_progress = CompetencyProgress(
        id='progress-two',
        skill_experience_id='experience',
        competency_id='competency-two',
        content_released=True,
        created_at=NOW,
        updated_at=NOW,
        initial_progress=Decimal('60'),
        current_progress=Decimal('60'),
        status=CompetencyProgressStatus.LEARNING,
    )
    first_progress.initial_progress = Decimal('80')
    first_progress.current_progress = Decimal('95')
    repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
        first_progress,
        second_progress,
    ]
    experience.status = SkillExperienceStatus.LEARNING
    consolidated = GetDiagnosticUseCase(database, curriculum, clock).execute(
        'account', 'goal', 'skill'
    )
    assert consolidated.next_activity_id is None
    assert tuple(item.progress for item in consolidated.competencies) == (
        Decimal('80'),
        Decimal('60'),
    )


def test_final_diagnostic_handles_missing_current_evaluation_and_emits_only_summary(
    rig: Any,
) -> None:
    database, repositories, curriculum, clock, _, experience, progress = rig
    attempts = [attempt(level) for level in ('easy', 'medium', 'hard')]
    prior = [
        ActivityEvaluation.create(
            id=f'evaluation-{level}',
            attempt_id=item.id,
            status=ActivityEvaluationStatus.COMPLETED,
            parts=(),
            started_at=NOW,
            score=Decimal('90'),
            completed_at=NOW,
        )
        for level, item in zip(('easy', 'medium'), attempts[:2], strict=True)
    ]
    current = ActivityEvaluation.create(
        id='evaluation-hard',
        attempt_id=attempts[-1].id,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=NOW,
        run_id='run-hard',
    )
    repositories.activity_attempts.find_by_id.return_value = attempts[-1]
    repositories.activity_attempts.find_many_by_skill_experience_id.return_value = (
        attempts
    )
    repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = (
        current
    )
    repositories.activity_evaluations.find_many_by_attempt_ids.return_value = prior
    repositories.concept_observations.find_many_by_attempt_id.return_value = []
    repositories.concept_observations.find_many_by_skill_experience_id.return_value = []
    EvaluateChoiceActivityUseCase(database, clock, curriculum).execute(
        attempts[-1].id, 'run-hard'
    )
    assert current.effect_applied_at == NOW
    assert experience.status is SkillExperienceStatus.LEARNING
    assert progress.initial_progress == Decimal('90')
    assert [call.args[0].name for call in repositories.events.add.call_args_list] == [
        'learning/diagnostic-completed'
    ]


def test_frozen_diagnostic_rubric_survives_new_catalog_coverage_gap(rig: Any) -> None:
    database, repositories, curriculum, clock, _, experience, _ = rig
    current_attempt = attempt('easy')
    current = ActivityEvaluation.create(
        id='evaluation-easy',
        attempt_id=current_attempt.id,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=NOW,
        run_id='run-easy',
    )
    repositories.activity_attempts.find_by_id.return_value = current_attempt
    repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
        current_attempt
    ]
    repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = (
        current
    )
    repositories.activity_evaluations.find_many_by_attempt_ids.return_value = []
    repositories.concept_observations.find_many_by_attempt_id.return_value = []
    curriculum.get_skill_content.return_value = catalog(('new-gap',))
    EvaluateChoiceActivityUseCase(database, clock, curriculum).execute(
        current_attempt.id, 'run-easy'
    )
    assert current.effect_applied_at == NOW
    assert experience.status is SkillExperienceStatus.DIAGNOSING
    repositories.events.add.assert_not_called()


def test_review_job_accepts_kind_and_scores_without_changing_completed_progress(
    rig: Any,
) -> None:
    database, repositories, curriculum, clock, _, experience, progress = rig
    experience.status = SkillExperienceStatus.COMPLETED
    progress.current_progress = Decimal('90')
    base = attempt('easy')
    frozen = base.grading_snapshot
    assert frozen is not None
    review = ActivityAttempt.create(
        id='review-attempt',
        skill_experience_id='experience',
        competency_id='competency',
        activity_id='diagnostic-easy',
        kind=ActivityAttemptKind.REVIEW,
        answers=base.answers,
        submitted_at=NOW,
        submission_key='review-key',
        grading_snapshot=replace(frozen, activity_type='learning'),
    )
    evaluation = ActivityEvaluation.create(
        id='review-evaluation',
        attempt_id=review.id,
        status=ActivityEvaluationStatus.PENDING,
        parts=(),
        started_at=NOW,
        run_id='review-run',
    )
    payload = asyncio.run(
        EvaluateChoiceActivityJob._normalize_payload(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            {
                'attempt_id': review.id,
                'run_id': 'review-run',
                'skill_experience_id': experience.id,
                'activity_id': review.activity_id,
                'kind': 'review',
                'requested_at': NOW.isoformat(),
            }
        )
    )
    assert payload['kind'] == 'review'
    repositories.activity_attempts.find_by_id.return_value = review
    repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = (
        evaluation
    )
    EvaluateChoiceActivityUseCase(database, clock, curriculum).execute(
        review.id, 'review-run'
    )
    assert evaluation.status is ActivityEvaluationStatus.COMPLETED
    assert evaluation.effect_applied_at == NOW
    assert progress.current_progress == Decimal('90')
    repositories.concept_observations.add_many.assert_not_called()
    repositories.events.add.assert_not_called()
    EvaluateChoiceActivityUseCase(database, clock, curriculum).execute(
        review.id, 'review-run'
    )
    repositories.activity_evaluations.update.assert_called_once_with(evaluation)
