import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PlanningSessionFaker } from '@/core/intelligence/fakers/planning-session-faker'
import { CONFIRMATION_KEY_PATTERN } from '@/core/intelligence/planning-session'

import {
  IDLE_GOAL_CREATION,
  type PlanningProposalReviewProps,
  usePlanningProposalReview,
} from '../use-planning-proposal-review'

const PLANNING_ID = '01ARZ3NDEKTSV4RRFFQ69G5FAV'

function renderReview(overrides: Partial<PlanningProposalReviewProps> = {}) {
  const props: PlanningProposalReviewProps = {
    planningId: PLANNING_ID,
    intent: 'Quero automatizar tarefas com Python.',
    proposal: PlanningSessionFaker.fakeProposal({
      title: 'Automação com Python',
      description: 'Scripts para planilhas.',
    }),
    isCancelling: false,
    isRestarting: false,
    restartErrorMessage: null,
    goalCreation: IDLE_GOAL_CREATION,
    onCancel: vi.fn(),
    onRestart: vi.fn(async () => true),
    onCreateGoal: vi.fn(),
    ...overrides,
  }
  return { props, ...renderHook(() => usePlanningProposalReview(props)) }
}

describe('usePlanningProposalReview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts in the graph view with the proposal fields and keeps edits across views (CA-01, CA-02)', () => {
    const { result } = renderReview()

    expect(result.current.view).toBe('graph')
    expect(result.current.title).toBe('Automação com Python')
    expect(result.current.description).toBe('Scripts para planilhas.')
    expect(result.current.relationSummary).toBe(
      'As duas habilidades se complementam. Você escolhe por onde começar.',
    )

    act(() => result.current.handleTitleChange('Automatizar planilhas'))
    act(() => result.current.handleViewChange('list'))
    expect(result.current.view).toBe('list')
    expect(result.current.title).toBe('Automatizar planilhas')
    act(() => result.current.handleViewChange('unknown'))
    expect(result.current.view).toBe('list')
    act(() => result.current.handleViewChange('graph'))
    expect(result.current.view).toBe('graph')
  })

  it('describes the relation summary by the number of Skills', () => {
    const single = renderReview({
      proposal: PlanningSessionFaker.fakeProposal({
        skills: [{ skillId: 'a', name: 'Python', justification: 'Base.' }],
        relations: [],
      }),
    })
    expect(single.result.current.relationSummary).toBe(
      'Esta habilidade sustenta o objetivo. Você escolhe por onde começar.',
    )

    const many = renderReview({
      proposal: PlanningSessionFaker.fakeProposal({
        skills: Array.from({ length: 9 }, (_, index) => ({
          skillId: `skill-${index}`,
          name: `Habilidade ${index}`,
          justification: 'Base.',
        })),
        relations: [],
      }),
    })
    expect(many.result.current.relationSummary).toBe(
      'As 9 habilidades se complementam. Você escolhe por onde começar.',
    )
  })

  it('blocks the goal creation with empty fields and clears the errors while typing (CA-04)', () => {
    const { result, props } = renderReview()

    act(() => result.current.handleTitleChange('   '))
    act(() => result.current.handleDescriptionChange(''))
    act(() => result.current.handleCreateGoal())

    expect(result.current.titleError).toBe('Informe um título para o Objetivo.')
    expect(result.current.descriptionError).toBe('Informe uma descrição para o Objetivo.')
    expect(props.onCreateGoal).not.toHaveBeenCalled()

    act(() => result.current.handleTitleChange('Novo título'))
    expect(result.current.titleError).toBeNull()
    expect(result.current.descriptionError).toBe('Informe uma descrição para o Objetivo.')
    act(() => result.current.handleCreateGoal())
    expect(props.onCreateGoal).not.toHaveBeenCalled()

    act(() => result.current.handleDescriptionChange('Nova descrição '))
    expect(result.current.descriptionError).toBeNull()
  })

  it('delivers the trimmed edits and the untouched proposal to the creation contract (CA-05)', () => {
    const { result, props } = renderReview()

    act(() => result.current.handleTitleChange('  Automatizar planilhas  '))
    act(() => result.current.handleDescriptionChange(' Scripts que leem planilhas. '))
    act(() => result.current.handleCreateGoal())

    expect(props.onCreateGoal).toHaveBeenCalledWith({
      planningId: PLANNING_ID,
      confirmationKey: expect.stringMatching(CONFIRMATION_KEY_PATTERN),
      title: 'Automatizar planilhas',
      description: 'Scripts que leem planilhas.',
      proposal: props.proposal,
    })
    expect(result.current.titleError).toBeNull()
    expect(result.current.descriptionError).toBeNull()

    // A retry replays the same confirmation key.
    act(() => result.current.handleCreateGoal())
    const [first, second] = vi.mocked(props.onCreateGoal).mock.calls
    expect(second[0].confirmationKey).toBe(first[0].confirmationKey)
  })

  it('freezes the review while creating or uncertain and words the action per state', () => {
    const creating = renderReview({ goalCreation: { status: 'creating', message: null } })
    expect(creating.result.current.isFrozen).toBe(true)
    expect(creating.result.current.createGoalLabel).toBe('Criando objetivo…')
    expect(creating.result.current.goalCreationNotice).toMatchObject({
      tone: 'processing',
      title: 'Criando seu objetivo…',
    })
    act(() => creating.result.current.handleCreateGoal())
    expect(creating.props.onCreateGoal).not.toHaveBeenCalled()

    const failed = renderReview({
      goalCreation: { status: 'failed', message: 'Este Skill ainda não está pronto.' },
    })
    expect(failed.result.current.isFrozen).toBe(false)
    expect(failed.result.current.createGoalLabel).toBe('Tentar criar objetivo')
    expect(failed.result.current.goalCreationNotice).toEqual({
      tone: 'failure',
      title: 'Não foi possível criar o objetivo',
      support: 'Este Skill ainda não está pronto. Sua proposta foi mantida.',
    })

    const plainFailure = renderReview({
      goalCreation: { status: 'failed', message: null },
    })
    expect(plainFailure.result.current.goalCreationNotice?.support).toBe(
      'Sua proposta foi mantida. Tente criar o objetivo novamente.',
    )

    const uncertain = renderReview({
      goalCreation: { status: 'uncertain', message: null },
    })
    expect(uncertain.result.current.isFrozen).toBe(true)
    expect(uncertain.result.current.createGoalLabel).toBe('Verificar resultado')
    expect(uncertain.result.current.goalCreationNotice?.tone).toBe('uncertain')
    act(() => uncertain.result.current.handleCreateGoal())
    expect(uncertain.props.onCreateGoal).toHaveBeenCalledOnce()
  })

  it('opens and closes the restart dialog without touching the edits (CA-06, CA-07)', async () => {
    const { result, props } = renderReview()

    act(() => result.current.handleTitleChange('Editado'))
    act(() => result.current.handleOpenRestart())
    expect(result.current.isRestartDialogOpen).toBe(true)
    act(() => result.current.handleCloseRestart())
    expect(result.current.isRestartDialogOpen).toBe(false)
    expect(result.current.title).toBe('Editado')
    expect(props.onRestart).not.toHaveBeenCalled()

    act(() => result.current.handleOpenRestart())
    await act(async () => {
      await result.current.handleSubmitRestart('Quero aprender APIs web')
    })
    expect(props.onRestart).toHaveBeenCalledWith('Quero aprender APIs web')
    expect(result.current.isRestartDialogOpen).toBe(false)
  })

  it('keeps the dialog open when the restart is refused (CA-09)', async () => {
    const { result } = renderReview({ onRestart: vi.fn(async () => false) })

    act(() => result.current.handleOpenRestart())
    await act(async () => {
      await result.current.handleSubmitRestart('Quero aprender APIs web')
    })

    expect(result.current.isRestartDialogOpen).toBe(true)
  })
})
