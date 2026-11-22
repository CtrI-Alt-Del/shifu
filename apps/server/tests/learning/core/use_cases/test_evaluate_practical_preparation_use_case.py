"""Grading, evidence and closure without grade for a practical preparation attempt."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import GoalFaker, SkillExperienceFaker
from shifu.fakers.shared.curriculum_practical_preparation_question_snapshot_faker import (
    CurriculumPracticalPreparationQuestionSnapshotFaker,
)
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
from shifu.learning.core.domain.errors import (
    EvaluationPendingError,
    EvaluationUnavailableError,
)
from shifu.learning.core.domain.structures import (
    PracticalPreparationAnswer,
    PracticalPreparationResult,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import EvaluateChoiceActivityUseCase
from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumLearningActivitySnapshot,
    CurriculumSkillSnapshot,
    PracticeCriterionDecision,
    PracticePhotoDecisions,
    PracticeRecordDecision,
)
from shifu.shared.core.interfaces import ClockProvider, CurriculumContentProvider

NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)
SUBMITTED_AT = NOW - timedelta(minutes=2)
ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
EXPERIENCE_ID = 'experience-1'
COMPETENCY_ID = 'competency-1'
ACTIVITY_ID = 'activity-1'
QUESTION_KEY = 'sauteed-vegetables'
CUT = 'cut-regularity'
TECHNIQUE = 'observable-technique'
PRESENTATION = 'presentation'


def criterion(key: str, level: int | None) -> PracticeCriterionDecision:
    return PracticeCriterionDecision(
        key=key,
        level=level,  # pyright: ignore[reportArgumentType] - allowed levels are checked by the use case
        comment_key=f'{key}-{level}' if level is not None else None,
    )


def records(*, cuts_sufficient: bool = True) -> tuple[PracticeRecordDecision, ...]:
    return (
        PracticeRecordDecision(record_key='cuts', sufficient=cuts_sufficient),
        PracticeRecordDecision(record_key='during', sufficient=True),
        PracticeRecordDecision(record_key='final', sufficient=True),
    )


def decisions(
    cut: int | None, technique: int | None, presentation: int | None, **flags: bool
) -> PracticePhotoDecisions:
    return PracticePhotoDecisions(
        criteria=(
            criterion(CUT, cut),
            criterion(TECHNIQUE, technique),
            criterion(PRESENTATION, presentation),
        ),
        records=records(**flags),
    )


def snapshot(
    concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...]
    | None = None,
) -> CurriculumLearningActivitySnapshot:
    return CurriculumLearningActivitySnapshot(
        id=ACTIVITY_ID,
        competency_id=COMPETENCY_ID,
        difficulty='easy',
        title='Legumes salteados',
        questions=(
            CurriculumPracticalPreparationQuestionSnapshotFaker.fake(
                concept_criteria=concept_criteria
            ),
        ),
        parts=(
            CurriculumChoicePartSnapshot(
                question_key=QUESTION_KEY, weight_percentage=Decimal(100)
            ),
        ),
        required_concept_ids=('concept-1',),
        activity_type='learning',
        schema_version=1,
        revision='revision-1',
    )


class TestEvaluatePracticalPreparationUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.clock = create_autospec(ClockProvider, instance=True)
        self.clock.now.return_value = NOW
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.experience = SkillExperienceFaker.fake(
            id=EXPERIENCE_ID, goal_id=GOAL_ID, skill_id=SKILL_ID
        )
        self.experience.status = SkillExperienceStatus.LEARNING
        self.curriculum = create_autospec(CurriculumContentProvider, instance=True)
        self.curriculum.get_skill_content.return_value = CurriculumSkillSnapshot(
            id=SKILL_ID,
            name='Culinária',
            competencies=(
                CurriculumCompetencySnapshot(
                    id=COMPETENCY_ID,
                    skill_id=SKILL_ID,
                    name='Salteados',
                    position=1,
                    concepts=(
                        CurriculumConceptSnapshot(
                            id='concept-1',
                            competency_id=COMPETENCY_ID,
                            name='Cortes regulares',
                            position=1,
                            prerequisite_ids=(),
                            observation_criteria='Cortes de tamanho parecido',
                        ),
                    ),
                    items=(
                        CurriculumActivitySnapshot(
                            id=ACTIVITY_ID,
                            title='Legumes salteados',
                            activity_type='learning',
                            difficulty='easy',
                            position=1,
                            concept_ids=('concept-1',),
                            required_concept_ids=('concept-1',),
                            question_count_by_concept=(('concept-1', 1),),
                            maximum_evidence_by_concept=(('concept-1', 1),),
                            executable_concept_evidence=True,
                        ),
                    ),
                ),
            ),
        )
        self.progress = CompetencyProgress(
            id='progress-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            content_released=True,
            created_at=NOW,
            updated_at=NOW,
            initial_progress=Decimal(0),
            current_progress=Decimal(0),
            status=CompetencyProgressStatus.LEARNING,
        )
        self.evaluation = ActivityEvaluation.create(
            id='evaluation-1',
            attempt_id='attempt-1',
            status=ActivityEvaluationStatus.PENDING,
            parts=(),
            started_at=NOW,
            run_id='run-1',
        )
        self._use_snapshot(snapshot())
        self.repositories.activity_evaluations.find_by_attempt_id.return_value = (
            self.evaluation
        )
        self.repositories.activity_evaluations.find_by_attempt_id_for_update.return_value = self.evaluation
        self.repositories.skill_experiences.find_by_id_for_update.return_value = (
            self.experience
        )
        self.repositories.goals.find_by_id.return_value = self.goal
        self.repositories.competency_progresses.find_by_skill_experience_id_and_competency_id.return_value = self.progress
        self.repositories.competency_progresses.find_many_by_skill_experience_id.return_value = [
            self.progress
        ]
        self.repositories.concept_observations.find_many_by_attempt_id.return_value = []
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = []
        self.subject = EvaluateChoiceActivityUseCase(
            self.database, self.clock, self.curriculum
        )

    def _use_snapshot(
        self,
        grading: CurriculumLearningActivitySnapshot,
        kind: ActivityAttemptKind = ActivityAttemptKind.LEARNING,
    ) -> None:
        self.attempt = ActivityAttempt.create(
            id='attempt-1',
            skill_experience_id=EXPERIENCE_ID,
            competency_id=COMPETENCY_ID,
            activity_id=ACTIVITY_ID,
            kind=kind,
            answers=(
                PracticalPreparationAnswer(
                    question_key=QUESTION_KEY,
                    draft_revision=3,
                    reflection='Cortei em cubos.',
                ),
            ),
            submitted_at=SUBMITTED_AT,
            submission_key='submission-1',
            grading_snapshot=grading,
            time_zone='America/Sao_Paulo',
        )
        self.repositories.activity_attempts.find_by_id.return_value = self.attempt
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = [
            self.attempt
        ]

    def _observed_values(self) -> list[Decimal | None]:
        observations = self.repositories.concept_observations.add_many.call_args.args[2]
        return [item.value for item in observations]

    def test_should_grade_with_the_weights_of_the_rubric(self) -> None:
        assert (
            self.subject.execute(
                'attempt-1',
                'run-1',
                practical_decisions=decisions(100, 50, 0),
            )
            is True
        )

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal(60)
        (part,) = self.evaluation.parts
        assert isinstance(part, PracticalPreparationResult)
        assert part.closed_without_grade is False
        assert [
            (item.criterion_key, item.level) for item in part.criterion_results
        ] == [
            (CUT, 100),
            (TECHNIQUE, 50),
            (PRESENTATION, 0),
        ]
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.events.add.assert_called_once()

    def test_should_derive_the_concept_evidence_separately_from_the_grade(
        self,
    ) -> None:
        capped = CurriculumChoiceConceptCriterionSnapshot(
            concept_id='concept-1',
            criterion='Prepara legumes salteados com cortes regulares.',
            examples='Cortes de tamanho parecido.',
            limits='As fotos não medem sabor.',
            correct_score=Decimal(80),
            incorrect_score=Decimal(0),
        )
        self._use_snapshot(snapshot((capped,)))

        self.subject.execute(
            'attempt-1', 'run-1', practical_decisions=decisions(100, 100, 100)
        )

        assert self.evaluation.score == Decimal(100)
        assert self._observed_values() == [Decimal(80)]

    def test_should_never_use_the_reflection_in_grade_or_evidence(self) -> None:
        self.subject.execute(
            'attempt-1', 'run-1', practical_decisions=decisions(75, 75, 75)
        )

        assert self.evaluation.score == Decimal(75)
        assert self._observed_values() == [Decimal(75)]

    def test_should_keep_the_evaluation_recoverable_for_an_incomplete_result(
        self,
    ) -> None:
        incomplete = PracticePhotoDecisions(
            criteria=(criterion(CUT, 100), criterion(TECHNIQUE, 100)),
            records=records(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute('attempt-1', 'run-1', practical_decisions=incomplete)

        self._assert_unresolved()

    def test_should_reject_a_comment_that_is_not_the_one_of_the_level(self) -> None:
        mismatched = PracticePhotoDecisions(
            criteria=(
                PracticeCriterionDecision(key=CUT, level=100, comment_key=f'{CUT}-25'),
                criterion(TECHNIQUE, 100),
                criterion(PRESENTATION, 100),
            ),
            records=records(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute('attempt-1', 'run-1', practical_decisions=mismatched)

        self._assert_unresolved()

    def test_should_reject_a_comment_that_is_not_in_the_rubric(self) -> None:
        unknown = PracticePhotoDecisions(
            criteria=(
                PracticeCriterionDecision(
                    key=CUT, level=100, comment_key='invented-comment'
                ),
                criterion(TECHNIQUE, 100),
                criterion(PRESENTATION, 100),
            ),
            records=records(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute('attempt-1', 'run-1', practical_decisions=unknown)

        self._assert_unresolved()

    def test_should_reject_a_criterion_outside_the_rubric(self) -> None:
        foreign = PracticePhotoDecisions(
            criteria=(
                criterion(CUT, 100),
                criterion(TECHNIQUE, 100),
                criterion(PRESENTATION, 100),
                criterion('taste', 100),
            ),
            records=records(),
        )

        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute('attempt-1', 'run-1', practical_decisions=foreign)

        self._assert_unresolved()

    def test_should_not_close_without_grade_for_an_inconclusive_criterion_alone(
        self,
    ) -> None:
        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(
                'attempt-1',
                'run-1',
                practical_decisions=decisions(100, None, 100),
            )

        self._assert_unresolved()

    def test_should_not_close_when_the_record_is_reported_sufficient(self) -> None:
        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute(
                'attempt-1',
                'run-1',
                practical_decisions=decisions(None, 100, 100, cuts_sufficient=True),
            )

        self._assert_unresolved()

    def test_should_close_without_grade_when_an_insufficiency_rule_is_met(
        self,
    ) -> None:
        assert (
            self.subject.execute(
                'attempt-1',
                'run-1',
                practical_decisions=decisions(None, 75, 50, cuts_sufficient=False),
            )
            is True
        )

        assert self.evaluation.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        assert self.evaluation.score is None
        assert self.evaluation.effect_applied_at is None
        assert self.evaluation.completed_at == NOW
        (part,) = self.evaluation.parts
        assert isinstance(part, PracticalPreparationResult)
        assert part.closed_without_grade is True
        assert part.score is None
        assert part.unassessable_record_keys == ('cuts',)
        assert [item.level for item in part.criterion_results] == [None, 75, 50]
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )

    def test_should_open_the_concept_verification_with_an_inconclusive_observation(
        self,
    ) -> None:
        self.subject.execute(
            'attempt-1',
            'run-1',
            practical_decisions=decisions(None, 75, 50, cuts_sufficient=False),
        )

        assert self._observed_values() == [None]
        self.repositories.concept_states.upsert_many.assert_called_once()

    def test_should_emit_no_xp_event_and_no_progress_effect_when_closed(self) -> None:
        self.subject.execute(
            'attempt-1',
            'run-1',
            practical_decisions=decisions(None, 75, 50, cuts_sufficient=False),
        )

        self.repositories.events.add.assert_not_called()
        assert self.evaluation.progress_before is None
        assert self.evaluation.progress_after is None
        assert self.evaluation.status_after is None

    def test_should_not_allow_retrying_a_closed_evaluation(self) -> None:
        self.subject.execute(
            'attempt-1',
            'run-1',
            practical_decisions=decisions(None, 75, 50, cuts_sufficient=False),
        )

        with pytest.raises(EvaluationPendingError):
            self.evaluation.retry(NOW, 'run-2')

    def test_should_do_nothing_when_the_experience_was_removed_meanwhile(self) -> None:
        self.repositories.skill_experiences.find_by_id_for_update.return_value = None

        assert (
            self.subject.execute(
                'attempt-1', 'run-1', practical_decisions=decisions(100, 100, 100)
            )
            is False
        )

        self.repositories.concept_observations.add_many.assert_not_called()
        self.repositories.events.add.assert_not_called()
        assert self.evaluation.status is ActivityEvaluationStatus.PENDING

    def test_should_ignore_a_stale_run(self) -> None:
        assert (
            self.subject.execute(
                'attempt-1', 'run-0', practical_decisions=decisions(100, 100, 100)
            )
            is False
        )

        assert self.evaluation.status is ActivityEvaluationStatus.PENDING

    def test_should_refuse_decisions_for_an_activity_without_a_practical_question(
        self,
    ) -> None:
        with pytest.raises(EvaluationUnavailableError):
            self.subject.execute('attempt-1', 'run-1')

        self._assert_unresolved()

    def test_should_not_reopen_a_closed_evaluation(self) -> None:
        self.subject.execute(
            'attempt-1',
            'run-1',
            practical_decisions=decisions(None, 75, 50, cuts_sufficient=False),
        )

        assert (
            self.subject.execute(
                'attempt-1', 'run-1', practical_decisions=decisions(100, 100, 100)
            )
            is False
        )
        assert self.evaluation.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE

    def _assert_unresolved(self) -> None:
        assert self.evaluation.status is ActivityEvaluationStatus.PENDING
        assert self.evaluation.parts == ()
        self.repositories.events.add.assert_not_called()
        self.repositories.concept_observations.add_many.assert_not_called()

    def _as_review(self) -> None:
        self.experience.status = SkillExperienceStatus.COMPLETED
        self._use_snapshot(snapshot(), ActivityAttemptKind.REVIEW)

    def test_should_grade_a_review_attempt_without_new_evidence_or_xp(self) -> None:
        self._as_review()

        assert (
            self.subject.execute(
                'attempt-1', 'run-1', practical_decisions=decisions(100, 50, 0)
            )
            is True
        )

        assert self.evaluation.status is ActivityEvaluationStatus.COMPLETED
        assert self.evaluation.score == Decimal(60)
        assert self.evaluation.effect_applied_at == NOW
        self.repositories.concept_observations.add_many.assert_not_called()
        self.repositories.events.add.assert_not_called()

    def test_should_close_a_review_attempt_without_grade_and_settle_it(self) -> None:
        self._as_review()

        assert (
            self.subject.execute(
                'attempt-1',
                'run-1',
                practical_decisions=decisions(None, 75, 50, cuts_sufficient=False),
            )
            is True
        )

        assert self.evaluation.status is ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE
        assert self.evaluation.effect_applied_at is None
        self.repositories.activity_evaluations.update.assert_called_once_with(
            self.evaluation
        )
