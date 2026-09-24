"""Pure, versioned Learning policy. Curriculum data enters as immutable inputs."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import ClassVar

from shifu.learning.core.domain.enums import (
    ActivityDifficulty,
    CompetencyProgressStatus,
)
from shifu.learning.core.domain.structures.adaptive_activity import AdaptiveActivity
from shifu.learning.core.domain.structures.adaptive_competency_memory import (
    AdaptiveCompetencyMemory,
)
from shifu.learning.core.domain.structures.adaptive_competency_state import (
    AdaptiveCompetencyState,
)
from shifu.learning.core.domain.structures.adaptive_concept import AdaptiveConcept
from shifu.learning.core.domain.structures.adaptive_concept_state import (
    AdaptiveConceptState,
)
from shifu.learning.core.domain.structures.adaptive_material import AdaptiveMaterial
from shifu.learning.core.domain.structures.adaptive_policy_result import (
    AdaptivePolicyResult,
)
from shifu.learning.core.domain.structures.adaptive_recommendation import (
    AdaptiveRecommendation,
)
from shifu.learning.core.domain.structures.concept_observation import (
    ConceptObservation,
)

_DIFFICULTIES = (
    ActivityDifficulty.EASY,
    ActivityDifficulty.MEDIUM,
    ActivityDifficulty.HARD,
)
_SEVENTY = Decimal('70')
_EIGHTY = Decimal('80')
_EIGHTY_FIVE = Decimal('85')


class AdaptiveLearningPolicy:
    """Reconstruct v2 state and next action from accepted evidence and catalog."""

    policy_id: ClassVar[str] = 'learning-adaptive-v2'

    def evaluate(
        self,
        *,
        concepts: tuple[AdaptiveConcept, ...],
        competency_ids: tuple[str, ...],
        activities: tuple[AdaptiveActivity, ...],
        materials: tuple[AdaptiveMaterial, ...],
        observations: tuple[ConceptObservation, ...],
        memories: tuple[AdaptiveCompetencyMemory, ...] = (),
        previous_target_id: str | None = None,
        pending_evaluation: bool = False,
        now: datetime,
    ) -> AdaptivePolicyResult:
        concept_by_id = {concept.id: concept for concept in concepts}
        memory_by_id = {memory.competency_id: memory for memory in memories}
        states = {
            concept.id: self._concept_state(concept.id, observations)
            for concept in concepts
        }
        competency_states = tuple(
            self._competency_state(
                competency_id,
                tuple(
                    concept
                    for concept in concepts
                    if concept.competency_id == competency_id
                ),
                states,
                observations,
                memory_by_id.get(competency_id),
                now,
            )
            for competency_id in competency_ids
        )
        released = self._release(competency_states)
        focus = next(
            (
                state.competency_id
                for state in released
                if state.status is not CompetencyProgressStatus.MASTERED
                or state.verification_cause is not None
            ),
            None,
        )
        recommendation = None
        if focus is not None and not pending_evaluation:
            recommendation = self._recommend(
                focus,
                concept_by_id,
                states,
                {state.competency_id: state for state in released},
                activities,
                materials,
                observations,
                previous_target_id,
            )
        return AdaptivePolicyResult(
            concept_states=tuple(states[concept.id] for concept in concepts),
            competency_states=released,
            focus_competency_id=focus,
            recommendation=recommendation,
        )

    def _concept_state(
        self,
        concept_id: str,
        observations: tuple[ConceptObservation, ...],
    ) -> AdaptiveConceptState:
        items = tuple(
            sorted(
                (item for item in observations if item.concept_id == concept_id),
                key=lambda item: (item.completed_at, item.attempt_id),
            )
        )
        latest_valid: dict[str, ConceptObservation] = {}
        latest_inconclusive: ConceptObservation | None = None
        for item in items:
            if item.value is None:
                latest_inconclusive = item
            else:
                latest_valid[item.activity_id] = item
                latest_inconclusive = None
        current = tuple(latest_valid.values())
        diagnostic = tuple(item for item in current if item.diagnostic)
        by_difficulty = {
            difficulty: tuple(
                item.value
                for item in diagnostic
                if item.difficulty is difficulty and item.value is not None
            )
            for difficulty in _DIFFICULTIES
        }
        difficulty_means = tuple(
            sum(values, Decimal('0')) / Decimal(len(values))
            for values in by_difficulty.values()
            if values
        )
        baseline = (
            sum(difficulty_means, Decimal('0')) / Decimal(len(difficulty_means))
            if difficulty_means
            else None
        )
        learning = tuple(
            sorted(
                (item for item in current if not item.diagnostic),
                key=lambda item: (item.first_submitted_at, item.activity_id),
            )
        )
        progress = baseline
        for item in learning:
            value = item.value
            if value is None:
                continue
            progress = (
                value
                if progress is None
                else progress * Decimal('0.7') + value * Decimal('0.3')
            )
        inconclusive_ids: list[str] = []
        for item in reversed(items):
            if item.value is not None:
                break
            if item.activity_id not in inconclusive_ids:
                inconclusive_ids.append(item.activity_id)
        return AdaptiveConceptState(
            concept_id=concept_id,
            initial_progress=baseline,
            progress=progress,
            observed_difficulties=frozenset(item.difficulty for item in current),
            distinct_activity_ids=frozenset(item.activity_id for item in current),
            hard_confirmation=any(
                item.difficulty is ActivityDifficulty.HARD
                and item.value is not None
                and item.value >= _EIGHTY
                for item in current
            ),
            evidence_verification=latest_inconclusive is not None,
            inconclusive_activity_ids=tuple(reversed(inconclusive_ids)),
            current_contributions=tuple(
                (item.activity_id, item.value)
                for item in learning
                if item.value is not None
            ),
        )

    def _competency_state(
        self,
        competency_id: str,
        concepts: tuple[AdaptiveConcept, ...],
        states: dict[str, AdaptiveConceptState],
        observations: tuple[ConceptObservation, ...],
        memory: AdaptiveCompetencyMemory | None,
        now: datetime,
    ) -> AdaptiveCompetencyState:
        concept_states = tuple(states[concept.id] for concept in concepts)
        known = tuple(
            state.progress for state in concept_states if state.progress is not None
        )
        partial = sum(known, Decimal('0')) / Decimal(len(known)) if known else None
        complete = bool(concept_states) and all(
            state.progress is not None and state.coverage_complete
            for state in concept_states
        )
        progress = partial if complete else None
        evidence_pending = next(
            (
                state.concept_id
                for state in concept_states
                if state.evidence_verification
            ),
            None,
        )
        acquired_at = memory.mastered_at if memory else None
        causes = self._active_regression_causes(
            concepts, concept_states, observations, acquired_at, partial
        )
        cause, cause_concept = causes[0] if causes else (None, None)
        lost = bool(
            acquired_at is not None
            and any(
                self._regression_confirmed(
                    active_cause, active_concept, concepts, observations, acquired_at
                )
                for active_cause, active_concept in causes
            )
        )
        entry = bool(
            complete
            and progress is not None
            and progress >= _EIGHTY_FIVE
            and evidence_pending is None
            and all(
                state.progress is not None
                and state.progress >= _SEVENTY
                and len(state.distinct_activity_ids) >= 2
                and state.hard_confirmation
                for state in concept_states
            )
        )
        mastered_at = None if lost else acquired_at or (now if entry else None)
        status = (
            CompetencyProgressStatus.MASTERED
            if mastered_at is not None
            else CompetencyProgressStatus.PROFICIENT
            if partial is not None and partial >= _SEVENTY
            else CompetencyProgressStatus.DEVELOPING
            if partial is not None and partial >= Decimal('40')
            else CompetencyProgressStatus.LEARNING
        )
        verification_cause = (
            'evidence'
            if evidence_pending is not None
            else cause
            if mastered_at
            else None
        )
        return AdaptiveCompetencyState(
            competency_id=competency_id,
            progress=progress,
            partial_progress=partial,
            coverage_complete=complete,
            status=status,
            mastered_at=mastered_at,
            verification_cause=verification_cause,
            verification_concept_id=(
                evidence_pending
                if evidence_pending is not None
                else cause_concept
                if mastered_at is not None
                else None
            ),
            content_released=bool(memory and memory.content_released),
        )

    def _active_regression_causes(
        self,
        concepts: tuple[AdaptiveConcept, ...],
        states: tuple[AdaptiveConceptState, ...],
        observations: tuple[ConceptObservation, ...],
        acquired_at: datetime | None,
        mean: Decimal | None,
    ) -> tuple[tuple[str, str | None], ...]:
        if acquired_at is None:
            return ()
        causes: list[tuple[str, str | None]] = []
        for state in states:
            if state.progress is not None and state.progress < Decimal('60'):
                causes.append(('concept', state.concept_id))
        if mean is not None and mean < Decimal('75'):
            causes.append(('mean', None))
        for state in states:
            if not state.hard_confirmation:
                causes.append(('hard', state.concept_id))
        return tuple(causes)

    def _regression_confirmed(
        self,
        cause: str,
        concept_id: str | None,
        concepts: tuple[AdaptiveConcept, ...],
        observations: tuple[ConceptObservation, ...],
        acquired_at: datetime,
    ) -> bool:
        relevant = tuple(
            sorted(
                (
                    item
                    for item in observations
                    if item.completed_at > acquired_at
                    and item.value is not None
                    and not item.diagnostic
                    and (cause == 'mean' or item.concept_id == concept_id)
                    and (cause != 'hard' or item.difficulty is ActivityDifficulty.HARD)
                ),
                key=lambda item: (item.completed_at, item.attempt_id),
            )
        )
        confirmations: set[str] = set()
        for item in relevant:
            prefix = tuple(
                observation
                for observation in observations
                if observation.completed_at <= item.completed_at
            )
            states = tuple(
                self._concept_state(concept.id, prefix) for concept in concepts
            )
            known = tuple(
                state.progress for state in states if state.progress is not None
            )
            mean = sum(known, Decimal('0')) / Decimal(len(known)) if known else None
            current_causes = self._active_regression_causes(
                concepts, states, prefix, acquired_at, mean
            )
            if (cause, concept_id) in current_causes:
                confirmations.add(item.activity_id)
                if len(confirmations) >= 2:
                    return True
            else:
                confirmations.clear()
        return False

    def _release(
        self,
        states: tuple[AdaptiveCompetencyState, ...],
    ) -> tuple[AdaptiveCompetencyState, ...]:
        result: list[AdaptiveCompetencyState] = []
        previous_stable = True
        for state in states:
            released = state.content_released or previous_stable
            result.append(
                AdaptiveCompetencyState(
                    competency_id=state.competency_id,
                    progress=state.progress,
                    partial_progress=state.partial_progress,
                    coverage_complete=state.coverage_complete,
                    status=state.status,
                    mastered_at=state.mastered_at,
                    verification_cause=state.verification_cause,
                    verification_concept_id=state.verification_concept_id,
                    content_released=released,
                )
            )
            previous_stable = (
                previous_stable
                and state.status is CompetencyProgressStatus.MASTERED
                and state.verification_cause is None
            )
        return tuple(result)

    def _recommend(
        self,
        focus: str,
        concepts: dict[str, AdaptiveConcept],
        states: dict[str, AdaptiveConceptState],
        competencies: dict[str, AdaptiveCompetencyState],
        activities: tuple[AdaptiveActivity, ...],
        materials: tuple[AdaptiveMaterial, ...],
        observations: tuple[ConceptObservation, ...],
        previous_target_id: str | None,
    ) -> AdaptiveRecommendation | None:
        focus_concepts = tuple(
            concept for concept in concepts.values() if concept.competency_id == focus
        )
        if not focus_concepts:
            return None
        competency = competencies[focus]
        activities = tuple(
            item
            for item in activities
            if item.competency_id in competencies
            and competencies[item.competency_id].content_released
        )
        materials = tuple(
            item
            for item in materials
            if item.competency_id is None
            or (
                item.competency_id in competencies
                and competencies[item.competency_id].content_released
            )
        )
        target, reason = self._target(
            focus_concepts,
            concepts,
            states,
            competency,
            activities,
            observations,
            previous_target_id,
        )
        original = target
        seen: set[str] = set()
        while target.id not in seen:
            seen.add(target.id)
            weak = self._weak_prerequisites(target.prerequisite_ids, concepts, states)
            if not weak:
                break
            target = weak[0]
            reason = 'prerequisite'
        else:
            return AdaptiveRecommendation(
                competency_id=focus,
                target_concept_id=target.id,
                original_target_concept_id=original.id,
                reason=reason,
                difficulty=None,
                activity_id=None,
                gap='prerequisite_cycle',
                recommended_competency_id=target.competency_id,
            )
        preferred = self._preferred_difficulty(states[target.id], observations)
        hard_required = competency.verification_cause == 'hard'
        if hard_required:
            preferred = ActivityDifficulty.HARD
        selected = self._select_activity(
            target.id,
            preferred,
            reason,
            concepts,
            states,
            activities,
            observations,
            hard_required=hard_required,
        )
        while selected is None:
            blocked = tuple(
                item
                for activity in activities
                if target.id in activity.concept_ids
                and activity.available
                and activity.executable_concept_evidence
                for item in self._weak_prerequisites(
                    activity.required_concept_ids, concepts, states
                )
                if item.id not in seen
            )
            if not blocked:
                break
            target = min(
                blocked,
                key=lambda item: (
                    states[item.id].progress is not None,
                    states[item.id].progress or Decimal('0'),
                    item.position,
                    item.id,
                ),
            )
            seen.add(target.id)
            reason = 'prerequisite'
            preferred = self._preferred_difficulty(states[target.id], observations)
            selected = self._select_activity(
                target.id, preferred, reason, concepts, states, activities, observations
            )
        if len(states[target.id].inconclusive_activity_ids) >= 2:
            return AdaptiveRecommendation(
                competency_id=focus,
                target_concept_id=target.id,
                original_target_concept_id=original.id,
                reason='verification',
                difficulty=preferred,
                activity_id=None,
                gap='assessment_unavailable',
                recommended_competency_id=target.competency_id,
            )
        if selected is None:
            return AdaptiveRecommendation(
                competency_id=focus,
                target_concept_id=target.id,
                original_target_concept_id=original.id,
                reason=reason,
                difficulty=preferred,
                activity_id=None,
                gap='curriculum_or_assessment_unavailable',
                recommended_competency_id=target.competency_id,
            )
        material = self._select_material(
            target.id, states[target.id], materials, observations
        )
        return AdaptiveRecommendation(
            competency_id=focus,
            target_concept_id=target.id,
            original_target_concept_id=original.id,
            reason=reason,
            difficulty=selected.difficulty,
            activity_id=selected.id,
            material_id=material.id if material else None,
            recommended_competency_id=selected.competency_id,
            material_competency_id=material.competency_id if material else None,
        )

    def _target(
        self,
        concepts: tuple[AdaptiveConcept, ...],
        all_concepts: dict[str, AdaptiveConcept],
        states: dict[str, AdaptiveConceptState],
        competency: AdaptiveCompetencyState,
        activities: tuple[AdaptiveActivity, ...],
        observations: tuple[ConceptObservation, ...],
        previous_target_id: str | None,
    ) -> tuple[AdaptiveConcept, str]:
        def rank(concept: AdaptiveConcept) -> tuple[int, Decimal, int, str]:
            state = states[concept.id]
            if (
                (
                    competency.verification_cause == 'evidence'
                    and competency.verification_concept_id == concept.id
                )
                or (
                    competency.verification_cause in {'concept', 'hard'}
                    and competency.verification_concept_id == concept.id
                )
                or competency.verification_cause == 'mean'
                or state.evidence_verification
            ):
                priority = 0
            elif (
                state.progress is None
                or not state.coverage_complete
                or len(state.distinct_activity_ids) < 2
            ):
                priority = 1
            elif state.progress < _SEVENTY:
                priority = 2
            elif not state.hard_confirmation:
                priority = 3
            else:
                priority = 4
            return (
                priority,
                state.progress if state.progress is not None else Decimal('-1'),
                concept.position,
                concept.id,
            )

        ordered = sorted(concepts, key=rank)
        best = ordered[0]
        if (
            previous_target_id is not None
            and rank(best)[0] != 4
            and competency.verification_cause != 'mean'
        ):
            prior = next(
                (item for item in ordered if item.id == previous_target_id), None
            )
            if (
                prior is not None
                and rank(prior)[0] == rank(best)[0]
                and self._has_viable_action(
                    prior.id,
                    all_concepts,
                    states,
                    activities,
                    observations,
                    frozenset(),
                )
            ):
                best = prior
        priority = rank(best)[0]
        reason = (
            'verification',
            'coverage',
            'practice',
            'hard_confirmation',
            'consolidation',
        )[priority]
        if (
            competency.verification_cause in {'concept', 'mean', 'hard'}
            and priority == 0
        ):
            reason = 'regression'
        return best, reason

    def _has_viable_action(
        self,
        concept_id: str,
        concepts: dict[str, AdaptiveConcept],
        states: dict[str, AdaptiveConceptState],
        activities: tuple[AdaptiveActivity, ...],
        observations: tuple[ConceptObservation, ...],
        seen: frozenset[str],
    ) -> bool:
        if concept_id in seen or concept_id not in concepts:
            return False
        seen = seen | {concept_id}
        concept = concepts[concept_id]
        weak = self._weak_prerequisites(concept.prerequisite_ids, concepts, states)
        if weak:
            return any(
                self._has_viable_action(
                    item.id, concepts, states, activities, observations, seen
                )
                for item in weak
            )
        preferred = self._preferred_difficulty(states[concept_id], observations)
        if (
            self._select_activity(
                concept_id,
                preferred,
                'practice',
                concepts,
                states,
                activities,
                observations,
            )
            is not None
        ):
            return True
        return any(
            self._has_viable_action(
                required.id, concepts, states, activities, observations, seen
            )
            for activity in activities
            if concept_id in activity.concept_ids
            and activity.available
            and activity.executable_concept_evidence
            for required in self._weak_prerequisites(
                activity.required_concept_ids, concepts, states
            )
        )

    def _weak_prerequisites(
        self,
        prerequisite_ids: tuple[str, ...],
        concepts: dict[str, AdaptiveConcept],
        states: dict[str, AdaptiveConceptState],
    ) -> tuple[AdaptiveConcept, ...]:
        candidates = tuple(
            concepts[item_id]
            for item_id in prerequisite_ids
            if item_id in concepts
            and (
                (progress := states[item_id].progress) is None
                or progress < _SEVENTY
                or len(states[item_id].distinct_activity_ids) < 2
                or states[item_id].evidence_verification
            )
        )
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    0
                    if states[item.id].progress is None
                    or states[item.id].evidence_verification
                    else 1,
                    0 if len(states[item.id].distinct_activity_ids) < 2 else 1,
                    states[item.id].progress
                    if states[item.id].progress is not None
                    else Decimal('-1'),
                    item.position,
                    item.id,
                ),
            )
        )

    def _preferred_difficulty(
        self,
        state: AdaptiveConceptState,
        observations: tuple[ConceptObservation, ...],
    ) -> ActivityDifficulty:
        for difficulty in _DIFFICULTIES:
            if difficulty not in state.observed_difficulties:
                return difficulty
        progress = state.progress
        index = (
            0
            if progress is None or progress < Decimal('40')
            else 1
            if progress < _SEVENTY
            else 2
        )
        current = self._current_valid(state.concept_id, observations)
        for level in (ActivityDifficulty.EASY, ActivityDifficulty.MEDIUM):
            if (
                len(
                    {
                        item.activity_id
                        for item in current
                        if item.difficulty is level
                        and item.value is not None
                        and item.value >= _EIGHTY
                    }
                )
                >= 2
            ):
                index = max(index, 1 if level is ActivityDifficulty.EASY else 2)
        return _DIFFICULTIES[index]

    def _current_valid(
        self,
        concept_id: str,
        observations: tuple[ConceptObservation, ...],
    ) -> tuple[ConceptObservation, ...]:
        latest: dict[str, ConceptObservation] = {}
        for item in sorted(
            observations, key=lambda item: (item.completed_at, item.attempt_id)
        ):
            if item.concept_id == concept_id and item.value is not None:
                latest[item.activity_id] = item
        return tuple(latest.values())

    def _select_activity(
        self,
        target_id: str,
        preferred: ActivityDifficulty,
        reason: str,
        concepts: dict[str, AdaptiveConcept],
        states: dict[str, AdaptiveConceptState],
        activities: tuple[AdaptiveActivity, ...],
        observations: tuple[ConceptObservation, ...],
        *,
        hard_required: bool = False,
    ) -> AdaptiveActivity | None:
        current = {
            item.activity_id: item
            for item in self._current_valid(target_id, observations)
        }
        candidates = tuple(
            item
            for item in activities
            if target_id in item.concept_ids
            and item.available
            and item.executable_concept_evidence
            and not self._weak_prerequisites(
                item.required_concept_ids, concepts, states
            )
        )
        if reason == 'hard_confirmation' or hard_required:
            candidates = tuple(
                item
                for item in candidates
                if item.difficulty is ActivityDifficulty.HARD
            )
        latest = max(
            (item for item in observations if item.concept_id == target_id),
            key=lambda item: (item.completed_at, item.attempt_id),
            default=None,
        )

        def rank(
            item: AdaptiveActivity,
        ) -> tuple[int, int, Decimal, Decimal, datetime, int, int, str]:
            contribution = current.get(item.id)
            value = contribution.value if contribution else None
            novel = value is None
            gain = self._potential_gain(target_id, item, observations)
            focus_count = dict(item.question_count_by_concept).get(target_id, 0)
            total_count = sum(count for _, count in item.question_count_by_concept) or 1
            focus_share = Decimal(focus_count) / Decimal(total_count)
            attempts = tuple(
                obs
                for obs in observations
                if obs.activity_id == item.id and obs.concept_id == target_id
            )
            last_time = max(
                (obs.completed_at for obs in attempts),
                default=datetime.min.replace(
                    tzinfo=latest.completed_at.tzinfo if latest else None
                ),
            )
            return (
                0 if novel else 1,
                1 if latest and latest.activity_id == item.id else 0,
                -gain,
                -focus_share,
                last_time,
                len(attempts),
                item.position,
                item.id,
            )

        preferred_candidates = tuple(
            item for item in candidates if item.difficulty is preferred
        )
        useful = tuple(
            item
            for item in preferred_candidates
            if item.id not in current
            or (current[item.id].value or Decimal('0')) < Decimal('100')
        )
        if useful:
            return min(useful, key=rank)
        ordered_levels = _DIFFICULTIES[: _DIFFICULTIES.index(preferred) + 1]
        consolidation = tuple(
            item
            for item in candidates
            if item.difficulty in ordered_levels
            and (
                item.id not in current
                or self._potential_gain(target_id, item, observations) > 0
            )
        )
        return min(consolidation, key=rank) if consolidation else None

    def _potential_gain(
        self,
        concept_id: str,
        activity: AdaptiveActivity,
        observations: tuple[ConceptObservation, ...],
    ) -> Decimal:
        before = self._concept_state(concept_id, observations).progress or Decimal('0')
        latest = tuple(
            item
            for item in observations
            if item.activity_id == activity.id and item.concept_id == concept_id
        )
        first = min((item.first_submitted_at for item in latest), default=None)
        if first is None:
            first = max(
                (item.completed_at for item in observations), default=datetime.min
            ) + timedelta(microseconds=1)
        completed = max(
            (item.completed_at for item in observations), default=first
        ) + timedelta(microseconds=1)
        hypothetical = ConceptObservation(
            attempt_id=f'policy-hypothetical-{activity.id}',
            activity_id=activity.id,
            concept_id=concept_id,
            difficulty=activity.difficulty,
            first_submitted_at=first,
            submitted_at=max((item.submitted_at for item in latest), default=first),
            completed_at=completed,
            question_scores=(Decimal('100'),),
        )
        after = self._concept_state(
            concept_id, (*observations, hypothetical)
        ).progress or Decimal('0')
        return max(after - before, Decimal('0'))

    def _select_material(
        self,
        target_id: str,
        state: AdaptiveConceptState,
        materials: tuple[AdaptiveMaterial, ...],
        observations: tuple[ConceptObservation, ...],
    ) -> AdaptiveMaterial | None:
        current = sorted(
            self._current_valid(target_id, observations),
            key=lambda item: (item.completed_at, item.attempt_id),
        )
        recent = current[-2:]
        two_failures = (
            len(recent) == 2
            and recent[0].activity_id != recent[1].activity_id
            and all(
                item.value is not None and item.value < Decimal('40') for item in recent
            )
        )
        if not (
            not state.distinct_activity_ids
            or (state.progress is not None and state.progress < Decimal('40'))
            or two_failures
        ):
            return None
        candidates = tuple(
            item
            for item in materials
            if item.available and target_id in item.concept_ids
        )
        return min(
            candidates,
            key=lambda item: (len(item.concept_ids), item.position, item.id),
            default=None,
        )
