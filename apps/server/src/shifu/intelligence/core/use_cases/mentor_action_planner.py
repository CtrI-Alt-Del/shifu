import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from shifu.intelligence.core.domain.enums import MentorActionKind, MentorIntent
from shifu.intelligence.core.domain.structures import (
    MentorActionCandidateGoal,
    MentorActionProposalDraft,
    MentorResponseBlock,
    MentorRouteResult,
)
from shifu.intelligence.core.interfaces import MentorRouteProvider
from shifu.shared.core.domain.structures import (
    MentorCatalogEntry,
    MentorContextSnapshot,
    MentorGoalDestination,
)
from shifu.shared.core.interfaces import (
    MentorCatalogProvider,
    MentorGoalDestinationsProvider,
)


@dataclass(frozen=True)
class MentorActionPlan:
    """Answer blocks for the action part of a message and the optional proposal."""

    blocks: tuple[MentorResponseBlock, ...]
    draft: MentorActionProposalDraft | None


@dataclass(frozen=True)
class _ActionRequest:
    kind: MentorActionKind
    part: str


class MentorActionPlanner:
    """Turn an explicit add/remove Skill request into a proposal or a safe text answer.

    The Mentor only proposes: the draft is persisted by the publication and nothing
    runs until the learner presses the card button (RF-01 to RF-05).
    """

    PROPOSAL_BLOCK_KEY: ClassVar[str] = 'action-proposal'
    REPEAT_BLOCK_KEY: ClassVar[str] = 'action-repeat'
    TEXT_BLOCK_KEY: ClassVar[str] = 'action-text'
    PROPOSAL_TEXT: ClassVar[str] = 'Preparei uma proposta para você confirmar.'
    REPEAT_TEXT: ClassVar[str] = (
        'Para a outra ação, envie o pedido de novo depois de responder a esta proposta.'
    )
    NO_GOALS_TEXT: ClassVar[str] = (
        'Ainda não encontrei Objetivos seus. O Mentor não cria Objetivos; '
        'você pode [criar um Objetivo](/learning/goals/new).'
    )
    SKILL_NOT_FOUND_TEXT: ClassVar[str] = 'Não encontrei essa Habilidade no Currículo.'
    JUSTIFICATION_PREFIX: ClassVar[str] = (
        'Você pediu ao Mentor para adicionar esta Habilidade.'
    )
    MAX_JUSTIFICATION_CODE_POINTS: ClassVar[int] = 2000
    MAX_SUGGESTED_SKILLS: ClassVar[int] = 5
    MIN_CONTENT_WORD_LENGTH: ClassVar[int] = 3
    _STOPWORDS: ClassVar[frozenset[str]] = frozenset(
        {'em', 'de', 'do', 'da', 'dos', 'das', 'e', 'a', 'o', 'para', 'no', 'na'}
    )
    _ACTION_INTENTS: ClassVar[dict[MentorIntent, MentorActionKind]] = {
        MentorIntent.ADD_SKILL: MentorActionKind.ADD_SKILL,
        MentorIntent.REMOVE_SKILL: MentorActionKind.REMOVE_SKILL,
    }
    # A conjunction that introduces another add/remove request starts a new part:
    # "adicione X ao meu Objetivo e remova Y do meu Objetivo". The verbs only decide
    # where to cut; the route provider still classifies each part.
    _ACTION_VERB: ClassVar[str] = (
        r'adicion(?:a|am|e|em|ar|o)|acrescent(?:a|am|e|em|ar|o)'
        r'|inclu(?:a|am|i|ir|o)|colo(?:que|quem|ca|car)|insir(?:a|am|o)'
        r'|inser(?:e|ir)|ponha|p[oõ]e|vincul(?:e|a|ar)'
        r'|remov(?:a|am|e|em|er|o)|retir(?:e|em|a|ar|o)|tir(?:e|em|a|ar|o)'
        r'|exclu(?:a|am|i|ir|o)|apag(?:ue|uem|a|ar|o)|elimin(?:e|em|a|ar|o)'
        r'|desvincul(?:e|a|ar)|delet(?:e|a|ar)'
    )
    _PART_SEPARATOR: ClassVar[re.Pattern[str]] = re.compile(
        r'([?;.!\n]+|\be também\b|\balém disso\b'
        rf'|\be\s+(?=(?:{_ACTION_VERB})\b))',
        re.IGNORECASE,
    )
    _MARKDOWN_SPECIALS: ClassVar[re.Pattern[str]] = re.compile(
        r'([\\`*_{}\[\]()#+!<>|~])'
    )

    def __init__(
        self,
        catalog_provider: MentorCatalogProvider,
        goal_destinations_provider: MentorGoalDestinationsProvider,
        route_provider: MentorRouteProvider,
    ) -> None:
        self._catalog_provider: MentorCatalogProvider = catalog_provider
        self._goal_destinations_provider: MentorGoalDestinationsProvider = (
            goal_destinations_provider
        )
        self._route_provider: MentorRouteProvider = route_provider

    @classmethod
    def is_action_intent(cls, intent: MentorIntent | None) -> bool:
        return intent in cls._ACTION_INTENTS

    def plan(
        self,
        account_id: str,
        content: str,
        context: MentorContextSnapshot,
        hint_goal_id: str | None,
        route: MentorRouteResult,
        assert_access: Callable[[], None],
    ) -> MentorActionPlan | None:
        """Return the action answer, or ``None`` when the message has no action intent."""
        requests = self._requests(content, context, route)
        if not requests:
            return None
        first = requests[0]
        plan = self._plan_first(account_id, first, context, hint_goal_id, assert_access)
        if plan.draft is None or len(requests) == 1:
            return plan
        return MentorActionPlan(
            blocks=(
                *plan.blocks,
                self._block(self.REPEAT_BLOCK_KEY, self.REPEAT_TEXT, None),
            ),
            draft=plan.draft,
        )

    def _plan_first(
        self,
        account_id: str,
        request: _ActionRequest,
        context: MentorContextSnapshot,
        hint_goal_id: str | None,
        assert_access: Callable[[], None],
    ) -> MentorActionPlan:
        assert_access()
        skill, suggestions = self._resolve_skill(
            account_id, request.part, context.eligible_references
        )
        if skill is None:
            return self._text(
                self._unresolved_skill_text(suggestions),
            )
        assert_access()
        goals = self._goal_destinations_provider.read(account_id, skill.skill_id).goals
        if request.kind is MentorActionKind.ADD_SKILL:
            return self._plan_addition(skill, goals, request.part, hint_goal_id)
        return self._plan_removal(skill, goals, request.part, hint_goal_id)

    def _plan_addition(
        self,
        skill: MentorCatalogEntry,
        goals: tuple[MentorGoalDestination, ...],
        part: str,
        hint_goal_id: str | None,
    ) -> MentorActionPlan:
        if not goals:
            return self._text(self.NO_GOALS_TEXT)
        fixed = self._fixed_destination(goals, part, hint_goal_id)
        justification = self._justification(skill)
        if fixed is not None:
            if fixed.skill_experience_id is not None:
                return self._text(
                    f'{self._escape(skill.title)} já está no Objetivo '
                    f'{self._escape(fixed.title)}. '
                    f'[Ver Habilidade](/learning/goals/{fixed.goal_id}/skills/{skill.skill_id}).'
                )
            return self._proposal(
                MentorActionProposalDraft(
                    kind=MentorActionKind.ADD_SKILL,
                    skill_id=skill.skill_id,
                    skill_name=skill.title,
                    goal_id=fixed.goal_id,
                    goal_title=fixed.title,
                    skill_experience_id=None,
                    candidate_goals=(),
                    justification=justification,
                )
            )
        if all(goal.skill_experience_id is not None for goal in goals):
            return self._text(
                f'{self._escape(skill.title)} já está em todos os seus Objetivos.'
            )
        return self._proposal(
            MentorActionProposalDraft(
                kind=MentorActionKind.ADD_SKILL,
                skill_id=skill.skill_id,
                skill_name=skill.title,
                goal_id=None,
                goal_title=None,
                skill_experience_id=None,
                candidate_goals=tuple(
                    MentorActionCandidateGoal(
                        goal_id=goal.goal_id,
                        title=goal.title,
                        contains_skill=goal.skill_experience_id is not None,
                        skill_experience_id=goal.skill_experience_id,
                    )
                    for goal in goals
                ),
                justification=justification,
            )
        )

    def _plan_removal(
        self,
        skill: MentorCatalogEntry,
        goals: tuple[MentorGoalDestination, ...],
        part: str,
        hint_goal_id: str | None,
    ) -> MentorActionPlan:
        holders = tuple(goal for goal in goals if goal.skill_experience_id is not None)
        if not holders:
            return self._text(
                f'{self._escape(skill.title)} não está em nenhum dos seus Objetivos.'
            )
        named = self._named_goals(goals, part)
        if len(named) == 1:
            fixed: MentorGoalDestination | None = named[0]
            if fixed.skill_experience_id is None:
                return self._text(
                    f'{self._escape(skill.title)} não está no Objetivo '
                    f'{self._escape(fixed.title)}.'
                )
        else:
            fixed = self._hinted_or_only(goals, hint_goal_id)
            if fixed is not None and fixed.skill_experience_id is None:
                # A context hint is weaker than a request: use the Objectives that hold it.
                fixed = None
        if fixed is None and len(holders) == 1:
            fixed = holders[0]
        if fixed is not None:
            return self._proposal(
                MentorActionProposalDraft(
                    kind=MentorActionKind.REMOVE_SKILL,
                    skill_id=skill.skill_id,
                    skill_name=skill.title,
                    goal_id=fixed.goal_id,
                    goal_title=fixed.title,
                    skill_experience_id=fixed.skill_experience_id,
                    candidate_goals=(),
                    justification=None,
                )
            )
        return self._proposal(
            MentorActionProposalDraft(
                kind=MentorActionKind.REMOVE_SKILL,
                skill_id=skill.skill_id,
                skill_name=skill.title,
                goal_id=None,
                goal_title=None,
                skill_experience_id=None,
                candidate_goals=tuple(
                    MentorActionCandidateGoal(
                        goal_id=goal.goal_id,
                        title=goal.title,
                        contains_skill=True,
                        skill_experience_id=goal.skill_experience_id,
                    )
                    for goal in holders
                ),
                justification=None,
            )
        )

    def _requests(
        self, content: str, context: MentorContextSnapshot, route: MentorRouteResult
    ) -> list[_ActionRequest]:
        """Action requests in message order; one part per request when it can be told."""
        kinds = self._kinds(route)
        if not kinds:
            return []
        parts = self._parts(content)
        if len(parts) <= 1:
            text = parts[0][0] if parts else content
            return [_ActionRequest(kind, text) for kind in kinds]
        found = [
            _ActionRequest(kind, part)
            for part, asked in parts
            # The route provider vetoes a question, so keep the mark it saw originally.
            for kind in self._kinds(
                self._route_provider.route(f'{part}?' if asked else part, context)
            )
        ]
        return found or [_ActionRequest(kind, content) for kind in kinds]

    @classmethod
    def _kinds(cls, route: MentorRouteResult) -> list[MentorActionKind]:
        return list(
            dict.fromkeys(
                cls._ACTION_INTENTS[match.intent]
                for match in route.intents
                if match.intent in cls._ACTION_INTENTS
            )
        )

    @classmethod
    def _parts(cls, content: str) -> list[tuple[str, bool]]:
        """Parts of the message with whether each one ended in a question mark."""
        chunks = cls._PART_SEPARATOR.split(content)
        return [
            (
                chunks[index].strip(),
                index + 1 < len(chunks) and '?' in chunks[index + 1],
            )
            for index in range(0, len(chunks), 2)
            if chunks[index].strip()
        ]

    def _resolve_skill(
        self, account_id: str, part: str, eligible_references: tuple[str, ...]
    ) -> tuple[MentorCatalogEntry | None, tuple[str, ...]]:
        """The one Skill the part names, else the names to suggest (maybe none)."""
        skills = [
            entry
            for entry in self._catalog_provider.search(
                account_id, part, eligible_references
            )
            if entry.kind == 'skill'
        ]
        named = self._maximal_titles(
            [entry for entry in skills if self._contains_title(part, entry.title)],
            lambda entry: entry.title,
        )
        if len(named) == 1:
            return named[0], ()
        if len(named) > 1:
            return None, self._names(named)
        # The search matches any word of the title or description, so a result is
        # only trusted when the message really names it (or is ambiguous between
        # Skills that share a word with it).
        words = self._content_words(part)
        related = [
            entry
            for entry in skills
            if self._content_words(entry.title).intersection(words)
        ]
        if len(skills) == 1 or len(related) == 1:
            [candidate] = related if len(related) == 1 else skills
            title_words = self._content_words(candidate.title)
            if title_words and title_words <= words:
                return candidate, ()
            return None, ()
        return None, self._names(related)

    def _names(self, entries: list[MentorCatalogEntry]) -> tuple[str, ...]:
        names = tuple(dict.fromkeys(entry.title for entry in entries))
        return names[: self.MAX_SUGGESTED_SKILLS]

    @classmethod
    def _content_words(cls, text: str) -> frozenset[str]:
        """Accent-folded words of ``text`` without stopwords and tiny tokens."""
        return frozenset(
            word
            for word in re.findall(r'\w+', cls._normalize(text))
            if len(word) >= cls.MIN_CONTENT_WORD_LENGTH and word not in cls._STOPWORDS
        )

    def _unresolved_skill_text(self, names: tuple[str, ...]) -> str:
        if not names:
            return self.SKILL_NOT_FOUND_TEXT
        listed = ', '.join(self._escape(name) for name in names)
        return f'Encontrei mais de uma Habilidade parecida: {listed}. Qual delas você quer?'

    def _fixed_destination(
        self,
        goals: tuple[MentorGoalDestination, ...],
        part: str,
        hint_goal_id: str | None,
    ) -> MentorGoalDestination | None:
        """RF-02: by one title in the message, else by the context hint, else the only one."""
        named = self._named_goals(goals, part)
        if len(named) == 1:
            return named[0]
        return self._hinted_or_only(goals, hint_goal_id)

    @staticmethod
    def _hinted_or_only(
        goals: tuple[MentorGoalDestination, ...], hint_goal_id: str | None
    ) -> MentorGoalDestination | None:
        hinted = next((goal for goal in goals if goal.goal_id == hint_goal_id), None)
        if hinted is not None:
            return hinted
        return goals[0] if len(goals) == 1 else None

    def _named_goals(
        self, goals: tuple[MentorGoalDestination, ...], part: str
    ) -> list[MentorGoalDestination]:
        return self._maximal_titles(
            [goal for goal in goals if self._contains_title(part, goal.title)],
            lambda goal: goal.title,
        )

    @classmethod
    def _maximal_titles[Item](
        cls, items: list[Item], title: Callable[[Item], str]
    ) -> list[Item]:
        """Drop items whose title is only a fragment of another matched title."""
        normalized = [cls._normalize(title(item)) for item in items]
        return [
            item
            for item, value in zip(items, normalized, strict=True)
            if not any(other != value and value in other for other in normalized)
        ]

    @classmethod
    def _justification(cls, skill: MentorCatalogEntry) -> str:
        description = (skill.description or '').strip()
        text = (
            f'{cls.JUSTIFICATION_PREFIX} {description}'
            if description
            else (cls.JUSTIFICATION_PREFIX)
        )
        return text[: cls.MAX_JUSTIFICATION_CODE_POINTS].rstrip()

    def _proposal(self, draft: MentorActionProposalDraft) -> MentorActionPlan:
        return MentorActionPlan(
            blocks=(
                self._block(
                    self.PROPOSAL_BLOCK_KEY,
                    self.PROPOSAL_TEXT,
                    MentorIntent(draft.kind.value),
                ),
            ),
            draft=draft,
        )

    def _text(self, content: str) -> MentorActionPlan:
        return MentorActionPlan(
            blocks=(self._block(self.TEXT_BLOCK_KEY, content, None),), draft=None
        )

    @staticmethod
    def _block(
        key: str, content: str, intent: MentorIntent | None
    ) -> MentorResponseBlock:
        # Ordinals are assigned by the use case, which owns the answer's order.
        return MentorResponseBlock(
            block_key=key, ordinal=0, intent=intent, content=content
        )

    @classmethod
    def _escape(cls, text: str) -> str:
        return cls._MARKDOWN_SPECIALS.sub(r'\\\1', text)

    @staticmethod
    def _normalize(value: str) -> str:
        decomposed = unicodedata.normalize('NFKD', value.casefold())
        return ' '.join(
            ''.join(
                char for char in decomposed if not unicodedata.combining(char)
            ).split()
        )

    @classmethod
    def _contains_title(cls, content: str, title: str) -> bool:
        normalized_title = cls._normalize(title)
        return bool(
            normalized_title
            and re.search(
                r'(?<!\w)' + re.escape(normalized_title) + r'(?!\w)',
                cls._normalize(content),
            )
        )
