from datetime import UTC, datetime, timedelta
from decimal import Decimal

from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures.adaptive_activity import AdaptiveActivity
from shifu.learning.core.domain.structures.adaptive_competency_memory import (
    AdaptiveCompetencyMemory,
)
from shifu.learning.core.domain.structures.adaptive_concept import AdaptiveConcept
from shifu.learning.core.domain.structures.adaptive_material import AdaptiveMaterial
from shifu.learning.core.domain.structures.adaptive_policy_result import (
    AdaptivePolicyResult,
)
from shifu.learning.core.domain.structures.concept_observation import (
    ConceptObservation,
)

_START = datetime(2026, 1, 1, tzinfo=UTC)


def _observation(
    activity_id: str,
    difficulty: ActivityDifficulty,
    score: Decimal | None,
    day: int,
    *,
    concept_id: str = 'concept',
    diagnostic: bool = False,
    first_day: int | None = None,
    attempt_id: str | None = None,
) -> ConceptObservation:
    when = _START + timedelta(days=day)
    return ConceptObservation(
        attempt_id=attempt_id or f'{activity_id}-{day}',
        activity_id=activity_id,
        concept_id=concept_id,
        difficulty=difficulty,
        first_submitted_at=_START
        + timedelta(days=first_day if first_day is not None else day),
        submitted_at=when,
        completed_at=when,
        question_scores=(score,),
        diagnostic=diagnostic,
    )


def _activity(
    activity_id: str,
    difficulty: ActivityDifficulty = ActivityDifficulty.EASY,
    *,
    concept_ids: tuple[str, ...] = ('concept',),
    required_concept_ids: tuple[str, ...] = (),
    position: int = 1,
) -> AdaptiveActivity:
    return AdaptiveActivity(
        id=activity_id,
        competency_id='competency',
        position=position,
        difficulty=difficulty,
        concept_ids=concept_ids,
        required_concept_ids=required_concept_ids,
        question_count_by_concept=tuple((concept_id, 1) for concept_id in concept_ids),
    )


def _evaluate(
    observations: tuple[ConceptObservation, ...] = (),
    *,
    concepts: tuple[AdaptiveConcept, ...] | None = None,
    activities: tuple[AdaptiveActivity, ...] = (),
    materials: tuple[AdaptiveMaterial, ...] = (),
    memories: tuple[AdaptiveCompetencyMemory, ...] = (),
    previous_target_id: str | None = None,
) -> tuple[Decimal | None, AdaptivePolicyResult]:
    result = AdaptiveLearningPolicy().evaluate(
        concepts=concepts
        or (AdaptiveConcept(id='concept', competency_id='competency', position=1),),
        competency_ids=('competency',),
        activities=activities,
        materials=materials,
        observations=observations,
        memories=memories,
        previous_target_id=previous_target_id,
        now=_START + timedelta(days=100),
    )
    return result.concept_states[0].progress, result


class TestAdaptiveLearningPolicy:
    def test_trajectory_requires_new_activity_evidence_beyond_retries(self) -> None:
        diagnostic = (
            _observation(
                'd-easy', ActivityDifficulty.EASY, Decimal('50'), 0, diagnostic=True
            ),
            _observation(
                'd-medium', ActivityDifficulty.MEDIUM, Decimal('50'), 1, diagnostic=True
            ),
            _observation(
                'd-hard', ActivityDifficulty.HARD, Decimal('50'), 2, diagnostic=True
            ),
        )
        first = _observation('practice', ActivityDifficulty.EASY, Decimal('100'), 3)
        _, after_first = _evaluate((*diagnostic, first))
        assert after_first.concept_states[0].initial_progress == Decimal('50')
        assert after_first.concept_states[0].progress == Decimal('65.0')

        retry = _observation(
            'practice', ActivityDifficulty.EASY, Decimal('100'), 4, first_day=3
        )
        _, after_retry = _evaluate((*diagnostic, first, retry))
        assert after_retry.concept_states[0].progress == Decimal('65.0')
        assert after_retry.concept_states[0].current_contributions == (
            ('practice', Decimal('100')),
        )

        new_activity = _observation(
            'transfer', ActivityDifficulty.MEDIUM, Decimal('0'), 5
        )
        _, after_transfer = _evaluate((*diagnostic, first, retry, new_activity))
        assert after_transfer.concept_states[0].progress == Decimal('45.50')
        assert after_transfer.concept_states[0].current_contributions == (
            ('practice', Decimal('100')),
            ('transfer', Decimal('0')),
        )
        assert (
            after_transfer.competency_states[0].status
            is not CompetencyProgressStatus.MASTERED
        )

    def test_should_average_all_valid_questions_once_per_activity_and_concept(
        self,
    ) -> None:
        observation = ConceptObservation(
            attempt_id='a-1',
            activity_id='a',
            concept_id='concept',
            difficulty=ActivityDifficulty.EASY,
            first_submitted_at=_START,
            submitted_at=_START,
            completed_at=_START,
            question_scores=(Decimal('0'), Decimal('100')),
        )
        _, result = _evaluate((observation,))
        assert observation.value == Decimal('50')
        assert result.concept_states[0].progress == Decimal('50')
        assert result.concept_states[0].distinct_activity_ids == frozenset({'a'})

    def test_should_preserve_unknown_and_distinguish_valid_zero_from_inconclusive(
        self,
    ) -> None:
        _, unknown = _evaluate()
        assert unknown.concept_states[0].progress is None
        assert unknown.concept_states[0].observed_difficulties == frozenset()

        _, inconclusive = _evaluate(
            (_observation('a', ActivityDifficulty.EASY, None, 1),)
        )
        assert inconclusive.concept_states[0].progress is None
        assert inconclusive.concept_states[0].evidence_verification

        _, zero = _evaluate(
            (_observation('a', ActivityDifficulty.EASY, Decimal('0'), 1),)
        )
        assert zero.concept_states[0].progress == Decimal('0')
        assert not zero.concept_states[0].evidence_verification

    def test_should_keep_diagnostic_baseline_fixed_and_replace_worse_retake_in_original_position(
        self,
    ) -> None:
        observations = (
            _observation(
                'd-easy', ActivityDifficulty.EASY, Decimal('0'), 0, diagnostic=True
            ),
            _observation(
                'd-medium',
                ActivityDifficulty.MEDIUM,
                Decimal('100'),
                1,
                diagnostic=True,
            ),
            _observation('a', ActivityDifficulty.EASY, Decimal('0'), 2),
            _observation('b', ActivityDifficulty.MEDIUM, Decimal('100'), 3),
        )
        _, first = _evaluate(observations)
        assert first.concept_states[0].initial_progress == Decimal('50')
        assert first.concept_states[0].progress == Decimal('54.5')

        _, improved = _evaluate(
            (
                *observations,
                _observation(
                    'a', ActivityDifficulty.EASY, Decimal('10'), 4, first_day=2
                ),
            )
        )
        assert improved.concept_states[0].progress == Decimal('56.6')
        assert len(improved.concept_states[0].distinct_activity_ids) == 4

        _, worse = _evaluate(
            (
                *observations,
                _observation(
                    'a', ActivityDifficulty.EASY, Decimal('0'), 4, first_day=2
                ),
                _observation(
                    'b', ActivityDifficulty.MEDIUM, Decimal('0'), 5, first_day=3
                ),
            )
        )
        assert worse.concept_states[0].progress == Decimal('24.5')

    def test_should_preserve_valid_contribution_when_retake_is_inconclusive(
        self,
    ) -> None:
        first = _observation('a', ActivityDifficulty.EASY, Decimal('70'), 1)
        partial = ConceptObservation(
            attempt_id='a-2',
            activity_id='a',
            concept_id='concept',
            difficulty=ActivityDifficulty.EASY,
            first_submitted_at=first.first_submitted_at,
            submitted_at=_START + timedelta(days=2),
            completed_at=_START + timedelta(days=2),
            question_scores=(Decimal('100'), None),
        )
        _, result = _evaluate((first, partial))
        assert result.concept_states[0].progress == Decimal('70')
        assert result.concept_states[0].current_contributions == (('a', Decimal('70')),)
        assert result.concept_states[0].evidence_verification

    def test_should_require_complete_coverage_diversity_and_hard_evidence_for_mastery(
        self,
    ) -> None:
        observations = (
            _observation(
                'easy', ActivityDifficulty.EASY, Decimal('100'), 1, diagnostic=True
            ),
            _observation(
                'medium', ActivityDifficulty.MEDIUM, Decimal('100'), 2, diagnostic=True
            ),
            _observation(
                'hard', ActivityDifficulty.HARD, Decimal('80'), 3, diagnostic=True
            ),
        )
        _, result = _evaluate(observations)
        assert result.competency_states[0].status is CompetencyProgressStatus.MASTERED
        assert result.competency_states[0].progress == Decimal(
            '93.33333333333333333333333333'
        )
        assert (
            result.concept_states[0].progress
            == result.concept_states[0].initial_progress
        )
        assert result.focus_competency_id is None
        assert result.recommendation is None

        _, no_hard_confirmation = _evaluate(
            (
                *observations[:2],
                _observation(
                    'hard', ActivityDifficulty.HARD, Decimal('79'), 3, diagnostic=True
                ),
            )
        )
        assert (
            no_hard_confirmation.competency_states[0].status
            is not CompetencyProgressStatus.MASTERED
        )

    def test_should_compare_unrounded_observation_at_mastery_boundary(self) -> None:
        just_below = Decimal('84.9999999999996')
        observations = tuple(
            _observation(
                f'd-{difficulty.value}', difficulty, just_below, index, diagnostic=True
            )
            for index, difficulty in enumerate(ActivityDifficulty, 1)
        )
        _, result = _evaluate(observations)
        state = result.competency_states[0]
        assert state.progress == just_below
        assert state.coverage_complete
        assert state.status is not CompetencyProgressStatus.MASTERED

    def test_should_offer_optional_material_with_easy_activity_on_first_contact(
        self,
    ) -> None:
        _, result = _evaluate(
            activities=(_activity('easy'),),
            materials=(
                AdaptiveMaterial(id='intro', position=1, concept_ids=('concept',)),
            ),
        )
        assert result.recommendation is not None
        assert result.recommendation.activity_id == 'easy'
        assert result.recommendation.material_id == 'intro'
        assert result.recommendation.material_is_optional
        assert result.recommendation.reason == 'coverage'

    def test_should_follow_weak_concept_and_activity_prerequisites_without_indirect_progress(
        self,
    ) -> None:
        concepts = (
            AdaptiveConcept(id='base', competency_id='competency', position=1),
            AdaptiveConcept(
                id='target',
                competency_id='competency',
                position=2,
                prerequisite_ids=('base',),
            ),
        )
        _, result = _evaluate(
            concepts=concepts,
            activities=(
                _activity('base-easy', concept_ids=('base',)),
                _activity(
                    'target-easy',
                    concept_ids=('target',),
                    required_concept_ids=('base',),
                    position=2,
                ),
            ),
        )
        assert result.recommendation is not None
        assert result.recommendation.target_concept_id == 'base'
        assert result.concept_states[1].progress is None

    def test_should_count_diagnostic_diversity_for_prerequisite_readiness(self) -> None:
        concepts = (
            AdaptiveConcept(id='base', competency_id='competency', position=1),
            AdaptiveConcept(
                id='target',
                competency_id='competency',
                position=2,
                prerequisite_ids=('base',),
            ),
        )
        observations = (
            _observation(
                'base-easy',
                ActivityDifficulty.EASY,
                Decimal('70'),
                1,
                concept_id='base',
                diagnostic=True,
            ),
            _observation(
                'base-medium',
                ActivityDifficulty.MEDIUM,
                Decimal('70'),
                2,
                concept_id='base',
                diagnostic=True,
            ),
            _observation(
                'base-hard',
                ActivityDifficulty.HARD,
                Decimal('80'),
                3,
                concept_id='base',
                diagnostic=True,
            ),
        )
        _, result = _evaluate(
            observations,
            concepts=concepts,
            activities=(
                _activity(
                    'target-easy',
                    concept_ids=('target',),
                    required_concept_ids=('base',),
                ),
            ),
        )
        assert result.concept_states[0].progress == Decimal(
            '73.33333333333333333333333333'
        )
        assert len(result.concept_states[0].distinct_activity_ids) == 3
        assert result.recommendation is not None
        assert result.recommendation.target_concept_id == 'target'
        assert result.recommendation.activity_id == 'target-easy'

    def test_should_report_gap_when_no_evaluable_activity_exists(self) -> None:
        _, result = _evaluate()
        assert result.recommendation is not None
        assert result.recommendation.activity_id is None
        assert result.recommendation.gap == 'curriculum_or_assessment_unavailable'

    def test_should_not_retain_previous_equal_priority_target_without_viable_action(
        self,
    ) -> None:
        concepts = (
            AdaptiveConcept(id='viable', competency_id='competency', position=1),
            AdaptiveConcept(id='unusable', competency_id='competency', position=2),
        )
        _, result = _evaluate(
            concepts=concepts,
            activities=(_activity('viable-easy', concept_ids=('viable',)),),
            previous_target_id='unusable',
        )
        assert result.recommendation is not None
        assert result.recommendation.target_concept_id == 'viable'
        assert result.recommendation.activity_id == 'viable-easy'

    def test_should_redirect_when_only_activity_requires_weak_foundation(self) -> None:
        concepts = (
            AdaptiveConcept(id='base', competency_id='competency', position=1),
            AdaptiveConcept(id='target', competency_id='competency', position=2),
        )
        observations = (
            _observation(
                'target-test', ActivityDifficulty.EASY, None, 1, concept_id='target'
            ),
        )
        _, result = _evaluate(
            observations,
            concepts=concepts,
            activities=(
                _activity('base-easy', concept_ids=('base',)),
                _activity(
                    'target-easy',
                    concept_ids=('target',),
                    required_concept_ids=('base',),
                ),
            ),
        )
        assert result.recommendation is not None
        assert result.recommendation.original_target_concept_id == 'target'
        assert result.recommendation.target_concept_id == 'base'
        assert result.recommendation.activity_id == 'base-easy'

    def test_should_report_assessment_unavailable_after_two_distinct_inconclusions(
        self,
    ) -> None:
        _, result = _evaluate(
            (
                _observation('a', ActivityDifficulty.EASY, None, 1),
                _observation('b', ActivityDifficulty.EASY, None, 2),
            ),
            activities=(_activity('c'),),
        )
        assert result.recommendation is not None
        assert result.recommendation.gap == 'assessment_unavailable'

    def test_should_confirm_regression_only_after_distinct_relevant_activities(
        self,
    ) -> None:
        diagnostic = (
            _observation(
                'd-easy', ActivityDifficulty.EASY, Decimal('100'), 0, diagnostic=True
            ),
            _observation(
                'd-medium',
                ActivityDifficulty.MEDIUM,
                Decimal('100'),
                1,
                diagnostic=True,
            ),
            _observation(
                'd-hard', ActivityDifficulty.HARD, Decimal('100'), 2, diagnostic=True
            ),
        )
        memory = (
            AdaptiveCompetencyMemory(
                competency_id='competency',
                mastered_at=_START + timedelta(days=3),
                content_released=True,
            ),
        )
        first = _observation('a', ActivityDifficulty.EASY, Decimal('0'), 4)
        _, pending = _evaluate((*diagnostic, first), memories=memory)
        assert pending.competency_states[0].status is CompetencyProgressStatus.MASTERED
        assert pending.competency_states[0].verification_cause == 'mean'

        _, repeat = _evaluate(
            (
                *diagnostic,
                first,
                _observation(
                    'a', ActivityDifficulty.EASY, Decimal('0'), 5, first_day=4
                ),
            ),
            memories=memory,
        )
        assert repeat.competency_states[0].status is CompetencyProgressStatus.MASTERED

        _, confirmed = _evaluate(
            (
                *diagnostic,
                first,
                _observation('b', ActivityDifficulty.MEDIUM, Decimal('0'), 5),
            ),
            memories=memory,
        )
        assert (
            confirmed.competency_states[0].status
            is not CompetencyProgressStatus.MASTERED
        )
        assert confirmed.competency_states[0].mastered_at is None
