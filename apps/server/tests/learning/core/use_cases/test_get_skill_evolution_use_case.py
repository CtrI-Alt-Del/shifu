from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import (
    ActivityAttemptFaker,
    ActivityEvaluationFaker,
    GoalFaker,
    SkillExperienceFaker,
)
from shifu.learning.core.domain.entities import ActivityAttempt, ActivityEvaluation
from shifu.learning.core.domain.enums import (
    ActivityAttemptKind,
    ActivityDifficulty,
    ActivityEvaluationStatus,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import SkillExperienceNotFoundError
from shifu.learning.core.domain.structures import (
    ConceptObservation,
    SkillEvolution,
    SkillEvolutionPoint,
)
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import GetSkillEvolutionUseCase
from shifu.shared.core.domain.structures import (
    CurriculumCompetencySnapshot,
    CurriculumConceptSnapshot,
    CurriculumSkillSnapshot,
)
from shifu.shared.core.interfaces import CurriculumContentProvider

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
SKILL_ID = 'skill-1'
EXPERIENCE_ID = 'experience-1'
DIAGNOSTIC_AT = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
EASY = ActivityDifficulty.EASY
MEDIUM = ActivityDifficulty.MEDIUM
HARD = ActivityDifficulty.HARD


def _at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 9, day, hour, 0, tzinfo=UTC)


def _skill(*concept_ids: str) -> CurriculumSkillSnapshot:
    return CurriculumSkillSnapshot(
        id=SKILL_ID,
        name='Python para análise de dados',
        competencies=(
            CurriculumCompetencySnapshot(
                id='competency-1',
                skill_id=SKILL_ID,
                name='Limpeza de tabelas',
                position=1,
                items=(),
                concepts=tuple(
                    CurriculumConceptSnapshot(
                        id=concept_id,
                        competency_id='competency-1',
                        name=f'Conceito {concept_id}',
                        position=position,
                        prerequisite_ids=(),
                        observation_criteria='Critério observável.',
                    )
                    for position, concept_id in enumerate(concept_ids, start=1)
                ),
            ),
        ),
    )


def _observation(
    concept_id: str,
    activity_id: str,
    difficulty: ActivityDifficulty,
    completed_at: datetime,
    score: str | None,
    *,
    diagnostic: bool = False,
) -> ConceptObservation:
    return ConceptObservation(
        attempt_id=f'attempt-{activity_id}',
        activity_id=activity_id,
        concept_id=concept_id,
        difficulty=difficulty,
        first_submitted_at=completed_at - timedelta(minutes=5),
        submitted_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        question_scores=(Decimal(score) if score is not None else None,),
        diagnostic=diagnostic,
    )


def _diagnostic(
    concept_id: str,
    activity_id: str,
    difficulty: ActivityDifficulty,
    score: str | None,
    completed_at: datetime = DIAGNOSTIC_AT,
) -> ConceptObservation:
    return _observation(
        concept_id, activity_id, difficulty, completed_at, score, diagnostic=True
    )


def _attempt(attempt_id: str, kind: ActivityAttemptKind) -> ActivityAttempt:
    return ActivityAttemptFaker.fake(
        id=attempt_id,
        skill_experience_id=EXPERIENCE_ID,
        kind=kind,
        submitted_at=_at(1),
    )


def _evaluation(
    attempt_id: str,
    completed_at: datetime,
    progress_after: str | None,
    status: ActivityEvaluationStatus = ActivityEvaluationStatus.COMPLETED,
) -> ActivityEvaluation:
    return ActivityEvaluationFaker.fake(
        attempt_id=attempt_id,
        status=status,
        started_at=completed_at,
        completed_at=(
            completed_at if status is ActivityEvaluationStatus.COMPLETED else None
        ),
        progress_after=Decimal(progress_after) if progress_after is not None else None,
    )


def _point(
    occurred_at: datetime,
    result: str,
    *,
    partial: bool,
    baseline: bool = False,
) -> SkillEvolutionPoint:
    return SkillEvolutionPoint(
        occurred_at=occurred_at,
        result=Decimal(result),
        is_partial=partial,
        is_baseline=baseline,
    )


class TestGetSkillEvolutionUseCase:
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(LearningDatabaseRepositories, instance=True)
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.provider = create_autospec(CurriculumContentProvider, instance=True)
        self.subject = GetSkillEvolutionUseCase(self.database, self.provider)
        self.repositories.skill_experiences.find_by_id.return_value = (
            SkillExperienceFaker.fake(
                id=EXPERIENCE_ID,
                goal_id=GOAL_ID,
                skill_id=SKILL_ID,
                status=SkillExperienceStatus.LEARNING,
            )
        )
        self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
            id=GOAL_ID, account_id=ACCOUNT_ID
        )
        self._store()

    def _store(
        self,
        *,
        skill: CurriculumSkillSnapshot | None = None,
        attempts: tuple[ActivityAttempt, ...] = (),
        evaluations: tuple[ActivityEvaluation, ...] = (),
        observations: tuple[ConceptObservation, ...] = (),
    ) -> None:
        self.provider.get_skill_content.return_value = skill or _skill(
            'concept-a', 'concept-b'
        )
        self.repositories.activity_attempts.find_many_by_skill_experience_id.return_value = list(
            attempts
        )

        def evaluations_of(attempt_ids: tuple[str, ...]) -> list[ActivityEvaluation]:
            return [item for item in evaluations if item.attempt_id in attempt_ids]

        self.repositories.activity_evaluations.find_many_by_attempt_ids.side_effect = (
            evaluations_of
        )
        self.repositories.concept_observations.find_many_by_skill_experience_id.return_value = list(
            observations
        )

    def _learning(
        self, *completions: tuple[str, datetime, str]
    ) -> tuple[tuple[ActivityAttempt, ...], tuple[ActivityEvaluation, ...]]:
        return (
            tuple(
                _attempt(name, ActivityAttemptKind.LEARNING)
                for name, _, _ in completions
            ),
            tuple(_evaluation(name, at, after) for name, at, after in completions),
        )

    def test_should_emit_the_base_and_one_point_per_changed_result_in_chronological_order(
        self,
    ) -> None:
        attempts, evaluations = self._learning(
            ('learning-1', _at(5), '48'),
            ('learning-2', _at(6), '48'),
            ('learning-3', _at(8), '55'),
        )
        self._store(
            skill=_skill('concept-a', 'concept-b'),
            attempts=attempts,
            evaluations=evaluations,
            observations=(
                _diagnostic('concept-a', 'diagnostic-1', EASY, '60'),
                _diagnostic('concept-a', 'diagnostic-2', MEDIUM, '40'),
                _diagnostic('concept-b', 'diagnostic-3', EASY, '30'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result == SkillEvolution(
            skill_experience_id=EXPERIENCE_ID,
            points=(
                _point(DIAGNOSTIC_AT, '40', partial=True, baseline=True),
                _point(_at(5), '48', partial=True),
                _point(_at(8), '55', partial=True),
            ),
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_called_once_with(
            ('learning-1', 'learning-2', 'learning-3')
        )

    def test_should_order_the_points_by_completion_when_the_repository_returns_them_unordered(
        self,
    ) -> None:
        attempts, evaluations = self._learning(
            ('learning-3', _at(8), '55'),
            ('learning-1', _at(5), '48'),
            ('learning-2', _at(6), '51'),
        )
        self._store(attempts=attempts, evaluations=evaluations)

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [(point.occurred_at, point.result) for point in result.points] == [
            (_at(5), Decimal('48')),
            (_at(6), Decimal('51')),
            (_at(8), Decimal('55')),
        ]

    @pytest.mark.parametrize(
        'observations',
        [
            (),
            (_diagnostic('concept-a', 'diagnostic-1', EASY, None),),
        ],
        ids=['no observation', 'inconclusive diagnostic'],
    )
    def test_should_have_no_base_point_without_a_numeric_baseline(
        self, observations: tuple[ConceptObservation, ...]
    ) -> None:
        attempts, evaluations = self._learning(
            ('learning-1', _at(5), '48'), ('learning-2', _at(8), '55')
        )
        self._store(
            attempts=attempts, evaluations=evaluations, observations=observations
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (
            _point(_at(5), '48', partial=True),
            _point(_at(8), '55', partial=True),
        )

    def test_should_return_only_the_base_when_the_experience_has_no_learning_evaluation(
        self,
    ) -> None:
        self._store(
            attempts=(_attempt('diagnostic-attempt', ActivityAttemptKind.DIAGNOSTIC),),
            observations=(_diagnostic('concept-a', 'diagnostic-1', EASY, '70'),),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (
            _point(DIAGNOSTIC_AT, '35', partial=True, baseline=True),
        )
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_not_called()

    def test_should_return_no_point_for_an_experience_without_evidence(self) -> None:
        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result == SkillEvolution(skill_experience_id=EXPERIENCE_ID, points=())

    def test_should_date_the_base_at_the_latest_diagnostic_completion(self) -> None:
        self._store(
            observations=(
                _diagnostic('concept-a', 'diagnostic-1', EASY, '50', _at(2)),
                _diagnostic('concept-b', 'diagnostic-2', EASY, '50', _at(3)),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (_point(_at(3), '50', partial=True, baseline=True),)

    def test_should_average_each_difficulty_before_averaging_the_difficulties(
        self,
    ) -> None:
        self._store(
            skill=_skill('concept-a'),
            observations=(
                _diagnostic('concept-a', 'easy-1', EASY, '60'),
                _diagnostic('concept-a', 'easy-2', EASY, '80'),
                _diagnostic('concept-a', 'hard-1', HARD, '20'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [point.result for point in result.points] == [Decimal('45')]

    def test_should_keep_only_the_latest_valid_diagnostic_observation_of_each_activity(
        self,
    ) -> None:
        self._store(
            skill=_skill('concept-a'),
            observations=(
                _diagnostic('concept-a', 'easy-1', EASY, '20', _at(2)),
                _diagnostic('concept-a', 'easy-1', EASY, '80', _at(3)),
                _diagnostic('concept-a', 'easy-1', EASY, None, _at(4)),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (_point(_at(4), '80', partial=True, baseline=True),)

    def test_should_ignore_learning_observations_when_building_the_base(self) -> None:
        self._store(
            skill=_skill('concept-a'),
            observations=(
                _diagnostic('concept-a', 'easy-1', EASY, '50'),
                _observation('concept-a', 'medium-1', MEDIUM, _at(5), '90'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [point.result for point in result.points] == [Decimal('50')]

    def test_should_keep_the_diagnostic_value_when_the_same_activity_is_observed_again_in_learning(
        self,
    ) -> None:
        self._store(
            skill=_skill('concept-a'),
            observations=(
                _diagnostic('concept-a', 'easy-1', EASY, '40'),
                _observation('concept-a', 'easy-1', EASY, _at(5), '90'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [point.result for point in result.points] == [Decimal('40')]
        assert result.points[0].is_baseline is True

    def test_should_compare_the_base_with_the_persisted_two_decimal_result(
        self,
    ) -> None:
        attempts, evaluations = self._learning(
            ('learning-1', _at(5), '33.33'), ('learning-2', _at(6), '40.00')
        )
        self._store(
            skill=_skill('concept-a', 'concept-b', 'concept-c'),
            attempts=attempts,
            evaluations=evaluations,
            observations=(
                _diagnostic('concept-a', 'easy-1', EASY, '100'),
                _diagnostic('concept-b', 'easy-2', EASY, '0'),
                _diagnostic('concept-c', 'easy-3', EASY, '0'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (
            _point(DIAGNOSTIC_AT, '33.33', partial=True, baseline=True),
            _point(_at(6), '40.00', partial=True),
        )

    def test_should_mark_every_point_partial_until_coverage_completes_at_the_last_evaluation(
        self,
    ) -> None:
        attempts, evaluations = self._learning(
            ('learning-1', _at(5), '55'),
            ('learning-2', _at(6), '60'),
            ('learning-3', _at(8), '70'),
        )
        self._store(
            attempts=attempts,
            evaluations=evaluations,
            observations=(
                _diagnostic('concept-a', 'diagnostic-1', EASY, '50'),
                _diagnostic('concept-b', 'diagnostic-2', EASY, '50'),
                _observation('concept-a', 'medium-a', MEDIUM, _at(5), '60'),
                _observation('concept-b', 'medium-b', MEDIUM, _at(5), '60'),
                _observation('concept-a', 'hard-a', HARD, _at(6), '70'),
                _observation('concept-b', 'hard-b', HARD, _at(8), '80'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (
            _point(DIAGNOSTIC_AT, '50', partial=True, baseline=True),
            _point(_at(5), '55', partial=True),
            _point(_at(6), '60', partial=True),
            _point(_at(8), '70', partial=False),
        )

    def test_should_not_count_inconclusive_observations_as_coverage(self) -> None:
        attempts, evaluations = self._learning(('learning-1', _at(5), '55'))
        self._store(
            skill=_skill('concept-a'),
            attempts=attempts,
            evaluations=evaluations,
            observations=(
                _diagnostic('concept-a', 'easy-1', EASY, '50'),
                _observation('concept-a', 'medium-1', MEDIUM, _at(5), '60'),
                _observation('concept-a', 'hard-1', HARD, _at(5), None),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [point.is_partial for point in result.points] == [True, True]

    def test_should_end_a_completed_experience_series_at_the_completing_evaluation(
        self,
    ) -> None:
        learning_attempts, learning_evaluations = self._learning(
            ('learning-1', _at(5), '60'), ('learning-2', _at(8), '90')
        )
        review_attempt = _attempt('review-1', ActivityAttemptKind.REVIEW)
        self._store(
            attempts=(*learning_attempts, review_attempt),
            evaluations=(*learning_evaluations, _evaluation('review-1', _at(20), '99')),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [(point.occurred_at, point.result) for point in result.points] == [
            (_at(5), Decimal('60')),
            (_at(8), Decimal('90')),
        ]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_called_once_with(
            ('learning-1', 'learning-2')
        )

    def test_should_never_read_diagnostic_attempt_evaluations(self) -> None:
        learning_attempts, learning_evaluations = self._learning(
            ('learning-1', _at(5), '60')
        )
        self._store(
            attempts=(
                _attempt('diagnostic-1', ActivityAttemptKind.DIAGNOSTIC),
                *learning_attempts,
            ),
            evaluations=(
                _evaluation('diagnostic-1', DIAGNOSTIC_AT, '10'),
                *learning_evaluations,
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert [point.result for point in result.points] == [Decimal('60')]
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_called_once_with(
            ('learning-1',)
        )

    def test_should_ignore_pending_failed_closed_without_grade_and_effectless_evaluations(
        self,
    ) -> None:
        attempts = tuple(
            _attempt(name, ActivityAttemptKind.LEARNING)
            for name in ('pending', 'failed', 'closed', 'effectless', 'official')
        )
        self._store(
            attempts=attempts,
            evaluations=(
                _evaluation('pending', _at(4), '77', ActivityEvaluationStatus.PENDING),
                _evaluation('failed', _at(5), '88', ActivityEvaluationStatus.FAILED),
                _evaluation(
                    'closed',
                    _at(5),
                    '66',
                    ActivityEvaluationStatus.CLOSED_WITHOUT_GRADE,
                ),
                _evaluation('effectless', _at(6), None),
                _evaluation('official', _at(7), '50'),
            ),
        )

        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.points == (_point(_at(7), '50', partial=True),)

    def test_should_report_the_experience_identifier_of_the_series(self) -> None:
        result = self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        assert result.skill_experience_id == EXPERIENCE_ID
        self.repositories.skill_experiences.find_by_id.assert_called_once_with(
            EXPERIENCE_ID
        )

    @pytest.mark.parametrize('scenario', ['unknown', 'orphan', 'foreign'])
    def test_should_raise_not_found_without_reading_the_series_for_an_unknown_or_foreign_experience(
        self, scenario: str
    ) -> None:
        if scenario == 'unknown':
            self.repositories.skill_experiences.find_by_id.return_value = None
        elif scenario == 'orphan':
            self.repositories.goals.find_by_id.return_value = None
        else:
            self.repositories.goals.find_by_id.return_value = GoalFaker.fake(
                id=GOAL_ID, account_id='account-2'
            )

        with pytest.raises(SkillExperienceNotFoundError):
            self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        self.repositories.activity_attempts.find_many_by_skill_experience_id.assert_not_called()
        self.repositories.activity_evaluations.find_many_by_attempt_ids.assert_not_called()
        self.repositories.concept_observations.find_many_by_skill_experience_id.assert_not_called()
        self.provider.get_skill_content.assert_not_called()

    def test_should_raise_not_found_when_the_skill_is_missing_from_the_curriculum(
        self,
    ) -> None:
        self.provider.get_skill_content.return_value = None

        with pytest.raises(SkillExperienceNotFoundError):
            self.subject.execute(ACCOUNT_ID, EXPERIENCE_ID)

        self.provider.get_skill_content.assert_called_once_with(SKILL_ID)
