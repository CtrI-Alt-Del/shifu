from decimal import Decimal

from shifu.shared.core.domain.structures import (
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumImageChoiceOptionSnapshot,
    CurriculumImageChoiceQuestionSnapshot,
)


class CurriculumImageChoiceQuestionSnapshotFaker:
    """Option ``i`` has the opaque key ``opt-<i + 1 as 12 hex>`` and a distinct image."""

    @staticmethod
    def option_key(index: int) -> str:
        return f'opt-{index + 1:012x}'

    @classmethod
    def fake(
        cls,
        key: str = 'qi',
        *,
        size: int = 4,
        correct_index: int = 2,
        concept_ids: tuple[str, ...] = ('concept-1',),
        correct_score: int | None = 100,
        incorrect_score: int | None = 0,
    ) -> CurriculumImageChoiceQuestionSnapshot:
        return CurriculumImageChoiceQuestionSnapshot(
            key=key,
            kind='image_choice',
            prompt='Qual destas cebolas está caramelizada?',
            options=tuple(
                CurriculumImageChoiceOptionSnapshot(
                    key=cls.option_key(index),
                    image_path=f'/curriculum/images/{index + 1:016x}.webp',
                    description=f'Descrição visual {index + 1}',
                    is_correct=index == correct_index,
                    feedback=f'Linha de retorno {index + 1}',
                )
                for index in range(size)
            ),
            correct_explanation='Explicação de acerto.',
            incorrect_explanation='Explicação de erro.',
            concept_criteria=tuple(
                CurriculumChoiceConceptCriterionSnapshot(
                    concept_id=concept_id,
                    criterion='Reconhece o ponto de cocção',
                    examples='Cebola macia e escura.',
                    limits='Não mede a execução.',
                    correct_score=(
                        None if correct_score is None else Decimal(correct_score)
                    ),
                    incorrect_score=(
                        None if incorrect_score is None else Decimal(incorrect_score)
                    ),
                )
                for concept_id in concept_ids
            ),
        )
