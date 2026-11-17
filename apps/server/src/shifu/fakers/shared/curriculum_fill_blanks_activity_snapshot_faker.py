from decimal import Decimal

from shifu.fakers.shared.curriculum_fill_blanks_question_snapshot_faker import (
    CurriculumFillBlanksQuestionSnapshotFaker,
)
from shifu.shared.core.domain.structures import (
    CurriculumChoiceConceptCriterionSnapshot,
    CurriculumChoiceOptionSnapshot,
    CurriculumChoicePartSnapshot,
    CurriculumChoiceQuestionSnapshot,
    CurriculumFillBlanksQuestionSnapshot,
    CurriculumLearningActivitySnapshot,
)


class CurriculumFillBlanksActivitySnapshotFaker:
    """A Learning Activity of one fill-blanks question and two single-choice ones."""

    @classmethod
    def fake(
        cls,
        *,
        activity_id: str = 'activity-1',
        competency_id: str = 'competency-1',
        revision: str = 'revision-1',
        choice_concept_id: str = 'concept-choice',
        fill_blanks: CurriculumFillBlanksQuestionSnapshot | None = None,
    ) -> CurriculumLearningActivitySnapshot:
        fill = fill_blanks or CurriculumFillBlanksQuestionSnapshotFaker.fake()
        choices = tuple(
            CurriculumChoiceQuestionSnapshot(
                key=f'q{number}',
                kind='single_choice',
                prompt='Choose',
                options=(
                    CurriculumChoiceOptionSnapshot(key='a', text='A', is_correct=True),
                    CurriculumChoiceOptionSnapshot(key='b', text='B', is_correct=False),
                ),
                correct_explanation='Correct',
                incorrect_explanation='Wrong',
                concept_criteria=(
                    CurriculumChoiceConceptCriterionSnapshot(
                        concept_id=choice_concept_id,
                        criterion='Picks the right option.',
                        examples='A.',
                        limits='None.',
                        correct_score=Decimal(100),
                        incorrect_score=Decimal(0),
                    ),
                ),
            )
            for number in (1, 2)
        )
        return CurriculumLearningActivitySnapshot(
            id=activity_id,
            competency_id=competency_id,
            difficulty='easy',
            title='English practice',
            questions=(fill, *choices),
            parts=(
                CurriculumChoicePartSnapshot(
                    question_key=fill.key, weight_percentage=Decimal(40)
                ),
                CurriculumChoicePartSnapshot(
                    question_key='q1', weight_percentage=Decimal(30)
                ),
                CurriculumChoicePartSnapshot(
                    question_key='q2', weight_percentage=Decimal(30)
                ),
            ),
            required_concept_ids=(),
            activity_type='learning',
            schema_version=1,
            revision=revision,
        )
