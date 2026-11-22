from decimal import Decimal

from shifu.learning.core.domain.errors import EvaluationUnavailableError
from shifu.learning.core.domain.structures import (
    PracticalConceptEvidence,
    PracticalCriterionResult,
    PracticalPreparationResult,
)
from shifu.shared.core.domain.structures import (
    CurriculumPracticalPreparationInsufficiencyRuleSnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
    PracticeCriterionDecision,
    PracticePhotoDecisions,
)


class PracticalPreparationScoring:
    """Validate assessor decisions and decide grade, evidence or closure without grade.

    The assessor only observes. Learning checks completeness, allowed levels and
    rubric comments, applies the Curriculum insufficiency rules, and computes the
    weighted grade and the Concept evidence separately.
    """

    @staticmethod
    def evaluate(
        question: CurriculumPracticalPreparationQuestionSnapshot,
        decisions: PracticePhotoDecisions,
    ) -> PracticalPreparationResult:
        criteria = {criterion.key: criterion for criterion in question.criteria}
        decided = {item.key: item for item in decisions.criteria}
        sufficient = {item.record_key: item.sufficient for item in decisions.records}
        if set(decided) != set(criteria) or set(sufficient) != {
            record.key for record in question.records
        }:
            raise EvaluationUnavailableError

        results: list[PracticalCriterionResult] = []
        for criterion in question.criteria:
            decision = decided[criterion.key]
            if decision.level is None:
                results.append(
                    PracticalCriterionResult(
                        criterion_key=criterion.key, level=None, comment_key=None
                    )
                )
                continue

            level = next(
                (item for item in criterion.levels if item.score == decision.level),
                None,
            )
            if level is None or level.comment_key != decision.comment_key:
                raise EvaluationUnavailableError
            results.append(
                PracticalCriterionResult(
                    criterion_key=criterion.key,
                    level=level.score,
                    comment_key=level.comment_key,
                )
            )

        insufficient = tuple(
            rule
            for rule in question.insufficiency_rules
            if PracticalPreparationScoring._is_insufficient(rule, decided, sufficient)
        )
        if insufficient:
            return PracticalPreparationResult(
                question_key=question.key,
                score=None,
                closed_without_grade=True,
                criterion_results=tuple(results),
                unassessable_record_keys=tuple(
                    dict.fromkeys(rule.record_key for rule in insufficient)
                ),
                concept_evidence=PracticalPreparationScoring._evidence(question, None),
            )

        # Any other inconclusive observation is a recoverable failure, never a grade.
        weighted = Decimal(0)
        for item in results:
            if item.level is None:
                raise EvaluationUnavailableError
            weighted += criteria[item.criterion_key].weight * Decimal(item.level)
        score = weighted / Decimal(100)
        return PracticalPreparationResult(
            question_key=question.key,
            score=score,
            closed_without_grade=False,
            criterion_results=tuple(results),
            unassessable_record_keys=(),
            concept_evidence=PracticalPreparationScoring._evidence(question, score),
        )

    @staticmethod
    def _is_insufficient(
        rule: CurriculumPracticalPreparationInsufficiencyRuleSnapshot,
        decided: dict[str, PracticeCriterionDecision],
        sufficient: dict[str, bool],
    ) -> bool:
        """Every named criterion is inconclusive and the assessor also reports the
        record as not showing enough."""
        return not sufficient[rule.record_key] and all(
            decided[key].level is None for key in rule.criterion_keys
        )

    @staticmethod
    def _evidence(
        question: CurriculumPracticalPreparationQuestionSnapshot,
        score: Decimal | None,
    ) -> tuple[PracticalConceptEvidence, ...]:
        """Evidence runs between the Concept's incorrect and correct anchors, so a
        high grade never exceeds the evidence the Curriculum allows for that Concept."""
        evidence: list[PracticalConceptEvidence] = []
        for criterion in question.concept_criteria:
            low = criterion.incorrect_score
            high = criterion.correct_score
            value = (
                low + (high - low) * score / Decimal(100)
                if score is not None and low is not None and high is not None
                else None
            )
            evidence.append(
                PracticalConceptEvidence(concept_id=criterion.concept_id, value=value)
            )
        return tuple(evidence)
