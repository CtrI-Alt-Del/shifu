from shifu.learning.core.domain.entities import Goal, SkillExperience
from shifu.learning.core.domain.enums import SkillExperienceStatus
from shifu.learning.core.domain.structures.competency_material_detail import (
    CompetencyMaterialDetail,
)
from shifu.learning.core.domain.structures.available_competency_detail import (
    AvailableCompetencyDetail,
)
from shifu.learning.core.domain.errors import CompetencyDetailNotFoundError
from shifu.learning.core.interfaces import LearningDatabase
from shifu.learning.core.use_cases.get_competency_detail_use_case import (
    GetCompetencyDetailUseCase,
)
from shifu.shared.core.domain.structures import (
    MentorCatalogEntry,
    MentorContextSnapshot,
)
from shifu.shared.core.interfaces import MentorCatalogProvider

_LIST_LIMIT = 20
_COUNT_LABELS: tuple[tuple[SkillExperienceStatus, str, str], ...] = (
    (SkillExperienceStatus.NOT_STARTED, 'não iniciada', 'não iniciadas'),
    (SkillExperienceStatus.DIAGNOSING, 'em diagnóstico', 'em diagnóstico'),
    (SkillExperienceStatus.LEARNING, 'em aprendizado', 'em aprendizado'),
    (SkillExperienceStatus.COMPLETED, 'concluída', 'concluídas'),
)


def _count_label(count: int, singular: str, plural: str) -> str:
    if count == 0:
        return ''
    return f'{count} {singular if count == 1 else plural}'


class LearningMentorContextProvider:
    """Expose current owned facts and Learning's released content, never answer keys."""

    def __init__(
        self,
        database: LearningDatabase,
        catalog: MentorCatalogProvider,
        competency_detail: GetCompetencyDetailUseCase,
    ) -> None:
        self._database = database
        self._catalog = catalog
        self._competency_detail = competency_detail

    def read(
        self,
        account_id: str,
        reference_ids: tuple[str, ...],
        *,
        goal_id: str | None = None,
        skill_id: str | None = None,
        competency_id: str | None = None,
        material_id: str | None = None,
        activity_id: str | None = None,
    ) -> MentorContextSnapshot:
        projection = self._catalog.read_projection()
        explicit = frozenset(reference_ids)
        explicit_skills = {
            entry.skill_id for entry in projection if entry.reference_id in explicit
        }
        with self._database.transaction() as repositories:
            goals = repositories.goals.find_many_by_account_id(account_id)
            explicit_goals = [goal for goal in goals if goal.id in explicit]
            if len(explicit_goals) == 1:
                skill_id, competency_id, material_id, activity_id = self._override_hint(
                    goal_id != explicit_goals[0].id,
                    (skill_id, competency_id, material_id, activity_id),
                )
                goal_id = explicit_goals[0].id
            goal = next((goal for goal in goals if goal.id == goal_id), None)
            if goal_id is not None and goal is None:
                raise CompetencyDetailNotFoundError
            facts = tuple(('goals', f'{goal.id}: {goal.title}') for goal in goals)
            ordered = sorted(
                sorted(goals, key=lambda owned: owned.id),
                key=lambda owned: owned.updated_at,
                reverse=True,
            )
            experiences = {
                owned.id: sorted(
                    repositories.skill_experiences.find_many_by_goal_id(owned.id),
                    key=lambda item: (item.created_at, item.id),
                )
                for owned in ordered
            }
            names = {
                entry.skill_id: entry.title
                for entry in projection
                if entry.kind == 'skill'
            }
            facts += self._completed_facts(ordered, experiences, names)
            if len(explicit_goals) > 1 or len(explicit_skills) > 1:
                return self._unresolved(
                    projection,
                    (
                        *facts,
                        (
                            'context_clarification',
                            'Indique um único Objetivo e uma única Habilidade para continuar.',
                        ),
                    ),
                    resolved_references=reference_ids,
                )
            if goal is None:
                return self._unresolved(
                    projection, facts + self._overview_facts(ordered, experiences)
                )
            if len(explicit_skills) == 1:
                selected_skill_id = next(iter(explicit_skills))
                _, competency_id, material_id, activity_id = self._override_hint(
                    skill_id != selected_skill_id,
                    (None, competency_id, material_id, activity_id),
                )
                skill_id = selected_skill_id
            experience = (
                repositories.skill_experiences.find_by_goal_id_and_skill_id(
                    goal.id, skill_id
                )
                if skill_id
                else None
            )
            if skill_id is not None and experience is None:
                raise CompetencyDetailNotFoundError
            if experience is None:
                return self._unresolved(
                    projection,
                    facts + self._goal_skill_facts(goal, experiences[goal.id], names),
                    goal.id,
                )
            selected = tuple(
                entry for entry in projection if entry.skill_id == experience.skill_id
            )
            status = experience.status
            self._validate_context_hint(
                selected,
                status,
                experience.skill_id,
                competency_id,
                material_id,
                activity_id,
            )
            facts += (
                ('progress_summary', f'Habilidade: {self._status_label(status.value)}'),
            )
            experience_id = experience.id
        allowed, current_facts = (
            (
                tuple(
                    entry.reference_id for entry in selected if entry.kind == 'skill'
                ),
                (),
            )
            if status
            in {SkillExperienceStatus.DIAGNOSING, SkillExperienceStatus.NOT_STARTED}
            else self._eligible_entries(
                account_id, goal.id, experience.skill_id, selected
            )
        )
        facts += current_facts
        self._validate_released_hint(
            allowed, status, competency_id, material_id, activity_id
        )
        resolved = tuple(
            dict.fromkeys((goal.id, *(ref for ref in reference_ids if ref in allowed)))
        )
        return MentorContextSnapshot(
            goal_id=goal.id,
            skill_experience_id=experience_id,
            skill_id=experience.skill_id,
            competency_id=competency_id,
            activity_id=activity_id,
            skill_completed=status is SkillExperienceStatus.COMPLETED,
            diagnostic_in_progress=status is SkillExperienceStatus.DIAGNOSING,
            facts=facts,
            eligible_references=allowed,
            resolved_references=resolved,
            unavailable_sources=('gamification',),
        )

    @staticmethod
    def _bounded(values: list[str]) -> list[str]:
        if len(values) <= _LIST_LIMIT:
            return values
        return [*values[:_LIST_LIMIT], f'e mais {len(values) - _LIST_LIMIT}.']

    @staticmethod
    def _skill_name(names: dict[str, str], skill_id: str) -> str:
        return names.get(skill_id) or 'Habilidade sem título'

    def _completed_facts(
        self,
        goals: list[Goal],
        experiences: dict[str, list[SkillExperience]],
        names: dict[str, str],
    ) -> tuple[tuple[str, str], ...]:
        entries = [
            f'{self._skill_name(names, experience.skill_id)} (Objetivo {goal.title})'
            for goal in goals
            for experience in experiences[goal.id]
            if experience.status is SkillExperienceStatus.COMPLETED
        ]
        return tuple(('completed_skills', value) for value in self._bounded(entries))

    def _overview_facts(
        self,
        goals: list[Goal],
        experiences: dict[str, list[SkillExperience]],
    ) -> tuple[tuple[str, str], ...]:
        lines = [self._overview_line(goal, experiences[goal.id]) for goal in goals]
        return tuple(('progress_overview', value) for value in self._bounded(lines))

    @staticmethod
    def _overview_line(goal: Goal, experiences: list[SkillExperience]) -> str:
        if not experiences:
            return f'{goal.title}: nenhuma Habilidade ainda.'
        counts = [
            _count_label(
                sum(1 for item in experiences if item.status is status),
                singular,
                plural,
            )
            for status, singular, plural in _COUNT_LABELS
        ]
        total = len(experiences)
        noun = 'Habilidade' if total == 1 else 'Habilidades'
        return f'{goal.title}: {total} {noun} — {", ".join(c for c in counts if c)}.'

    def _goal_skill_facts(
        self,
        goal: Goal,
        experiences: list[SkillExperience],
        names: dict[str, str],
    ) -> tuple[tuple[str, str], ...]:
        lines = [
            f'{self._skill_name(names, item.skill_id)}: {self._status_label(item.status.value)}'
            for item in experiences
        ] or ['Este Objetivo ainda não tem Habilidades.']
        return (
            ('goal_progress_title', goal.title),
            *(('goal_skill_status', value) for value in self._bounded(lines)),
        )

    @staticmethod
    def _override_hint(
        changed: bool,
        hint: tuple[str | None, str | None, str | None, str | None],
    ) -> tuple[str | None, str | None, str | None, str | None]:
        return (None, None, None, None) if changed else hint

    @staticmethod
    def _validate_released_hint(
        allowed: tuple[str, ...],
        status: SkillExperienceStatus,
        competency_id: str | None,
        material_id: str | None,
        activity_id: str | None,
    ) -> None:
        for reference_id in (
            None if status is SkillExperienceStatus.DIAGNOSING else competency_id,
            material_id,
            None if status is SkillExperienceStatus.DIAGNOSING else activity_id,
        ):
            if reference_id is not None and reference_id not in allowed:
                raise CompetencyDetailNotFoundError

    def _validate_context_hint(
        self,
        entries: tuple[MentorCatalogEntry, ...],
        status: SkillExperienceStatus,
        skill_id: str,
        competency_id: str | None,
        material_id: str | None,
        activity_id: str | None,
    ) -> None:
        diagnostic_activity = (
            status is SkillExperienceStatus.DIAGNOSING
            and activity_id is not None
            and self._catalog.is_diagnostic_activity(
                skill_id, competency_id, activity_id
            )
        )
        self._validate_hint(
            entries,
            competency_id,
            material_id,
            None if diagnostic_activity else activity_id,
        )

    def _eligible_entries(
        self,
        account_id: str,
        goal_id: str,
        skill_id: str,
        entries: tuple[MentorCatalogEntry, ...],
    ) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
        facts: list[tuple[str, str]] = []
        allowed = {entry.reference_id for entry in entries if entry.kind == 'skill'}
        for entry in entries:
            if entry.kind != 'competency':
                continue
            detail = self._competency_detail.execute(
                account_id, goal_id, skill_id, entry.reference_id
            )
            if not isinstance(detail, AvailableCompetencyDetail):
                continue
            allowed.add(entry.reference_id)
            value = (
                str(detail.progress) if detail.progress is not None else 'desconhecido'
            )
            coverage = 'completa' if detail.coverage_complete else 'parcial'
            facts.append(
                (
                    'progress_summary',
                    f'{detail.competency_name}: {value}; cobertura {coverage}; {self._status_label(detail.status.value)}',
                )
            )
            for item in detail.items:
                if isinstance(item, CompetencyMaterialDetail):
                    allowed.add(item.id)
                    facts.append(('eligible_materials', f'{item.id}: {item.title}'))
                elif item.activity_type == 'learning':
                    allowed.add(item.id)
                    facts.append(('activities', f'{item.id}: {item.title}'))
                    if item.latest_score is not None:
                        facts.append(
                            (
                                'assessment_summary',
                                f'{item.title}: nota oficial {item.latest_score}',
                            )
                        )
            if detail.adaptive is not None:
                facts.append(
                    (
                        'recommendation',
                        f'Learning recomenda: {self._reason_label(detail.adaptive.reason)}; alvo {detail.adaptive.target_concept_name or "não informado"}; atividade {detail.adaptive.activity_id or "indisponível"}',
                    )
                )
        return tuple(sorted(allowed)), tuple(facts)

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            'learning': 'em aprendizado',
            'developing': 'em desenvolvimento',
            'proficient': 'proficiente',
            'mastered': 'dominada',
            'completed': 'concluída',
            'diagnosing': 'diagnóstico em andamento',
            'not-started': 'não iniciada',
        }.get(status, 'estado indisponível')

    @staticmethod
    def _reason_label(reason: str) -> str:
        return {
            'verification': 'Confirmar uma evidência inconclusiva.',
            'coverage': 'Cobrir evidências que ainda faltam neste Conceito.',
            'practice': 'Fortalecer este Conceito com uma nova prática.',
            'hard_confirmation': 'Confirmar o aprendizado em uma Atividade difícil.',
            'consolidation': 'Consolidar o domínio alcançado.',
            'regression': 'Verificar o desempenho recente.',
            'prerequisite': 'Fortalecer primeiro um fundamento necessário.',
        }.get(reason, 'Consultar o próximo passo oficial em Learning.')

    @staticmethod
    def _validate_hint(
        entries: tuple[MentorCatalogEntry, ...],
        competency_id: str | None,
        material_id: str | None,
        activity_id: str | None,
    ) -> None:
        for reference_id, kind in (
            (competency_id, 'competency'),
            (material_id, 'material'),
            (activity_id, 'activity'),
        ):
            if reference_id is None:
                continue
            matches = [
                entry
                for entry in entries
                if entry.reference_id == reference_id and entry.kind == kind
            ]
            if not matches or (
                kind != 'competency'
                and competency_id is not None
                and not any(entry.competency_id == competency_id for entry in matches)
            ):
                raise CompetencyDetailNotFoundError

    @staticmethod
    def _unresolved(
        projection: tuple[MentorCatalogEntry, ...],
        facts: tuple[tuple[str, str], ...],
        goal_id: str | None = None,
        resolved_references: tuple[str, ...] | None = None,
    ) -> MentorContextSnapshot:
        return MentorContextSnapshot(
            goal_id=goal_id,
            skill_experience_id=None,
            skill_id=None,
            competency_id=None,
            activity_id=None,
            skill_completed=None,
            diagnostic_in_progress=False,
            facts=facts,
            eligible_references=tuple(
                entry.reference_id for entry in projection if entry.kind == 'skill'
            ),
            resolved_references=(
                resolved_references
                if resolved_references is not None
                else (goal_id,)
                if goal_id is not None
                else ()
            ),
            unavailable_sources=('gamification',),
        )
