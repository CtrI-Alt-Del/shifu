from collections.abc import Callable
from datetime import UTC, datetime
import pytest
from shifu.intelligence.core.domain.enums import PlanningQuestionKind
from shifu.intelligence.core.domain.structures import (
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

_NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
_PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'
_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAW'
_NEXT_OPERATION_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAX'


def _question(
    question_id: str = 'q1',
    kind: PlanningQuestionKind = PlanningQuestionKind.SINGLE,
    *,
    unknown: bool = False,
    other: bool = False,
) -> PlanningQuestion:
    options = [
        PlanningOption(id='o1', text='Sites'),
        PlanningOption(id='o2', text='APIs'),
    ]
    if other:
        options.append(PlanningOption.other())
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
            for skill_id in skill_ids or ('skill-a',)
        ),
    )


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
