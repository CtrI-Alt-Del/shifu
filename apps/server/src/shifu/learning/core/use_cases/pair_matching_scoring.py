from decimal import Decimal

from shifu.learning.core.domain.structures import (
    PairMatchingAnswer,
    PairMatchingEvaluationResult,
)
from shifu.shared.core.domain.errors import ValidationError
from shifu.shared.core.domain.structures import CurriculumPairMatchingQuestionSnapshot


class PairMatchingScoring:
    @staticmethod
    def validate(
        question: CurriculumPairMatchingQuestionSnapshot,
        answer: PairMatchingAnswer,
    ) -> None:
        word_keys = {item.key for item in question.words}
        translation_keys = {item.key for item in question.translations}
        if (
            answer.question_key != question.key
            or len(answer.pairs) != len(question.words)
            or {pair.word_key for pair in answer.pairs} != word_keys
            or {pair.translation_key for pair in answer.pairs} != translation_keys
        ):
            raise ValidationError

    @staticmethod
    def evaluate(
        question: CurriculumPairMatchingQuestionSnapshot,
        answer: PairMatchingAnswer,
    ) -> PairMatchingEvaluationResult:
        PairMatchingScoring.validate(question, answer)
        expected = {
            pair.word_key: pair.translation_key for pair in question.correct_pairs
        }
        total = len(question.words)
        correct = sum(
            expected.get(pair.word_key) == pair.translation_key for pair in answer.pairs
        )
        if correct == total:
            outcome = 'full'
            explanation = question.full_explanation
        elif correct == 0:
            outcome = 'incorrect'
            explanation = question.incorrect_explanation
        else:
            outcome = 'partial'
            explanation = question.partial_explanation
        return PairMatchingEvaluationResult(
            question_key=question.key,
            score=Decimal(100) * correct / Decimal(total),
            correct_pair_count=correct,
            total_pair_count=total,
            outcome=outcome,
            explanation=explanation,
        )
