from shifu.curriculum.core.domain.structures import FillBlanksQuestion
from shifu.fakers.curriculum.structures import FillBlanksQuestionFaker
from shifu.shared.core.domain.structures import (
    CurriculumFillBlanksBlankSnapshot,
    CurriculumFillBlanksConceptCriterionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumFillBlanksSegmentSnapshot,
    CurriculumFillBlanksWordSnapshot,
)


class CurriculumFillBlanksQuestionSnapshotFaker:
    @classmethod
    def fake(
        cls, question: FillBlanksQuestion | None = None
    ) -> CurriculumFillBlanksQuestionSnapshot:
        """Project a Curriculum fill-blanks question (the faker default) as a snapshot."""
        source = question or FillBlanksQuestionFaker.fake()
        return CurriculumFillBlanksQuestionSnapshot(
            key=source.key,
            prompt=source.prompt,
            content_language=source.content_language,
            segments=tuple(
                CurriculumFillBlanksSegmentSnapshot(
                    text=item.text, blank_key=item.blank_key
                )
                for item in source.segments
            ),
            blanks=tuple(
                CurriculumFillBlanksBlankSnapshot(
                    key=item.key, accepted_words=item.accepted_words
                )
                for item in source.blanks
            ),
            bank=tuple(
                CurriculumFillBlanksWordSnapshot(key=item.key, word=item.word)
                for item in source.bank
            ),
            correct_explanation=source.correct_explanation,
            incorrect_explanation=source.incorrect_explanation,
            partial_explanation=source.partial_explanation,
            concept_criteria=tuple(
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id=item.concept_id,
                    criterion=item.criterion,
                    examples=item.examples,
                    limits=item.limits,
                    blank_keys=item.blank_keys,
                )
                for item in source.concept_criteria
            ),
        )
