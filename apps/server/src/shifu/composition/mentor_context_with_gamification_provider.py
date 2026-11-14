"""Join Gamification's read-only facts to the Learning context the Mentor reads."""

from dataclasses import replace

from shifu.shared.core.domain.errors import ServiceUnavailableError
from shifu.shared.core.domain.structures import MentorContextSnapshot
from shifu.shared.core.interfaces import (
    MentorContextProvider,
    MentorGamificationFactsProvider,
)

_GAMIFICATION = 'gamification'


class MentorContextWithGamificationProvider:
    """Add XP, level, streak and achievements to every Mentor context read.

    Learning still decides the Objective, Habilidade and released content. When
    Gamification cannot be read, the snapshot keeps it listed as unavailable, so
    the Mentor says the data is missing instead of guessing it.
    """

    def __init__(
        self,
        learning: MentorContextProvider,
        gamification: MentorGamificationFactsProvider,
    ) -> None:
        self._learning = learning
        self._gamification = gamification

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
        snapshot = self._learning.read(
            account_id,
            reference_ids,
            goal_id=goal_id,
            skill_id=skill_id,
            competency_id=competency_id,
            material_id=material_id,
            activity_id=activity_id,
        )
        try:
            facts = self._gamification.read(account_id)
        except ServiceUnavailableError:
            return snapshot
        return replace(
            snapshot,
            facts=(*snapshot.facts, *facts),
            unavailable_sources=tuple(
                source
                for source in snapshot.unavailable_sources
                if source != _GAMIFICATION
            ),
        )
