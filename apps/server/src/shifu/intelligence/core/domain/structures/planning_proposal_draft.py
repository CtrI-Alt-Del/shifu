from collections.abc import Mapping

from shifu.shared.core.domain.structures import structure


@structure
class PlanningProposalDraftSkill:
    skill_id: str
    justification: str


@structure
class PlanningProposalDraft:
    """Model output before the mechanical validation that gates its exposure."""

    title: str
    description: str
    skills: tuple[PlanningProposalDraftSkill, ...]

    def problems(self, candidates: Mapping[str, str]) -> tuple[str, ...]:
        """List, in pt-BR, every rule the draft breaks; empty means valid."""
        problems: list[str] = []
        if not self.title.strip():
            problems.append('O título está ausente.')
        if not self.description.strip():
            problems.append('A descrição está ausente.')
        if not self.skills:
            problems.append('A proposta precisa de ao menos uma Habilidade.')
        seen: set[str] = set()
        for skill in self.skills:
            if skill.skill_id not in candidates:
                problems.append(
                    f'A Habilidade "{skill.skill_id}" não existe entre as candidatas.'
                )
            elif skill.skill_id in seen:
                problems.append(
                    f'A Habilidade "{candidates[skill.skill_id]}" está duplicada.'
                )
            elif not skill.justification.strip():
                problems.append(
                    f'A Habilidade "{candidates[skill.skill_id]}" está sem justificativa.'
                )
            seen.add(skill.skill_id)
        return tuple(problems)
