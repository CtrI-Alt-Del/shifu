from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from shifu.intelligence.core.domain.entities import PlanningSession
from shifu.intelligence.core.domain.enums import (
    PlanningIntentKind,
    PlanningOperationKind,
    PlanningQuestionKind,
    PlanningSessionStatus,
)
from shifu.intelligence.core.domain.errors import (
    PlanningAnswersInvalidError,
    PlanningOperationConflictError,
    PlanningStateConflictError,
)
from shifu.intelligence.core.domain.structures import (
    PlanningAnswer,
    PlanningAnsweredBatch,
    PlanningAnsweredQuestion,
    PlanningOperationResult,
    PlanningOption,
    PlanningProposal,
    PlanningProposalDraft,
    PlanningProposalDraftSkill,
    PlanningProposalSkill,
    PlanningQuestion,
    PlanningQuestionBatch,
    PlanningSkillRelation,
)
from shifu.intelligence.core.domain.structures.planning_operation_result import (
    FAILED_MESSAGE,
    OPERATION_TIMEOUT_CODE,
    VALIDATION_EXHAUSTED_CODE,
)

_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
_PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
_NEXT_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAX'


def _question(
    question_id: str = 'q1',
    kind: PlanningQuestionKind = PlanningQuestionKind.SINGLE,
    *,
    unknown: bool = False,
) -> PlanningQuestion:
    options = [
        PlanningOption(id='o1', text='Sites'),
        PlanningOption(id='o2', text='APIs'),
    ]
    if unknown:
        options.append(PlanningOption.unknown())
    return PlanningQuestion(
        id=question_id,
        text='O que você quer construir?',
        kind=kind,
        options=tuple(options),
    )


def _batch(*questions: PlanningQuestion) -> PlanningQuestionBatch:
    return PlanningQuestionBatch(id='batch-1', questions=questions or (_question(),))


def _proposal(*skill_ids: str) -> PlanningProposal:
    return PlanningProposal(
        title='Aprender web',
        description='Do HTML ao React.',
        skills=tuple(
            PlanningProposalSkill(
                skill_id=skill_id, name=f'Skill {skill_id}', justification='Base.'
            )
            for skill_id in (skill_ids or ('skill-a',))
        ),
    )


def _session() -> PlanningSession:
    return PlanningSession.start(
        _PLANNING_ID,
        'account-1',
        'revision-1',
        '  Quero   aprender  web ',
        _OPERATION_ID,
        _NOW,
    )


def _interviewing() -> PlanningSession:
    session = _session()
    assert session.complete(
        _OPERATION_ID, 1, PlanningOperationResult.for_batch(_batch()), _NOW
    )
    return session


class TestPlanningSessionTransitions:
    def test_should_start_processing_with_a_normalized_intent(self) -> None:
        session = _session()

        assert session.intent == 'Quero aprender web'
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.generation == 1
        assert session.version == 0
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.START
        assert session.batch is None
        assert session.answered_batch_count == 0

    @pytest.mark.parametrize('intent', ['', '   ', 'x' * 4001])
    def test_should_reject_a_blank_or_oversized_intent(self, intent: str) -> None:
        with pytest.raises(ValueError, match='intent'):
            PlanningSession.start(
                _PLANNING_ID, 'account-1', 'rev', intent, _OPERATION_ID, _NOW
            )

    def test_should_expose_a_batch_and_accept_a_complete_valid_answer_set(
        self,
    ) -> None:
        session = _interviewing()
        later = _NOW + timedelta(minutes=1)

        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.batch is not None
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o2',)),),
            _NEXT_OPERATION_ID,
            later,
        )

        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.ANSWER
        assert session.operation.id == _NEXT_OPERATION_ID
        assert session.batch is None
        assert session.answered_batch_count == 1
        assert session.answered_batches[0].items[0].selected_texts == ('APIs',)
        assert session.updated_at == later

    @pytest.mark.parametrize(
        ('batch_id', 'answers', 'error'),
        [
            (
                'batch-2',
                (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
                PlanningStateConflictError,
            ),
            ('batch-1', (), PlanningAnswersInvalidError),
            (
                'batch-1',
                (PlanningAnswer(question_id='q9', option_ids=('o1',)),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o9',)),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o1', 'o2')),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=()),),
                PlanningAnswersInvalidError,
            ),
            (
                'batch-1',
                (
                    PlanningAnswer(question_id='q1', option_ids=('o1',)),
                    PlanningAnswer(question_id='q1', option_ids=('o2',)),
                ),
                PlanningAnswersInvalidError,
            ),
        ],
    )
    def test_should_reject_incomplete_or_invalid_answer_sets_without_changing_state(
        self,
        batch_id: str,
        answers: tuple[PlanningAnswer, ...],
        error: type[Exception],
    ) -> None:
        session = _interviewing()

        with pytest.raises(error):
            session.submit_answers(batch_id, answers, _NEXT_OPERATION_ID, _NOW)

        assert session.status is PlanningSessionStatus.INTERVIEW
        assert session.operation is None
        assert session.answered_batch_count == 0

    def test_should_keep_the_unknown_option_exclusive_on_multiple_choice(self) -> None:
        question = _question(kind=PlanningQuestionKind.MULTIPLE, unknown=True)
        session = _session()
        assert session.complete(
            _OPERATION_ID, 1, PlanningOperationResult.for_batch(_batch(question)), _NOW
        )

        with pytest.raises(PlanningAnswersInvalidError, match='Não sei'):
            session.submit_answers(
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('nao-sei', 'o1')),),
                _NEXT_OPERATION_ID,
                _NOW,
            )
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1', 'o2')),),
            _NEXT_OPERATION_ID,
            _NOW,
        )

        assert session.answered_batches[0].items[0].selected_texts == ('Sites', 'APIs')

    def test_should_refuse_answers_restart_and_retry_while_an_operation_runs(
        self,
    ) -> None:
        session = _session()

        with pytest.raises(PlanningOperationConflictError):
            session.submit_answers('batch-1', (), _NEXT_OPERATION_ID, _NOW)
        with pytest.raises(PlanningOperationConflictError):
            session.restart('Outra intenção', 'rev', _NEXT_OPERATION_ID, _NOW)
        with pytest.raises(PlanningOperationConflictError):
            session.retry(_NEXT_OPERATION_ID, _NOW)
        assert session.operation is not None
        assert session.operation.id == _OPERATION_ID

    def test_should_refuse_answers_outside_the_interview(self) -> None:
        session = _session()
        assert session.complete(
            _OPERATION_ID, 1, PlanningOperationResult.for_proposal(_proposal()), _NOW
        )

        with pytest.raises(PlanningStateConflictError):
            session.submit_answers(
                'batch-1',
                (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
                _NEXT_OPERATION_ID,
                _NOW,
            )

    def test_should_restart_into_a_new_generation_and_discard_the_context(self) -> None:
        session = _interviewing()
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            _NEXT_OPERATION_ID,
            _NOW,
        )
        assert session.complete(
            _NEXT_OPERATION_ID,
            1,
            PlanningOperationResult.for_proposal(
                _proposal(), classification=PlanningIntentKind.LEARNING
            ),
            _NOW,
        )

        session.restart('  Agora quero APIs ', 'revision-2', 'op-3', _NOW)

        assert session.generation == 2
        assert session.intent == 'Agora quero APIs'
        assert session.access_revision == 'revision-2'
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.RESTART
        assert session.answered_batches == ()
        assert session.proposal is None
        assert session.classification is None
        assert session.consulted_curriculum is False

    @pytest.mark.parametrize(
        'result',
        [
            PlanningOperationResult.failed(),
            PlanningOperationResult.validation_failed(),
        ],
    )
    def test_should_retry_only_after_a_failure_and_keep_the_context(
        self, result: PlanningOperationResult
    ) -> None:
        session = _interviewing()
        session.submit_answers(
            'batch-1',
            (PlanningAnswer(question_id='q1', option_ids=('o1',)),),
            _NEXT_OPERATION_ID,
            _NOW,
        )
        assert session.complete(_NEXT_OPERATION_ID, 1, result, _NOW)
        assert session.message is not None
        assert session.failure_code is not None

        session.retry('op-3', _NOW)

        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None
        assert session.operation.kind is PlanningOperationKind.RETRY
        assert session.answered_batch_count == 1
        assert session.message is None
        assert session.failure_code is None

    def test_should_refuse_a_retry_without_a_failure(self) -> None:
        session = _interviewing()

        with pytest.raises(PlanningStateConflictError):
            session.retry(_NEXT_OPERATION_ID, _NOW)

    def test_should_expire_only_a_processing_operation_older_than_the_timeout(
        self,
    ) -> None:
        session = _session()
        timeout = timedelta(minutes=3)

        assert not session.expire_operation(_NOW + timedelta(minutes=2), timeout)
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.expire_operation(_NOW + timeout, timeout)
        assert session.status is PlanningSessionStatus.FAILED
        assert session.failure_code == OPERATION_TIMEOUT_CODE
        assert session.message == FAILED_MESSAGE
        assert session.operation is None
        assert not session.expire_operation(_NOW + timedelta(hours=1), timeout)

    @pytest.mark.parametrize(
        ('operation_id', 'generation'),
        [(_NEXT_OPERATION_ID, 1), (_OPERATION_ID, 2)],
    )
    def test_should_discard_results_that_miss_the_operation_or_generation_fence(
        self, operation_id: str, generation: int
    ) -> None:
        session = _session()

        assert not session.complete(
            operation_id, generation, PlanningOperationResult.for_batch(_batch()), _NOW
        )
        assert session.status is PlanningSessionStatus.PROCESSING
        assert session.operation is not None

    def test_should_discard_a_second_result_for_the_same_operation(self) -> None:
        session = _session()
        assert session.complete(
            _OPERATION_ID, 1, PlanningOperationResult.for_batch(_batch()), _NOW
        )

        assert not session.complete(
            _OPERATION_ID, 1, PlanningOperationResult.for_proposal(_proposal()), _NOW
        )
        assert session.status is PlanningSessionStatus.INTERVIEW

    @pytest.mark.parametrize(
        ('result', 'status', 'failure_code'),
        [
            (
                PlanningOperationResult.out_of_scope(
                    classification=PlanningIntentKind.OUT_OF_SCOPE
                ),
                PlanningSessionStatus.OUT_OF_SCOPE,
                None,
            ),
            (
                PlanningOperationResult.unsupported(),
                PlanningSessionStatus.UNSUPPORTED,
                None,
            ),
            (
                PlanningOperationResult.validation_failed(),
                PlanningSessionStatus.VALIDATION_FAILED,
                VALIDATION_EXHAUSTED_CODE,
            ),
            (
                PlanningOperationResult.failed(),
                PlanningSessionStatus.FAILED,
                'service_unavailable',
            ),
        ],
    )
    def test_should_expose_distinguishable_outcomes_with_a_learner_message(
        self,
        result: PlanningOperationResult,
        status: PlanningSessionStatus,
        failure_code: str | None,
    ) -> None:
        session = _session()

        assert session.complete(_OPERATION_ID, 1, result, _NOW)
        assert session.status is status
        assert session.message
        assert session.failure_code == failure_code
        assert session.operation is None
        assert session.batch is None
        assert session.proposal is None


class TestPlanningStructures:
    @pytest.mark.parametrize(
        'build',
        [
            lambda: PlanningOption(id='', text='x'),
            lambda: PlanningQuestion(
                id='q',
                text='t',
                kind=PlanningQuestionKind.SINGLE,
                options=(PlanningOption(id='a', text='A'),),
            ),
            lambda: PlanningQuestion(
                id='q',
                text='t',
                kind=PlanningQuestionKind.SINGLE,
                options=tuple(
                    PlanningOption(id=f'o{i}', text=f'T{i}') for i in range(7)
                ),
            ),
            lambda: PlanningQuestion(
                id='q',
                text='t',
                kind=PlanningQuestionKind.SINGLE,
                options=(
                    PlanningOption(id='a', text='A'),
                    PlanningOption(id='b', text='a'),
                ),
            ),
            lambda: PlanningQuestion(
                id='q',
                text='t',
                kind=PlanningQuestionKind.SINGLE,
                options=(
                    PlanningOption(id='a', text='A'),
                    PlanningOption(id='b', text='B'),
                    PlanningOption.unknown(),
                    PlanningOption(id='c', text='C', exclusive=True),
                ),
            ),
            lambda: PlanningQuestionBatch(id='b', questions=()),
            lambda: PlanningQuestionBatch(
                id='b', questions=tuple(_question(f'q{i}') for i in range(5))
            ),
            lambda: PlanningQuestionBatch(
                id='b', questions=(_question('q1'), _question('q1'))
            ),
            lambda: PlanningAnsweredBatch(batch_id='b', items=()),
            lambda: PlanningAnsweredBatch(
                batch_id='b',
                items=(
                    PlanningAnsweredQuestion(question=_question(), option_ids=('o1',)),
                    PlanningAnsweredQuestion(question=_question(), option_ids=('o2',)),
                ),
            ),
            lambda: PlanningProposal(
                title='',
                description='d',
                skills=(
                    PlanningProposalSkill(skill_id='a', name='A', justification='j'),
                ),
            ),
            lambda: PlanningProposal(title='t', description='d', skills=()),
            lambda: _proposal('a', 'a'),
            lambda: PlanningProposal(
                title='t',
                description='d',
                skills=(
                    PlanningProposalSkill(skill_id='a', name='A', justification='j'),
                ),
                relations=(
                    PlanningSkillRelation(skill_id='a', foundation_skill_id='z'),
                ),
            ),
            lambda: PlanningSkillRelation(skill_id='a', foundation_skill_id='a'),
            lambda: PlanningOperationResult.for_batch(
                _batch(), classification=None
            ).__class__(kind=PlanningOperationResult.for_batch(_batch()).kind),
            lambda: PlanningOperationResult(
                kind=PlanningOperationResult.failed().kind, message='m'
            ),
        ],
    )
    def test_should_reject_invalid_planning_structures(
        self, build: Callable[[], object]
    ) -> None:
        with pytest.raises(ValueError, match=r'.'):
            build()

    def test_should_list_every_draft_problem_in_portuguese(self) -> None:
        candidates = {'skill-a': 'APIs web', 'skill-b': 'React'}
        draft = PlanningProposalDraft(
            title=' ',
            description='',
            skills=(
                PlanningProposalDraftSkill(skill_id='skill-a', justification='ok'),
                PlanningProposalDraftSkill(skill_id='skill-a', justification='ok'),
                PlanningProposalDraftSkill(skill_id='skill-z', justification='ok'),
                PlanningProposalDraftSkill(skill_id='skill-b', justification=' '),
            ),
        )

        problems = draft.problems(candidates)

        assert problems == (
            'O título está ausente.',
            'A descrição está ausente.',
            'A Habilidade "APIs web" está duplicada.',
            'A Habilidade "skill-z" não existe entre as candidatas.',
            'A Habilidade "React" está sem justificativa.',
        )
        assert PlanningProposalDraft(title='t', description='d', skills=()).problems(
            candidates
        ) == ('A proposta precisa de ao menos uma Habilidade.',)
        assert (
            PlanningProposalDraft(
                title='t',
                description='d',
                skills=(
                    PlanningProposalDraftSkill(skill_id='skill-b', justification='j'),
                ),
            ).problems(candidates)
            == ()
        )
