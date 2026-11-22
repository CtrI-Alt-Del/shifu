from decimal import Decimal

from shifu.shared.core.domain.structures import (
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumPracticalPreparationCriterionSnapshot,
    CurriculumPracticalPreparationInsufficiencyRuleSnapshot,
    CurriculumPracticalPreparationLevelSnapshot,
    CurriculumPracticalPreparationQuestionSnapshot,
    CurriculumPracticalPreparationRecordSnapshot,
    CurriculumPracticalPreparationReferenceSnapshot,
)

_LEVEL_SCORES = (0, 25, 50, 75, 100)


class CurriculumPracticalPreparationQuestionSnapshotFaker:
    """Sauteed vegetables example (records cuts/during/final, weights 40/40/20)."""

    @staticmethod
    def criterion(
        key: str, name: str, weight: Decimal | int
    ) -> CurriculumPracticalPreparationCriterionSnapshot:
        return CurriculumPracticalPreparationCriterionSnapshot(
            key=key,
            name=name,
            description=f'{name} observável nas fotos.',
            weight=Decimal(weight),
            levels=tuple(
                CurriculumPracticalPreparationLevelSnapshot(
                    score=score,
                    description=f'{name}: nível {score} observável nas fotos.',
                    comment_key=f'{key}-{score}',
                )
                for score in _LEVEL_SCORES
            ),
            inconclusive_when='As fotos não mostram o suficiente para avaliar.',
        )

    @classmethod
    def fake(
        cls,
        *,
        key: str = 'sauteed-vegetables',
        records: tuple[CurriculumPracticalPreparationRecordSnapshot, ...] | None = None,
        criteria: tuple[CurriculumPracticalPreparationCriterionSnapshot, ...]
        | None = None,
        insufficiency_rules: tuple[
            CurriculumPracticalPreparationInsufficiencyRuleSnapshot, ...
        ]
        | None = None,
        concept_criteria: tuple[CurriculumChoiceConceptCriterionSnapshot, ...]
        | None = None,
    ) -> CurriculumPracticalPreparationQuestionSnapshot:
        return CurriculumPracticalPreparationQuestionSnapshot(
            key=key,
            kind='practical_preparation',
            prompt='Prepare legumes salteados e registre o resultado.',
            guidance=('Use fogo alto e mexa os legumes com frequência.',),
            references=(
                CurriculumPracticalPreparationReferenceSnapshot(
                    label='Técnica de salteado',
                    accessible_text='Legumes cortados em pedaços iguais, em fogo alto.',
                ),
            ),
            difficulty='easy',
            records=records
            if records is not None
            else (
                CurriculumPracticalPreparationRecordSnapshot(
                    key='cuts',
                    label='Cortes',
                    must_show='Os legumes já cortados.',
                ),
                CurriculumPracticalPreparationRecordSnapshot(
                    key='during',
                    label='Durante o preparo',
                    must_show='Os legumes na panela durante o salteado.',
                ),
                CurriculumPracticalPreparationRecordSnapshot(
                    key='final',
                    label='Prato final',
                    must_show='O prato pronto, servido.',
                ),
            ),
            criteria=criteria
            if criteria is not None
            else (
                cls.criterion('cut-regularity', 'Regularidade dos cortes', 40),
                cls.criterion('observable-technique', 'Técnica observável', 40),
                cls.criterion('presentation', 'Apresentação', 20),
            ),
            insufficiency_rules=insufficiency_rules
            if insufficiency_rules is not None
            else (
                CurriculumPracticalPreparationInsufficiencyRuleSnapshot(
                    record_key='cuts',
                    criterion_keys=('cut-regularity',),
                    comment='Refaça a foto dos cortes com os legumes bem visíveis.',
                ),
                CurriculumPracticalPreparationInsufficiencyRuleSnapshot(
                    record_key='during',
                    criterion_keys=('observable-technique',),
                    comment='Registre o preparo na frigideira com os legumes visíveis.',
                ),
                CurriculumPracticalPreparationInsufficiencyRuleSnapshot(
                    record_key='final',
                    criterion_keys=('presentation',),
                    comment='Fotografe o prato finalizado com a apresentação inteira à vista.',
                ),
            ),
            concept_criteria=concept_criteria
            if concept_criteria is not None
            else (
                CurriculumChoiceConceptCriterionSnapshot(
                    concept_id='concept-1',
                    criterion='Prepara legumes salteados com cortes regulares.',
                    examples='Cortes de tamanho parecido.',
                    limits='As fotos não medem sabor.',
                    correct_score=Decimal(100),
                    incorrect_score=Decimal(0),
                ),
            ),
        )
