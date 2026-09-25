from shifu.shared.core.domain.structures import (
    CurriculumActivitySnapshot,
    CurriculumChoiceActivitySnapshot,
    CurriculumSkillSnapshot,
)


class ChoiceEvidenceEligibility:
    @staticmethod
    def is_valid(
        snapshot: CurriculumChoiceActivitySnapshot,
        skill: CurriculumSkillSnapshot | None,
    ) -> bool:
        if skill is None or not skill.v2_eligible:
            return False
        competency = next(
            (item for item in skill.competencies if item.id == snapshot.competency_id),
            None,
        )
        if competency is None:
            return False
        if snapshot.activity_type == 'diagnostic':
            candidates = competency.diagnostic_activities
        elif snapshot.activity_type == 'learning':
            candidates = tuple(
                item
                for item in competency.items
                if isinstance(item, CurriculumActivitySnapshot)
            )
        else:
            return False
        activity = next((item for item in candidates if item.id == snapshot.id), None)
        if activity is None or not activity.executable_concept_evidence:
            return False
        if activity.required_concept_ids != snapshot.required_concept_ids:
            return False
        mapped = tuple(
            criterion.concept_id
            for question in snapshot.questions
            for criterion in question.concept_criteria
        )
        return (
            bool(snapshot.questions)
            and all(question.concept_criteria for question in snapshot.questions)
            and set(mapped) == set(activity.concept_ids)
            and all(
                mapped.count(concept_id) == count
                for concept_id, count in activity.question_count_by_concept
            )
        )
