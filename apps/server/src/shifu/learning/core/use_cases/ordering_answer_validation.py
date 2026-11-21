from hashlib import sha256
from itertools import permutations
from decimal import Decimal

from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.domain.structures import VerifiedOrdering
from shifu.shared.core.domain.structures import CurriculumOrderingQuestionSnapshot
from shifu.shared.core.domain.errors import ValidationError


class OrderingAnswerValidation:
    @staticmethod
    def validate(
        question: CurriculumOrderingQuestionSnapshot,
        ordered_step_keys: tuple[str, ...],
    ) -> None:
        expected = {step.key for step in question.steps}
        if (
            len(ordered_step_keys) != len(question.steps)
            or len(ordered_step_keys) != len(set(ordered_step_keys))
            or set(ordered_step_keys) != expected
        ):
            raise ValidationError

    @staticmethod
    def verify(
        question: CurriculumOrderingQuestionSnapshot,
        ordered_step_keys: tuple[str, ...],
    ) -> VerifiedOrdering:
        OrderingAnswerValidation.validate(question, ordered_step_keys)
        correct = ordered_step_keys in question.accepted_orders
        return VerifiedOrdering(
            question_key=question.key,
            ordered_step_keys=ordered_step_keys,
            score=Decimal(100 if correct else 0),
            is_correct=correct,
            explanation=(
                question.correct_explanation
                if correct
                else question.incorrect_explanation
            ),
        )

    @staticmethod
    def initial_order(
        question: CurriculumOrderingQuestionSnapshot,
        revision: str,
    ) -> tuple[str, ...]:
        seed = sha256(f'{revision}:{question.key}'.encode()).digest()
        candidate = [step.key for step in question.steps]
        candidate.sort(key=lambda key: sha256(seed + key.encode()).digest())
        accepted = set(question.accepted_orders)
        ordered = tuple(candidate)
        if ordered not in accepted:
            return ordered

        for permutation in permutations(candidate):
            if permutation not in accepted:
                return permutation

        raise InvalidAttemptError
