import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from shifu.fakers.learning.entities import (
    GoalFaker,
    MentorActionReceiptFaker,
    SkillExperienceFaker,
)
from shifu.learning.core.domain.enums import (
    MentorActionOperation,
    MentorActionOutcome,
    MentorActionRejectionReason,
    SkillExperienceStatus,
)
from shifu.learning.core.domain.errors import MentorActionConflictError
from shifu.learning.core.domain.events import (
    MentorSkillActionResolvedEvent,
    MentorSkillActionResolvedPayload,
)
from shifu.learning.core.domain.structures import MentorActionResolution
from shifu.learning.core.interfaces import (
    LearningDatabase,
    LearningDatabaseRepositories,
)
from shifu.learning.core.use_cases import AddSkillToGoalFromMentorUseCase
from shifu.shared.core.domain.structures import SkillCatalogEntry
from shifu.shared.core.interfaces import (
    ClockProvider,
    CurriculumCatalogProvider,
    IdentifierProvider,
)

ACCOUNT_ID = 'account-1'
GOAL_ID = 'goal-1'
CONFIRMATION_ID = 'confirmation-1'
SKILL_ID = 'skill-1'
JUSTIFICATION = 'Você pediu ao Mentor para adicionar esta Habilidade.'
NOW = datetime(2026, 10, 23, 12, 30, tzinfo=UTC)
EXPERIENCE_ID = 'experience-new'
RECEIPT_ID = 'receipt-new'


def _fingerprint(
    goal_id: str = GOAL_ID,
    skill_id: str = SKILL_ID,
    justification: str = JUSTIFICATION,
) -> str:
    canonical = json.dumps(
        {
            'operation': 'add_skill',
            'goal_id': goal_id,
            'skill_id': skill_id,
            'justification': justification,
        },
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


class TestAddSkillToGoalFromMentorUseCase:
    def setup_method(self) -> None:
        self.database = create_autospec(LearningDatabase, instance=True)
        self.repositories = create_autospec(
            LearningDatabaseRepositories,
            instance=True,
        )
        self.database.transaction.return_value.__enter__.return_value = (
            self.repositories
        )
        self.goals = self.repositories.goals
        self.experiences = self.repositories.skill_experiences
        self.receipts = self.repositories.mentor_action_receipts
        self.events = self.repositories.events
        self.catalog = create_autospec(CurriculumCatalogProvider, instance=True)
        self.identifiers = create_autospec(IdentifierProvider, instance=True)
        self.clock = create_autospec(ClockProvider, instance=True)
        self.identifiers.generate.side_effect = [EXPERIENCE_ID, RECEIPT_ID]
        self.clock.now.return_value = NOW
        self.goal = GoalFaker.fake(id=GOAL_ID, account_id=ACCOUNT_ID)
        self.goals.find_by_id_for_update.return_value = self.goal
        self.receipts.find_by_confirmation_id.return_value = None
        self.receipts.try_add.return_value = True
        self.experiences.find_by_goal_id_and_skill_id.return_value = None
        self.catalog.find_skill_by_id.return_value = SkillCatalogEntry(
            id=SKILL_ID,
            name='Funções em Python',
            description='Funções, parâmetros e retornos em Python.',
        )
        self.subject = AddSkillToGoalFromMentorUseCase(
            learning_database=self.database,
            curriculum_catalog_provider=self.catalog,
            identifier_provider=self.identifiers,
            clock_provider=self.clock,
        )

    def _execute(
        self,
        *,
        goal_id: str = GOAL_ID,
        skill_id: str = SKILL_ID,
        justification: str = JUSTIFICATION,
    ) -> MentorActionResolution:
        return self.subject.execute(
            ACCOUNT_ID, goal_id, CONFIRMATION_ID, skill_id, justification
        )

    def test_should_add_a_not_started_experience_with_the_justification(self) -> None:
        resolution = self._execute()

        assert resolution == MentorActionResolution(
            confirmation_id=CONFIRMATION_ID,
            operation=MentorActionOperation.ADD_SKILL,
            outcome=MentorActionOutcome.ADDED,
            rejection_reason=None,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            skill_experience_id=EXPERIENCE_ID,
        )
        self.experiences.add.assert_called_once()
        created = self.experiences.add.call_args.args[0]
        assert created.id == EXPERIENCE_ID
        assert created.goal_id == GOAL_ID
        assert created.skill_id == SKILL_ID
        assert created.inclusion_reason == JUSTIFICATION
        assert created.status is SkillExperienceStatus.NOT_STARTED
        assert created.created_at == NOW
        assert created.updated_at == NOW

    def test_should_not_create_foundations_or_competency_progress(self) -> None:
        self._execute()

        self.experiences.add_many.assert_not_called()
        self.repositories.competency_progresses.add.assert_not_called()
        self.repositories.competency_progresses.add_many.assert_not_called()
        self.catalog.find_direct_foundations_for_many.assert_not_called()

    def test_should_store_a_receipt_with_identifiers_and_the_request_fingerprint(
        self,
    ) -> None:
        self._execute()

        self.receipts.try_add.assert_called_once()
        receipt = self.receipts.try_add.call_args.args[0]
        assert receipt.id == RECEIPT_ID
        assert receipt.account_id == ACCOUNT_ID
        assert receipt.confirmation_id == CONFIRMATION_ID
        assert receipt.operation is MentorActionOperation.ADD_SKILL
        assert receipt.goal_id == GOAL_ID
        assert receipt.skill_id == SKILL_ID
        assert receipt.skill_experience_id == EXPERIENCE_ID
        assert receipt.outcome is MentorActionOutcome.ADDED
        assert receipt.rejection_reason is None
        assert receipt.request_fingerprint == _fingerprint()
        assert receipt.resolved_at == NOW

    def test_should_emit_the_resolved_event_once_with_the_complete_payload(
        self,
    ) -> None:
        self._execute()

        self.events.add.assert_called_once_with(
            MentorSkillActionResolvedEvent(
                payload=MentorSkillActionResolvedPayload(
                    account_id=ACCOUNT_ID,
                    confirmation_id=CONFIRMATION_ID,
                    operation='add_skill',
                    outcome='added',
                    rejection_reason=None,
                    goal_id=GOAL_ID,
                    skill_id=SKILL_ID,
                    skill_experience_id=EXPERIENCE_ID,
                    resolved_at='2026-10-23T12:30:00Z',
                )
            )
        )

    def test_should_return_the_existing_experience_when_the_skill_is_present(
        self,
    ) -> None:
        existing = SkillExperienceFaker.fake(goal_id=GOAL_ID, skill_id=SKILL_ID)
        self.experiences.find_by_goal_id_and_skill_id.return_value = existing

        resolution = self._execute()

        assert resolution.outcome is MentorActionOutcome.ALREADY_PRESENT
        assert resolution.rejection_reason is None
        assert resolution.skill_experience_id == existing.id
        self.experiences.add.assert_not_called()
        receipt = self.receipts.try_add.call_args.args[0]
        assert receipt.outcome is MentorActionOutcome.ALREADY_PRESENT
        assert receipt.skill_experience_id == existing.id
        self.events.add.assert_called_once()

    @pytest.mark.parametrize('goal', [None, GoalFaker.fake(account_id='other')])
    def test_should_reject_a_missing_or_foreign_goal_without_revealing_it(
        self,
        goal: object,
    ) -> None:
        self.goals.find_by_id_for_update.return_value = goal

        resolution = self._execute()

        assert resolution.outcome is MentorActionOutcome.REJECTED
        assert (
            resolution.rejection_reason is MentorActionRejectionReason.GOAL_UNAVAILABLE
        )
        assert resolution.goal_id == GOAL_ID
        assert resolution.skill_experience_id is None
        self.catalog.find_skill_by_id.assert_not_called()
        self.experiences.add.assert_not_called()
        self.events.add.assert_called_once()

    def test_should_reject_a_skill_missing_from_the_curriculum(self) -> None:
        self.catalog.find_skill_by_id.return_value = None

        resolution = self._execute()

        assert resolution.outcome is MentorActionOutcome.REJECTED
        assert (
            resolution.rejection_reason is MentorActionRejectionReason.SKILL_UNAVAILABLE
        )
        self.experiences.find_by_goal_id_and_skill_id.assert_not_called()
        self.experiences.add.assert_not_called()
        receipt = self.receipts.try_add.call_args.args[0]
        assert receipt.rejection_reason is MentorActionRejectionReason.SKILL_UNAVAILABLE
        self.events.add.assert_called_once()

    def test_should_check_receipt_then_lock_goal_then_recheck_receipt(self) -> None:
        order: list[str] = []

        def track(step: str, result: object = None) -> Callable[..., object]:
            def record(*_arguments: object) -> object:
                order.append(step)
                return result

            return record

        self.receipts.find_by_confirmation_id.side_effect = track('receipt')
        self.goals.find_by_id_for_update.side_effect = track('lock', result=self.goal)
        self.experiences.add.side_effect = track('effect')
        self.receipts.try_add.side_effect = track('try_add', result=True)
        self.events.add.side_effect = track('event')

        self._execute()

        assert order == ['receipt', 'lock', 'receipt', 'effect', 'try_add', 'event']

    def test_should_return_the_stored_resolution_on_replay_without_events(
        self,
    ) -> None:
        stored = MentorActionReceiptFaker.fake(
            account_id=ACCOUNT_ID,
            confirmation_id=CONFIRMATION_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            skill_experience_id='experience-stored',
            outcome=MentorActionOutcome.ADDED,
            request_fingerprint=_fingerprint(),
        )
        self.receipts.find_by_confirmation_id.return_value = stored

        resolution = self._execute()

        assert resolution.outcome is MentorActionOutcome.ADDED
        assert resolution.skill_experience_id == 'experience-stored'
        self.receipts.find_by_confirmation_id.assert_called_once_with(
            ACCOUNT_ID, CONFIRMATION_ID
        )
        self.goals.find_by_id_for_update.assert_not_called()
        self.experiences.add.assert_not_called()
        self.receipts.try_add.assert_not_called()
        self.events.add.assert_not_called()

    def test_should_return_the_receipt_committed_by_a_concurrent_request_after_locking(
        self,
    ) -> None:
        winner = MentorActionReceiptFaker.fake(
            account_id=ACCOUNT_ID,
            confirmation_id=CONFIRMATION_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            skill_experience_id='experience-winner',
            request_fingerprint=_fingerprint(),
        )
        self.receipts.find_by_confirmation_id.side_effect = [None, winner]

        resolution = self._execute()

        assert resolution.skill_experience_id == 'experience-winner'
        self.goals.find_by_id_for_update.assert_called_once_with(GOAL_ID)
        self.catalog.find_skill_by_id.assert_not_called()
        self.experiences.add.assert_not_called()
        self.receipts.try_add.assert_not_called()
        self.events.add.assert_not_called()

    @pytest.mark.parametrize(
        'changed',
        [
            {'goal_id': 'goal-2'},
            {'skill_id': 'skill-2'},
            {'justification': 'Outra justificativa.'},
        ],
    )
    def test_should_raise_a_conflict_for_a_divergent_payload_under_the_same_id(
        self,
        changed: dict[str, str],
    ) -> None:
        self.receipts.find_by_confirmation_id.return_value = (
            MentorActionReceiptFaker.fake(
                account_id=ACCOUNT_ID,
                confirmation_id=CONFIRMATION_ID,
                request_fingerprint=_fingerprint(),
            )
        )

        with pytest.raises(MentorActionConflictError):
            self._execute(**changed)

        self.experiences.add.assert_not_called()
        self.receipts.try_add.assert_not_called()
        self.events.add.assert_not_called()

    def test_should_return_the_winner_resolution_when_try_add_loses_the_race_for_a_rejection(
        self,
    ) -> None:
        self.goals.find_by_id_for_update.return_value = None
        winner = MentorActionReceiptFaker.fake(
            account_id=ACCOUNT_ID,
            confirmation_id=CONFIRMATION_ID,
            goal_id=GOAL_ID,
            skill_id=SKILL_ID,
            skill_experience_id=None,
            outcome=MentorActionOutcome.REJECTED,
            rejection_reason=MentorActionRejectionReason.GOAL_UNAVAILABLE,
            request_fingerprint=_fingerprint(),
        )
        self.receipts.find_by_confirmation_id.side_effect = [None, None, winner]
        self.receipts.try_add.return_value = False

        resolution = self._execute()

        assert resolution.outcome is MentorActionOutcome.REJECTED
        assert (
            resolution.rejection_reason is MentorActionRejectionReason.GOAL_UNAVAILABLE
        )
        self.events.add.assert_not_called()

    def test_should_raise_a_conflict_when_the_winner_has_another_fingerprint(
        self,
    ) -> None:
        self.goals.find_by_id_for_update.return_value = None
        self.receipts.find_by_confirmation_id.side_effect = [
            None,
            None,
            MentorActionReceiptFaker.fake(
                account_id=ACCOUNT_ID,
                confirmation_id=CONFIRMATION_ID,
                request_fingerprint=_fingerprint(goal_id='goal-2'),
            ),
        ]
        self.receipts.try_add.return_value = False

        with pytest.raises(MentorActionConflictError):
            self._execute()

        self.events.add.assert_not_called()

    def test_should_raise_a_conflict_when_try_add_loses_after_performing_an_effect(
        self,
    ) -> None:
        self.receipts.find_by_confirmation_id.side_effect = [
            None,
            None,
            MentorActionReceiptFaker.fake(
                account_id=ACCOUNT_ID,
                confirmation_id=CONFIRMATION_ID,
                request_fingerprint=_fingerprint(),
            ),
        ]
        self.receipts.try_add.return_value = False

        with pytest.raises(MentorActionConflictError):
            self._execute()

        self.experiences.add.assert_called_once()
        self.events.add.assert_not_called()

    def test_should_raise_a_conflict_when_the_losing_race_has_no_visible_winner(
        self,
    ) -> None:
        self.goals.find_by_id_for_update.return_value = None
        self.receipts.try_add.return_value = False

        with pytest.raises(MentorActionConflictError):
            self._execute()

        self.events.add.assert_not_called()
