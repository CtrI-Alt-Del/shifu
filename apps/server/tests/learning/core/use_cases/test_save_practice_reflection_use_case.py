import pytest

from shifu.fakers.learning.entities import ActivityEvaluationFaker
from shifu.learning.core.domain.errors import InvalidAttemptError
from shifu.learning.core.use_cases import SavePracticeReflectionUseCase
from shifu.shared.core.domain.errors import ConflictError, NotFoundError
from tests.learning.core.use_cases.practice_draft_use_case_setup import (
    PracticeDraftUseCaseSetup,
    fake_draft,
)


class TestSavePracticeReflectionUseCase:
    def setup_method(self) -> None:
        self.setup = PracticeDraftUseCaseSetup()
        self.drafts = self.setup.repositories.practice_drafts
        self.subject = SavePracticeReflectionUseCase(
            self.setup.database, self.setup.curriculum, self.setup.identifiers
        )

    def test_should_create_the_first_draft_with_the_reflection_and_revision_one(
        self,
    ) -> None:
        view = self.subject.execute(*self.setup.scope, 'Usei fogo alto.')

        added = self.drafts.add.call_args.args[0]
        assert (added.id, added.reflection, added.revision) == (
            'generated-1',
            'Usei fogo alto.',
            1,
        )
        assert (view.revision, view.reflection) == (1, 'Usei fogo alto.')
        self.setup.repositories.skill_experiences.find_by_id_for_update.assert_called_once()

    def test_should_keep_the_last_saved_reflection_and_grow_the_revision(self) -> None:
        draft = fake_draft(revision=3)
        draft.reflection = 'Versão do outro aparelho.'
        self.drafts.find_active_for_update.return_value = draft

        view = self.subject.execute(*self.setup.scope, 'Versão mais recente.')

        self.drafts.update.assert_called_once_with(draft)
        self.drafts.add.assert_not_called()
        assert (view.revision, view.reflection) == (4, 'Versão mais recente.')

    def test_should_accept_an_empty_reflection(self) -> None:
        view = self.subject.execute(*self.setup.scope, '')

        assert (view.revision, view.reflection) == (1, '')

    def test_should_reject_a_reflection_over_the_limit_without_saving(self) -> None:
        with pytest.raises(InvalidAttemptError):
            self.subject.execute(*self.setup.scope, 'a' * 4001)

        self.drafts.add.assert_not_called()

    def test_should_refuse_the_write_while_an_evaluation_is_unresolved(self) -> None:
        self.setup.repositories.activity_evaluations.find_unresolved_by_skill_experience_id.return_value = ActivityEvaluationFaker.fake()

        with pytest.raises(ConflictError):
            self.subject.execute(*self.setup.scope, 'Tarde demais.')

        self.drafts.add.assert_not_called()
        self.drafts.update.assert_not_called()

    def test_should_deny_a_missing_experience(self) -> None:
        self.setup.repositories.skill_experiences.find_by_goal_id_and_skill_id.return_value = None

        with pytest.raises(NotFoundError):
            self.subject.execute(*self.setup.scope, 'Texto.')
