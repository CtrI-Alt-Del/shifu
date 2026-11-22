from decimal import Decimal

from shifu.curriculum.core.domain.structures import (
    ChoiceConceptCriterion,
    PracticalPreparationQuestion,
    PracticeCriterion,
    PracticeCriterionLevel,
    PracticeInsufficiencyRule,
    PracticePhotoRecord,
    PracticeReference,
)

_LEVEL_SCORES = (0, 25, 50, 75, 100)


class PracticalPreparationQuestionFaker:
    """Sauteed vegetables example: demonstration and test data only.

    Three records (cuts, during preparation, final dish) and three criteria
    weighted 40/40/20. The weights belong to this example, not to the kind.
    """

    @staticmethod
    def criterion(
        key: str,
        name: str,
        description: str,
        weight: Decimal | int,
    ) -> PracticeCriterion:
        return PracticeCriterion(
            key=key,
            name=name,
            description=description,
            weight=Decimal(weight),
            levels=tuple(
                PracticeCriterionLevel(
                    score=score,
                    description=f'{name}: nível {score} observável nas fotos.',
                    comment_key=f'{key}-{score}',
                )
                for score in _LEVEL_SCORES
            ),
            inconclusive_when='As fotos não mostram o suficiente para avaliar.',
        )

    @classmethod
    def records(cls) -> tuple[PracticePhotoRecord, ...]:
        return (
            PracticePhotoRecord(
                key='cuts',
                label='Cortes',
                must_show='Os legumes já cortados, na tábua ou em um recipiente.',
            ),
            PracticePhotoRecord(
                key='during',
                label='Durante o preparo',
                must_show='Os legumes na panela ou frigideira durante o salteado.',
            ),
            PracticePhotoRecord(
                key='final',
                label='Prato final',
                must_show='O prato pronto, servido.',
            ),
        )

    @classmethod
    def criteria(cls) -> tuple[PracticeCriterion, ...]:
        return (
            cls.criterion(
                'cut-regularity',
                'Regularidade dos cortes',
                'Os pedaços têm tamanho e formato parecidos.',
                40,
            ),
            cls.criterion(
                'observable-technique',
                'Técnica observável',
                'A técnica de salteado é visível durante o preparo.',
                40,
            ),
            cls.criterion(
                'presentation',
                'Apresentação',
                'O prato final está organizado e limpo.',
                20,
            ),
        )

    @classmethod
    def insufficiency_rules(cls) -> tuple[PracticeInsufficiencyRule, ...]:
        return (
            PracticeInsufficiencyRule(
                record_key='cuts',
                criterion_keys=('cut-regularity',),
                comment='Refaça a foto dos cortes com os legumes bem visíveis.',
            ),
            PracticeInsufficiencyRule(
                record_key='during',
                criterion_keys=('observable-technique',),
                comment='Registre o preparo na frigideira com os legumes visíveis.',
            ),
            PracticeInsufficiencyRule(
                record_key='final',
                criterion_keys=('presentation',),
                comment='Fotografe o prato finalizado com a apresentação inteira à vista.',
            ),
        )

    @classmethod
    def concept_criterion(cls, concept_id: str = 'concept-1') -> ChoiceConceptCriterion:
        return ChoiceConceptCriterion(
            concept_id=concept_id,
            criterion='Prepara legumes salteados com cortes regulares.',
            examples='Cortes de tamanho parecido e técnica de salteado visível.',
            limits='As fotos não medem sabor nem tempo de cozimento.',
            correct_score=100,
            incorrect_score=0,
        )

    @classmethod
    def fake(
        cls,
        *,
        key: str = 'sauteed-vegetables',
        prompt: str = 'Prepare legumes salteados e registre o resultado.',
        guidance: tuple[str, ...] = (
            'Use fogo alto e mexa os legumes com frequência.',
        ),
        references: tuple[PracticeReference, ...] = (
            PracticeReference(
                label='Técnica de salteado',
                accessible_text='Legumes cortados em pedaços iguais, em fogo alto.',
            ),
        ),
        difficulty: str = 'easy',
        records: tuple[PracticePhotoRecord, ...] | None = None,
        criteria: tuple[PracticeCriterion, ...] | None = None,
        insufficiency_rules: tuple[PracticeInsufficiencyRule, ...] | None = None,
        concept_criteria: tuple[ChoiceConceptCriterion, ...] | None = None,
    ) -> PracticalPreparationQuestion:
        return PracticalPreparationQuestion(
            key=key,
            prompt=prompt,
            guidance=guidance,
            references=references,
            difficulty=difficulty,
            records=records if records is not None else cls.records(),
            criteria=criteria if criteria is not None else cls.criteria(),
            insufficiency_rules=(
                insufficiency_rules
                if insufficiency_rules is not None
                else cls.insufficiency_rules()
            ),
            concept_criteria=(
                concept_criteria
                if concept_criteria is not None
                else (cls.concept_criterion(),)
            ),
        )
