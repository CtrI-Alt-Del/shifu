from shifu.curriculum.core.domain.structures import (
    FillBlanksBankWord,
    FillBlanksBlank,
    FillBlanksConceptCriterion,
    FillBlanksQuestion,
    FillBlanksSegment,
)


class FillBlanksQuestionFaker:
    """Three blanks: two share a grammar Concept, one has a vocabulary Concept."""

    @classmethod
    def fake(
        cls,
        *,
        key: str = 'fill-1',
        segments: tuple[FillBlanksSegment, ...] | None = None,
        blanks: tuple[FillBlanksBlank, ...] | None = None,
        bank: tuple[FillBlanksBankWord, ...] | None = None,
        concept_criteria: tuple[FillBlanksConceptCriterion, ...] | None = None,
        partial_explanation: str | None = 'Almost there. Review the verb forms.',
    ) -> FillBlanksQuestion:
        return FillBlanksQuestion(
            key=key,
            prompt='Complete o texto com as palavras do banco.',
            content_language='en',
            segments=segments
            if segments is not None
            else (
                FillBlanksSegment(text='She '),
                FillBlanksSegment(blank_key='b1'),
                FillBlanksSegment(text=' to school and '),
                FillBlanksSegment(blank_key='b2'),
                FillBlanksSegment(text=' her homework every '),
                FillBlanksSegment(blank_key='b3'),
                FillBlanksSegment(text='.'),
            ),
            blanks=blanks
            if blanks is not None
            else (
                FillBlanksBlank(key='b1', accepted_words=('goes', 'walks')),
                FillBlanksBlank(key='b2', accepted_words=('does',)),
                FillBlanksBlank(key='b3', accepted_words=('day',)),
            ),
            bank=bank
            if bank is not None
            else (
                FillBlanksBankWord(key='w1', word='goes'),
                FillBlanksBankWord(key='w2', word='walks'),
                FillBlanksBankWord(key='w3', word='does'),
                FillBlanksBankWord(key='w4', word='day'),
                FillBlanksBankWord(key='w5', word='day'),
                FillBlanksBankWord(key='w6', word='go'),
            ),
            correct_explanation='Correct. The third person singular takes -s or -es.',
            incorrect_explanation='Review the third person singular of the present.',
            partial_explanation=partial_explanation,
            concept_criteria=concept_criteria
            if concept_criteria is not None
            else (
                FillBlanksConceptCriterion(
                    concept_id='concept-grammar',
                    criterion='Verb agreement in the third person singular.',
                    examples='She goes; she does.',
                    limits='Spelling is not observed.',
                    blank_keys=('b1', 'b2'),
                ),
                FillBlanksConceptCriterion(
                    concept_id='concept-vocabulary',
                    criterion='Common time expressions.',
                    examples='every day.',
                    limits='Only the expression in the text.',
                    blank_keys=('b3',),
                ),
            ),
        )
