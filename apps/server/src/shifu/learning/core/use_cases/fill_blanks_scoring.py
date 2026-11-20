from decimal import ROUND_HALF_UP, Decimal

from shifu.learning.core.domain.structures import (
    FillBlanksAnswer,
    FillBlanksEvaluationResult,
    FillBlanksPlacement,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import CurriculumFillBlanksQuestionSnapshot


class FillBlanksScoring:
    _FULL_SCORE = Decimal(100)
    _CENTS = Decimal('0.01')

    @staticmethod
    def normalize(
        question: CurriculumFillBlanksQuestionSnapshot, answer: FillBlanksAnswer
    ) -> FillBlanksAnswer:
        """Require every blank filled once with distinct, known bank occurrences."""
        by_blank = {placement.blank_key: placement for placement in answer.placements}
        word_keys = tuple(placement.word_key for placement in answer.placements)
        if (
            answer.question_key != question.key
            or len(by_blank) != len(answer.placements)
            or set(by_blank) != {blank.key for blank in question.blanks}
            or len(set(word_keys)) != len(word_keys)
            or not set(word_keys) <= {word.key for word in question.bank}
        ):
            raise ValidationError

        return FillBlanksAnswer(
            question_key=question.key,
            placements=tuple(
                FillBlanksPlacement(
                    blank_key=blank.key, word_key=by_blank[blank.key].word_key
                )
                for blank in question.blanks
            ),
        )

    @staticmethod
    def score(
        question: CurriculumFillBlanksQuestionSnapshot, answer: FillBlanksAnswer
    ) -> FillBlanksEvaluationResult:
        """Equal credit per blank; occurrences of the same word are equivalent."""
        normalized = FillBlanksScoring.normalize(question, answer)
        word_by_key = {word.key: word.word for word in question.bank}
        placed = {
            item.blank_key: word_by_key[item.word_key] for item in normalized.placements
        }
        correct_keys = tuple(
            blank.key
            for blank in question.blanks
            if placed[blank.key] in blank.accepted_words
        )
        score = FillBlanksScoring._percentage(len(correct_keys), len(question.blanks))
        if score == FillBlanksScoring._FULL_SCORE:
            explanation = question.correct_explanation
        elif score == 0 or question.partial_explanation is None:
            explanation = question.incorrect_explanation
        else:
            explanation = question.partial_explanation
        return FillBlanksEvaluationResult(
            question_key=question.key,
            score=score,
            is_correct=score == FillBlanksScoring._FULL_SCORE,
            correct_blank_keys=correct_keys,
            blank_count=len(question.blanks),
            explanation=explanation,
        )

    @staticmethod
    def concept_observations(
        question: CurriculumFillBlanksQuestionSnapshot,
        result: FillBlanksEvaluationResult,
    ) -> dict[str, Decimal]:
        """Evidence per Concept: share of its mapped blanks that are correct."""
        correct = set(result.correct_blank_keys)
        return {
            criterion.concept_id: FillBlanksScoring._percentage(
                len(correct.intersection(criterion.blank_keys)),
                len(criterion.blank_keys),
            )
            for criterion in question.concept_criteria
        }

    @staticmethod
    def _percentage(part: int, total: int) -> Decimal:
        return (FillBlanksScoring._FULL_SCORE * part / total).quantize(
            FillBlanksScoring._CENTS, rounding=ROUND_HALF_UP
        )
