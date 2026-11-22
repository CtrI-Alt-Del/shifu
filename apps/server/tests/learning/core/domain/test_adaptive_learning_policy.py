from datetime import UTC, datetime, timedelta
from decimal import Decimal

from shifu.learning.core.domain.adaptive_learning_policy import AdaptiveLearningPolicy
from shifu.learning.core.domain.enums import ActivityDifficulty
from shifu.learning.core.domain.structures import ConceptObservation

START = datetime(2026, 9, 20, 12, tzinfo=UTC)


def observation(
    *,
    concept_id: str = 'concept-1',
    activity_id: str = 'activity-easy',
    difficulty: ActivityDifficulty = ActivityDifficulty.EASY,
    score: Decimal | None = Decimal(100),
    after: timedelta = timedelta(),
    diagnostic: bool = True,
) -> ConceptObservation:
    completed_at = START + after
    return ConceptObservation(
        attempt_id=f'{activity_id}-{concept_id}-{after.total_seconds()}',
        activity_id=activity_id,
        concept_id=concept_id,
        difficulty=difficulty,
        first_submitted_at=completed_at,
        submitted_at=completed_at,
        completed_at=completed_at,
        question_scores=(score,),
        diagnostic=diagnostic,
    )


class TestAdaptiveLearningPolicyDiagnosticObservedDifficulties:
    def test_should_return_nothing_without_observations(self) -> None:
        assert (
            AdaptiveLearningPolicy.diagnostic_observed_difficulties('concept-1', ())
            == frozenset()
        )

    def test_should_collect_the_difficulties_of_valid_diagnostic_observations(
        self,
    ) -> None:
        observations = (
            observation(activity_id='a-easy', difficulty=ActivityDifficulty.EASY),
            observation(activity_id='a-hard', difficulty=ActivityDifficulty.HARD),
        )

        result = AdaptiveLearningPolicy.diagnostic_observed_difficulties(
            'concept-1', observations
        )

        assert result == frozenset({ActivityDifficulty.EASY, ActivityDifficulty.HARD})

    def test_should_ignore_observations_of_other_concepts(self) -> None:
        observations = (
            observation(concept_id='concept-2', difficulty=ActivityDifficulty.MEDIUM),
        )

        assert (
            AdaptiveLearningPolicy.diagnostic_observed_difficulties(
                'concept-1', observations
            )
            == frozenset()
        )

    def test_should_ignore_learning_observations(self) -> None:
        observations = (
            observation(difficulty=ActivityDifficulty.HARD, diagnostic=False),
        )

        assert (
            AdaptiveLearningPolicy.diagnostic_observed_difficulties(
                'concept-1', observations
            )
            == frozenset()
        )

    def test_should_ignore_inconclusive_diagnostic_observations(self) -> None:
        observations = (observation(score=None),)

        assert (
            AdaptiveLearningPolicy.diagnostic_observed_difficulties(
                'concept-1', observations
            )
            == frozenset()
        )

    def test_should_keep_the_latest_valid_observation_when_a_later_one_is_inconclusive(
        self,
    ) -> None:
        observations = (
            observation(difficulty=ActivityDifficulty.MEDIUM),
            observation(
                difficulty=ActivityDifficulty.MEDIUM,
                score=None,
                after=timedelta(hours=1),
            ),
        )

        result = AdaptiveLearningPolicy.diagnostic_observed_difficulties(
            'concept-1', observations
        )

        assert result == frozenset({ActivityDifficulty.MEDIUM})

    def test_should_drop_an_activity_whose_latest_valid_observation_is_not_diagnostic(
        self,
    ) -> None:
        observations = (
            observation(difficulty=ActivityDifficulty.HARD),
            observation(
                difficulty=ActivityDifficulty.HARD,
                diagnostic=False,
                after=timedelta(hours=1),
            ),
        )

        assert (
            AdaptiveLearningPolicy.diagnostic_observed_difficulties(
                'concept-1', observations
            )
            == frozenset()
        )

    def test_should_not_depend_on_the_input_order(self) -> None:
        older = observation(difficulty=ActivityDifficulty.EASY)
        newer = observation(
            difficulty=ActivityDifficulty.EASY,
            diagnostic=False,
            after=timedelta(hours=1),
        )

        assert AdaptiveLearningPolicy.diagnostic_observed_difficulties(
            'concept-1', (newer, older)
        ) == AdaptiveLearningPolicy.diagnostic_observed_difficulties(
            'concept-1', (older, newer)
        )
