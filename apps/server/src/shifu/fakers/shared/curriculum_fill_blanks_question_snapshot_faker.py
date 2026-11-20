from shifu.shared.core.domain.structures import (
    CurriculumFillBlanksBlankSnapshot,
    CurriculumFillBlanksConceptCriterionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumFillBlanksSegmentSnapshot,
    CurriculumFillBlanksWordSnapshot,
)


class CurriculumFillBlanksQuestionSnapshotFaker:
    """Three blanks: two share a grammar Concept, one has a vocabulary Concept."""

    @classmethod
    def fake(
        cls,
        *,
        key: str = 'fill-1',
        segments: tuple[CurriculumFillBlanksSegmentSnapshot, ...] | None = None,
        blanks: tuple[CurriculumFillBlanksBlankSnapshot, ...] | None = None,
        bank: tuple[CurriculumFillBlanksWordSnapshot, ...] | None = None,
        concept_criteria: tuple[CurriculumFillBlanksConceptCriterionSnapshot, ...]
        | None = None,
        partial_explanation: str | None = 'Almost there. Review the verb forms.',
    ) -> CurriculumFillBlanksQuestionSnapshot:
        return CurriculumFillBlanksQuestionSnapshot(
            key=key,
            prompt='Complete o texto com as palavras do banco.',
            content_language='en',
            segments=segments
            if segments is not None
            else (
                CurriculumFillBlanksSegmentSnapshot(text='She '),
                CurriculumFillBlanksSegmentSnapshot(blank_key='b1'),
                CurriculumFillBlanksSegmentSnapshot(text=' to school and '),
                CurriculumFillBlanksSegmentSnapshot(blank_key='b2'),
                CurriculumFillBlanksSegmentSnapshot(text=' her homework every '),
                CurriculumFillBlanksSegmentSnapshot(blank_key='b3'),
                CurriculumFillBlanksSegmentSnapshot(text='.'),
            ),
            blanks=blanks
            if blanks is not None
            else (
                CurriculumFillBlanksBlankSnapshot(
                    key='b1', accepted_words=('goes', 'walks')
                ),
                CurriculumFillBlanksBlankSnapshot(key='b2', accepted_words=('does',)),
                CurriculumFillBlanksBlankSnapshot(key='b3', accepted_words=('day',)),
            ),
            bank=bank
            if bank is not None
            else (
                CurriculumFillBlanksWordSnapshot(key='w4', word='day'),
                CurriculumFillBlanksWordSnapshot(key='w6', word='go'),
                CurriculumFillBlanksWordSnapshot(key='w3', word='does'),
                CurriculumFillBlanksWordSnapshot(key='w1', word='goes'),
                CurriculumFillBlanksWordSnapshot(key='w5', word='day'),
                CurriculumFillBlanksWordSnapshot(key='w2', word='walks'),
            ),
            correct_explanation='Correct. The third person singular takes -s or -es.',
            incorrect_explanation='Review the third person singular of the present.',
            partial_explanation=partial_explanation,
            concept_criteria=concept_criteria
            if concept_criteria is not None
            else (
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id='concept-grammar',
                    criterion='Verb agreement in the third person singular.',
                    examples='She goes; she does.',
                    limits='Spelling is not observed.',
                    blank_keys=('b1', 'b2'),
                ),
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id='concept-vocabulary',
                    criterion='Common time expressions.',
                    examples='every day.',
                    limits='Only the expression in the text.',
                    blank_keys=('b3',),
                ),
            ),
        )
