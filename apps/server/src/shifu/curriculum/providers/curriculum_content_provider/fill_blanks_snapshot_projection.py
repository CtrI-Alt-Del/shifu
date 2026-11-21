from shifu.curriculum.core.domain.structures import FillBlanksQuestion
from shifu.shared.core.domain.structures import (
    CurriculumFillBlanksBlankSnapshot,
    CurriculumFillBlanksConceptCriterionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumFillBlanksSegmentSnapshot,
    CurriculumFillBlanksWordSnapshot,
)


class FillBlanksSnapshotProjection:
    @staticmethod
    def project(
        question: FillBlanksQuestion,
        competency_concept_ids: set[str],
        activity_type: str,
    ) -> CurriculumFillBlanksQuestionSnapshot | None:
        """Publish a Learning-only fill-blanks question for its own Competency."""
        if activity_type != 'learning' or not {
            criterion.concept_id for criterion in question.concept_criteria
        }.issubset(competency_concept_ids):
            return None

        return CurriculumFillBlanksQuestionSnapshot(
            key=question.key,
            prompt=question.prompt,
            content_language=question.content_language,
            segments=tuple(
                CurriculumFillBlanksSegmentSnapshot(
                    text=segment.text, blank_key=segment.blank_key
                )
                for segment in question.segments
            ),
            blanks=tuple(
                CurriculumFillBlanksBlankSnapshot(
                    key=blank.key, accepted_words=blank.accepted_words
                )
                for blank in question.blanks
            ),
            bank=tuple(
                CurriculumFillBlanksWordSnapshot(key=word.key, word=word.word)
                for word in question.bank
            ),
            correct_explanation=question.correct_explanation,
            incorrect_explanation=question.incorrect_explanation,
            partial_explanation=question.partial_explanation,
            concept_criteria=tuple(
                CurriculumFillBlanksConceptCriterionSnapshot(
                    concept_id=criterion.concept_id,
                    criterion=criterion.criterion,
                    examples=criterion.examples,
                    limits=criterion.limits,
                    blank_keys=criterion.blank_keys,
                )
                for criterion in question.concept_criteria
            ),
        )
