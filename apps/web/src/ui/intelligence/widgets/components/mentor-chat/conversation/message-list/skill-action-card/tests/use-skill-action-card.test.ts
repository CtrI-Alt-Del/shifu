import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, renderHook } from '@testing-library/react'
import { createElement, type PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
import type { MentorSkillActionOutcome } from '@/core/learning/mentor-skill-action-outcome'
import type { MentorContextValue } from '@/ui/intelligence/contexts/mentor-context/types'
import { useConfirmMentorSkillAdditionAction } from '@/ui/intelligence/hooks/use-confirm-mentor-skill-addition-action'
import { useConfirmMentorSkillRemovalAction } from '@/ui/intelligence/hooks/use-confirm-mentor-skill-removal-action'
import { useDeclineMentorActionProposalAction } from '@/ui/intelligence/hooks/use-decline-mentor-action-proposal-action'
import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'
import { useSkillActionCard } from '../use-skill-action-card'

vi.mock('@/ui/intelligence/hooks/use-mentor-context', () => ({
  useMentorContext: vi.fn(),
}))
vi.mock('@/ui/intelligence/hooks/use-confirm-mentor-skill-addition-action', () => ({
  useConfirmMentorSkillAdditionAction: vi.fn(),
}))
vi.mock('@/ui/intelligence/hooks/use-confirm-mentor-skill-removal-action', () => ({
  useConfirmMentorSkillRemovalAction: vi.fn(),
}))
vi.mock('@/ui/intelligence/hooks/use-decline-mentor-action-proposal-action', () => ({
  useDeclineMentorActionProposalAction: vi.fn(),
}))
const useMentorContextMock = vi.mocked(useMentorContext)
const useConfirmMentorSkillAdditionActionMock = vi.mocked(
  useConfirmMentorSkillAdditionAction,
)
const useConfirmMentorSkillRemovalActionMock = vi.mocked(
  useConfirmMentorSkillRemovalAction,
)
const useDeclineMentorActionProposalActionMock = vi.mocked(
  useDeclineMentorActionProposalAction,
)

const SESSION_ID = '01J7T8AC91Z5K8M4JQ8C2D6F00'
const PROPOSAL_ID = '01J7T8AC91Z5K8M4JQ8C2D6F01'
const SKILL_ID = '01J7T8AC91Z5K8M4JQ8C2D6F02'
const GOAL_ID = '01J7T8AC91Z5K8M4JQ8C2D6F03'
const OTHER_GOAL_ID = '01J7T8AC91Z5K8M4JQ8C2D6F04'
const EXPERIENCE_ID = '01J7T8AC91Z5K8M4JQ8C2D6F05'
const OTHER_EXPERIENCE_ID = '01J7T8AC91Z5K8M4JQ8C2D6F06'
const JUSTIFICATION =
  'Você pediu ao Mentor para adicionar esta Habilidade. Funções, parâmetros e retornos.'

const onActionResolvedMock = vi.fn()
const confirmSkillAdditionMock = vi.fn()
const confirmSkillRemovalMock = vi.fn()
const declineActionProposalMock = vi.fn()
let queryClient: QueryClient

function makeProposal(
  overrides: Partial<MentorActionProposal> = {},
): MentorActionProposal {
  return {
    id: PROPOSAL_ID,
    sourceMessageId: '01J7T8AC91Z5K8M4JQ8C2D6F07',
    kind: 'add_skill',
    skillId: SKILL_ID,
    skillName: 'Funções em Python',
    goalId: GOAL_ID,
    goalTitle: 'Aprender a programar',
    skillExperienceId: null,
    candidateGoals: [],
    justification: JUSTIFICATION,
    status: 'pending',
    outcome: null,
    rejectionReason: null,
    resolvedGoalId: null,
    resolvedSkillExperienceId: null,
    createdAt: '2026-10-23T12:00:00Z',
    ...overrides,
  }
}

const removal = (overrides: Partial<MentorActionProposal> = {}) =>
  makeProposal({
    kind: 'remove_skill',
    skillExperienceId: EXPERIENCE_ID,
    justification: null,
    ...overrides,
  })

const pickerProposal = (overrides: Partial<MentorActionProposal> = {}) =>
  makeProposal({
    goalId: null,
    goalTitle: null,
    candidateGoals: [
      {
        goalId: GOAL_ID,
        title: 'Aprender a programar',
        containsSkill: false,
        skillExperienceId: null,
      },
      {
        goalId: OTHER_GOAL_ID,
        title: 'Construir meu portfólio',
        containsSkill: true,
        skillExperienceId: OTHER_EXPERIENCE_ID,
      },
    ],
    ...overrides,
  })

function outcomeOf(
  overrides: Partial<MentorSkillActionOutcome>,
): MentorSkillActionOutcome {
  return {
    confirmationId: PROPOSAL_ID,
    operation: 'add_skill',
    outcome: 'added',
    rejectionReason: null,
    goalId: GOAL_ID,
    skillId: SKILL_ID,
    skillExperienceId: EXPERIENCE_ID,
    ...overrides,
  }
}

function wrapper({ children }: PropsWithChildren) {
  return createElement(QueryClientProvider, { client: queryClient }, children)
}

function renderCard(proposal: MentorActionProposal) {
  return renderHook(() => useSkillActionCard(proposal), { wrapper })
}

const actionLabels = (result: { current: ReturnType<typeof useSkillActionCard> }) =>
  result.current.actions.map((action) => action.label)

function actionOf(
  result: { current: ReturnType<typeof useSkillActionCard> },
  label: string,
) {
  const action = result.current.actions.find((candidate) => candidate.label === label)
  if (!action) throw new Error(`Missing action ${label}`)
  return action
}

describe('useSkillActionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient()
    vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue(undefined)
    useMentorContextMock.mockReturnValue({
      selectedSessionId: SESSION_ID,
      onActionResolved: onActionResolvedMock,
    } as unknown as MentorContextValue)
    useConfirmMentorSkillAdditionActionMock.mockReturnValue({
      confirmSkillAddition: confirmSkillAdditionMock,
      error: null,
      isPending: false,
    } as unknown as ReturnType<typeof useConfirmMentorSkillAdditionAction>)
    useConfirmMentorSkillRemovalActionMock.mockReturnValue({
      confirmSkillRemoval: confirmSkillRemovalMock,
      error: null,
      isPending: false,
    } as unknown as ReturnType<typeof useConfirmMentorSkillRemovalAction>)
    useDeclineMentorActionProposalActionMock.mockReturnValue({
      declineActionProposal: declineActionProposalMock,
      error: null,
      isPending: false,
    } as unknown as ReturnType<typeof useDeclineMentorActionProposalAction>)
  })
  afterEach(cleanup)

  describe('proposal', () => {
    it('presents an addition with its destination, justification and the two buttons', () => {
      const { result } = renderCard(makeProposal())

      expect(result.current.title).toBe('Adicionar Funções em Python?')
      expect(result.current.icon).toEqual({ name: 'graduation-cap', tone: 'jade' })
      expect(result.current.destination).toBe('Objetivo: Aprender a programar')
      expect(result.current.reason).toBe(JUSTIFICATION)
      expect(result.current.consequences).toBeUndefined()
      expect(actionLabels(result)).toEqual(['Recusar', 'Adicionar habilidade'])
      expect(actionOf(result, 'Recusar').variant).toBe('outline')
      expect(actionOf(result, 'Adicionar habilidade').variant).toBe('primary')
      expect(result.current.picker).toBeNull()
      expect(result.current.swap).toBeNull()
    })

    it('presents a removal with its consequences before the danger button', () => {
      const { result } = renderCard(removal())

      expect(result.current.title).toBe('Remover Funções em Python?')
      expect(result.current.icon).toEqual({ name: 'trash-2', tone: 'danger' })
      expect(result.current.reason).toBe(
        'Você pediu para retirar esta Habilidade do Objetivo.',
      )
      expect(result.current.consequences).toContain('Você perderá o diagnóstico')
      expect(result.current.consequences).toContain(
        'Se adicionar novamente, começará do zero.',
      )
      expect(actionLabels(result)).toEqual(['Recusar', 'Remover habilidade'])
      expect(actionOf(result, 'Remover habilidade').variant).toBe('danger')
    })
  })

  describe('Objective picker', () => {
    it('starts on the picker with the containing Objective disabled and only a decline button', () => {
      const { result } = renderCard(pickerProposal())

      expect(result.current.isTitleVisible).not.toBe(false)
      expect(result.current.title).toBe('Adicionar Funções em Python?')
      expect(result.current.destination).toBeUndefined()
      expect(result.current.picker).toEqual({
        hint: 'Escolha um Objetivo para revisar a proposta de adição.',
        candidates: [
          {
            goalId: GOAL_ID,
            title: 'Aprender a programar',
            isDisabled: false,
            isSelected: false,
          },
          {
            goalId: OTHER_GOAL_ID,
            title: 'Construir meu portfólio',
            isDisabled: true,
            isSelected: false,
          },
        ],
      })
      expect(actionLabels(result)).toEqual(['Recusar'])
    })

    it('shows the full proposal with Trocar Objetivo after choosing and returns to the picker on swap', () => {
      const { result } = renderCard(pickerProposal())

      act(() => result.current.handleSelectGoal(GOAL_ID))

      expect(result.current.picker).toBeNull()
      expect(result.current.destination).toBe('Objetivo: Aprender a programar')
      expect(result.current.swap?.label).toBe('Trocar Objetivo')
      expect(actionLabels(result)).toEqual(['Recusar', 'Adicionar habilidade'])

      act(() => result.current.swap?.handleSelect())

      expect(result.current.picker?.candidates.map((item) => item.isSelected)).toEqual([
        true,
        false,
      ])
      expect(result.current.swap).toBeNull()

      act(() => result.current.handleSelectGoal(OTHER_GOAL_ID))

      expect(result.current.picker).toBeNull()
      expect(result.current.destination).toBe('Objetivo: Construir meu portfólio')
    })

    it('lists a removal candidate as available and uses the experience of the chosen Objective', async () => {
      confirmSkillRemovalMock.mockResolvedValue(
        outcomeOf({
          operation: 'remove_skill',
          outcome: 'removed',
          goalId: OTHER_GOAL_ID,
          skillExperienceId: OTHER_EXPERIENCE_ID,
        }),
      )
      const { result } = renderCard(
        pickerProposal({ kind: 'remove_skill', justification: null }),
      )

      expect(result.current.picker?.hint).toBe(
        'Escolha um Objetivo para revisar a proposta de remoção.',
      )
      expect(result.current.picker?.candidates.map((item) => item.isDisabled)).toEqual([
        false,
        false,
      ])
      act(() => result.current.handleSelectGoal(OTHER_GOAL_ID))
      await act(async () => actionOf(result, 'Remover habilidade').handleSelect?.())

      expect(confirmSkillRemovalMock).toHaveBeenCalledExactlyOnceWith(OTHER_GOAL_ID, {
        confirmationId: PROPOSAL_ID,
        skillExperienceId: OTHER_EXPERIENCE_ID,
      })
    })

    it('locks the chosen Objective after the first confirmation', async () => {
      confirmSkillAdditionMock.mockRejectedValue(new RestError('indisponível', 503))
      const { result } = renderCard(pickerProposal())

      act(() => result.current.handleSelectGoal(GOAL_ID))
      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(result.current.swap).toBeNull()
      expect(result.current.picker).toBeNull()
      expect(result.current.destination).toBe('Objetivo: Aprender a programar')
    })
  })

  describe('confirmation', () => {
    it('confirms an addition with the proposal id, shows processing and then the added result', async () => {
      let resolve: (outcome: MentorSkillActionOutcome) => void = () => undefined
      confirmSkillAdditionMock.mockReturnValue(
        new Promise<MentorSkillActionOutcome>((done) => {
          resolve = done
        }),
      )
      const { result } = renderCard(makeProposal())

      act(() => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(confirmSkillAdditionMock).toHaveBeenCalledExactlyOnceWith(GOAL_ID, {
        confirmationId: PROPOSAL_ID,
        skillId: SKILL_ID,
        justification: JUSTIFICATION,
      })
      expect(result.current.title).toBe('Adicionando Funções em Python')
      expect(result.current.result).toBe(
        'A confirmação está em andamento. Aguarde o resultado.',
      )
      expect(result.current.statusText).toBe('Adicionando habilidade…')
      expect(result.current.actions).toEqual([])

      await act(async () => resolve(outcomeOf({})))

      expect(result.current.title).toBe('Funções em Python adicionada')
      expect(result.current.result).toBe(
        'A Habilidade começa como não iniciada. A justificativa pode ser consultada no Objetivo.',
      )
      expect(result.current.statusText).toBe('Adição concluída')
      expect(result.current.actions).toEqual([
        {
          key: 'view',
          label: 'Ver Objetivo',
          variant: 'outline',
          destination: { kind: 'goal', goalId: GOAL_ID },
        },
      ])
      expect(onActionResolvedMock).toHaveBeenCalledExactlyOnceWith(PROPOSAL_ID)
    })

    it('invalidates the Objective detail and the home Objectives queries after a completed outcome', async () => {
      confirmSkillAdditionMock.mockResolvedValue(outcomeOf({}))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['learning', 'goal-detail', GOAL_ID],
      })
      expect(queryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: ['learning', 'home-goals'],
      })
    })

    it('links an already present Skill to its existing experience', async () => {
      confirmSkillAdditionMock.mockResolvedValue(
        outcomeOf({ outcome: 'already_present' }),
      )
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(result.current.title).toBe('Funções em Python já está no Objetivo')
      expect(result.current.result).toBe('Sua experiência existente foi mantida.')
      expect(result.current.statusText).toBe('Nenhuma Habilidade duplicada.')
      expect(actionOf(result, 'Ver Habilidade').destination).toEqual({
        kind: 'skill',
        goalId: GOAL_ID,
        skillId: SKILL_ID,
      })
    })

    it('confirms a removal with the experience id and shows the removed result', async () => {
      confirmSkillRemovalMock.mockResolvedValue(
        outcomeOf({ operation: 'remove_skill', outcome: 'removed' }),
      )
      const { result } = renderCard(removal())

      await act(async () => actionOf(result, 'Remover habilidade').handleSelect?.())

      expect(confirmSkillRemovalMock).toHaveBeenCalledExactlyOnceWith(GOAL_ID, {
        confirmationId: PROPOSAL_ID,
        skillExperienceId: EXPERIENCE_ID,
      })
      expect(confirmSkillAdditionMock).not.toHaveBeenCalled()
      expect(result.current.title).toBe('Funções em Python removida')
      expect(result.current.icon).toEqual({ name: 'trash-2', tone: 'muted' })
      expect(result.current.result).toBe(
        'A experiência e seu histórico foram removidos. O Objetivo permanece disponível.',
      )
      expect(result.current.statusText).toBe('Remoção concluída')
      expect(actionLabels(result)).toEqual(['Ver Objetivo'])
    })

    it.each([
      ['goal_unavailable', 'Este Objetivo não está mais disponível.'],
      ['skill_unavailable', 'Esta Habilidade não está mais disponível no Currículo.'],
      ['experience_unavailable', 'Esta experiência já não está no Objetivo.'],
    ] as const)(
      'shows the %s rejection without buttons or cache invalidation',
      async (reason, text) => {
        confirmSkillAdditionMock.mockResolvedValue(
          outcomeOf({ outcome: 'rejected', rejectionReason: reason }),
        )
        const { result } = renderCard(makeProposal())

        await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

        expect(result.current.title).toBe('Não foi possível adicionar Funções em Python')
        expect(result.current.result).toBe(text)
        expect(result.current.statusText).toBe('Nenhuma alteração foi executada.')
        expect(result.current.actions).toEqual([])
        expect(queryClient.invalidateQueries).not.toHaveBeenCalled()
        expect(onActionResolvedMock).toHaveBeenCalledWith(PROPOSAL_ID)
      },
    )

    it('uses the removal wording for a rejected removal', async () => {
      confirmSkillRemovalMock.mockResolvedValue(
        outcomeOf({
          operation: 'remove_skill',
          outcome: 'rejected',
          rejectionReason: 'experience_unavailable',
        }),
      )
      const { result } = renderCard(removal())

      await act(async () => actionOf(result, 'Remover habilidade').handleSelect?.())

      expect(result.current.title).toBe('Não foi possível remover Funções em Python')
    })

    it('ignores a second confirmation while one is processing', () => {
      confirmSkillAdditionMock.mockReturnValue(new Promise(() => undefined))
      const { result } = renderCard(makeProposal())
      const confirm = actionOf(result, 'Adicionar habilidade')

      act(() => confirm.handleSelect?.())
      act(() => confirm.handleSelect?.())

      expect(confirmSkillAdditionMock).toHaveBeenCalledOnce()
    })

    it('sends the default justification when the proposal has none', async () => {
      confirmSkillAdditionMock.mockResolvedValue(outcomeOf({}))
      const { result } = renderCard(makeProposal({ justification: null }))

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(confirmSkillAdditionMock).toHaveBeenCalledWith(GOAL_ID, {
        confirmationId: PROPOSAL_ID,
        skillId: SKILL_ID,
        justification: 'Você pediu ao Mentor para adicionar esta Habilidade.',
      })
    })
  })

  describe('failure classification', () => {
    it('treats a safe 503 as a recoverable failure with retry and decline', async () => {
      confirmSkillAdditionMock.mockRejectedValue(new RestError('indisponível', 503))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(result.current.title).toBe('Não foi possível adicionar Funções em Python')
      expect(result.current.result).toBe(
        'A adição não foi concluída. Sua proposta foi preservada.',
      )
      expect(result.current.statusText).toBe('Tente novamente com a mesma confirmação.')
      expect(actionLabels(result)).toEqual(['Recusar', 'Tentar novamente'])
      expect(onActionResolvedMock).not.toHaveBeenCalled()
    })

    it('uses the removal wording for a recoverable removal failure', async () => {
      confirmSkillRemovalMock.mockRejectedValue(new RestError('indisponível', 503))
      const { result } = renderCard(removal())

      await act(async () => actionOf(result, 'Remover habilidade').handleSelect?.())

      expect(result.current.title).toBe('Não foi possível remover Funções em Python')
      expect(result.current.result).toBe(
        'A remoção não foi concluída. Sua proposta foi preservada.',
      )
    })

    it.each([
      ['a network error', new RestError('rede', 0)],
      ['a timeout', new AppError('tempo esgotado', 'Erro de comunicação')],
      [
        'an unreadable response',
        new AppError('O corpo da resposta REST não foi informado.'),
      ],
      ['a conflict', new RestError('conflito', 409)],
      ['an unexpected failure', new TypeError('Failed to fetch')],
    ])(
      'treats %s as an uncertain result that never claims failure',
      async (_label, error) => {
        confirmSkillAdditionMock.mockRejectedValue(error)
        const { result } = renderCard(makeProposal())

        await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

        expect(result.current.title).toBe('Verificando adição de Funções em Python')
        expect(result.current.result).toBe(
          'Ainda não foi possível confirmar o resultado. Verifique a mesma confirmação antes de continuar.',
        )
        expect(result.current.statusText).toBe('Resultado ainda não confirmado')
        expect(actionLabels(result)).toEqual(['Verificar resultado'])
      },
    )

    it('uses the removal wording for an uncertain removal', async () => {
      confirmSkillRemovalMock.mockRejectedValue(new RestError('rede', 0))
      const { result } = renderCard(removal())

      await act(async () => actionOf(result, 'Remover habilidade').handleSelect?.())

      expect(result.current.title).toBe('Verificando remoção de Funções em Python')
    })

    it('retries with the original data and the same confirmation id', async () => {
      confirmSkillAdditionMock
        .mockRejectedValueOnce(new RestError('indisponível', 503))
        .mockResolvedValueOnce(outcomeOf({}))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())
      await act(async () => actionOf(result, 'Tentar novamente').handleSelect?.())

      expect(confirmSkillAdditionMock).toHaveBeenCalledTimes(2)
      expect(confirmSkillAdditionMock.mock.calls[1]).toEqual(
        confirmSkillAdditionMock.mock.calls[0],
      )
      expect(result.current.title).toBe('Funções em Python adicionada')
    })

    it('verifies an uncertain removal by resending the locked request', async () => {
      confirmSkillRemovalMock
        .mockRejectedValueOnce(new RestError('rede', 0))
        .mockResolvedValueOnce(
          outcomeOf({ operation: 'remove_skill', outcome: 'removed' }),
        )
      const { result } = renderCard(removal())

      await act(async () => actionOf(result, 'Remover habilidade').handleSelect?.())
      await act(async () => actionOf(result, 'Verificar resultado').handleSelect?.())

      expect(confirmSkillRemovalMock.mock.calls[1]).toEqual(
        confirmSkillRemovalMock.mock.calls[0],
      )
      expect(result.current.title).toBe('Funções em Python removida')
    })

    it('resends the locked Objective when verifying after a picker choice', async () => {
      confirmSkillAdditionMock
        .mockRejectedValueOnce(new RestError('rede', 0))
        .mockResolvedValueOnce(outcomeOf({}))
      const { result } = renderCard(pickerProposal())

      act(() => result.current.handleSelectGoal(GOAL_ID))
      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())
      await act(async () => actionOf(result, 'Verificar resultado').handleSelect?.())

      expect(confirmSkillAdditionMock).toHaveBeenNthCalledWith(1, GOAL_ID, {
        confirmationId: PROPOSAL_ID,
        skillId: SKILL_ID,
        justification: JUSTIFICATION,
      })
      expect(confirmSkillAdditionMock.mock.calls[1]).toEqual(
        confirmSkillAdditionMock.mock.calls[0],
      )
    })
  })

  describe('decline', () => {
    it('declines through the Intelligence route, shows the declined state and refreshes', async () => {
      declineActionProposalMock.mockResolvedValue(makeProposal({ status: 'declined' }))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Recusar').handleSelect?.())

      expect(declineActionProposalMock).toHaveBeenCalledExactlyOnceWith(
        SESSION_ID,
        PROPOSAL_ID,
      )
      expect(result.current.title).toBe('Adição recusada')
      expect(result.current.result).toBe(
        'Funções em Python não foi adicionada ao Objetivo.',
      )
      expect(result.current.statusText).toBe('Nenhuma alteração foi executada.')
      expect(result.current.actions).toEqual([])
      expect(onActionResolvedMock).toHaveBeenCalledExactlyOnceWith(PROPOSAL_ID)
      expect(confirmSkillAdditionMock).not.toHaveBeenCalled()
    })

    it('uses the removal wording when a removal is declined', async () => {
      declineActionProposalMock.mockResolvedValue(removal({ status: 'declined' }))
      const { result } = renderCard(removal())

      await act(async () => actionOf(result, 'Recusar').handleSelect?.())

      expect(result.current.title).toBe('Remoção recusada')
      expect(result.current.result).toBe('Funções em Python permanece no Objetivo.')
    })

    it('declines from a recoverable failure', async () => {
      confirmSkillAdditionMock.mockRejectedValue(new RestError('indisponível', 503))
      declineActionProposalMock.mockResolvedValue(makeProposal({ status: 'declined' }))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())
      await act(async () => actionOf(result, 'Recusar').handleSelect?.())

      expect(result.current.title).toBe('Adição recusada')
    })

    it('keeps the proposal and reports a decline failure', async () => {
      declineActionProposalMock.mockRejectedValue(new RestError('erro', 503))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Recusar').handleSelect?.())

      expect(result.current.title).toBe('Adicionar Funções em Python?')
      expect(result.current.result).toBe(
        'Não foi possível recusar agora. Tente novamente.',
      )
      expect(actionLabels(result)).toEqual(['Recusar', 'Adicionar habilidade'])
      expect(onActionResolvedMock).not.toHaveBeenCalled()
    })

    it('re-reads the conversation without an error when the decline finds a final proposal', async () => {
      declineActionProposalMock.mockRejectedValue(new RestError('final', 409))
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Recusar').handleSelect?.())

      expect(onActionResolvedMock).toHaveBeenCalledExactlyOnceWith(PROPOSAL_ID)
      expect(result.current.result).toBeUndefined()
      expect(result.current.title).toBe('Adicionar Funções em Python?')
    })

    it('does nothing without a selected conversation', async () => {
      useMentorContextMock.mockReturnValue({
        selectedSessionId: null,
        onActionResolved: onActionResolvedMock,
      } as unknown as MentorContextValue)
      const { result } = renderCard(makeProposal())

      await act(async () => actionOf(result, 'Recusar').handleSelect?.())

      expect(declineActionProposalMock).not.toHaveBeenCalled()
    })

    it('disables both buttons while the decline is pending', () => {
      useDeclineMentorActionProposalActionMock.mockReturnValue({
        declineActionProposal: declineActionProposalMock,
        error: null,
        isPending: true,
      } as unknown as ReturnType<typeof useDeclineMentorActionProposalAction>)
      const { result } = renderCard(makeProposal())

      expect(result.current.actions.map((action) => action.disabled)).toEqual([
        true,
        true,
      ])
    })
  })

  describe('persisted state', () => {
    it.each([
      ['declined', 'Adição recusada'],
      ['rejected', 'Não foi possível adicionar Funções em Python'],
    ] as const)(
      'renders a %s proposal from the server without buttons',
      (status, title) => {
        const { result } = renderCard(
          makeProposal({
            status,
            rejectionReason: status === 'rejected' ? 'goal_unavailable' : null,
          }),
        )

        expect(result.current.title).toBe(title)
        expect(result.current.actions).toEqual([])
      },
    )

    it('renders a completed removal from the server with the Objective link', () => {
      const { result } = renderCard(
        removal({ status: 'completed', outcome: 'removed', resolvedGoalId: GOAL_ID }),
      )

      expect(result.current.title).toBe('Funções em Python removida')
      expect(actionOf(result, 'Ver Objetivo').destination).toEqual({
        kind: 'goal',
        goalId: GOAL_ID,
      })
    })

    it('prefers the confirmed Learning outcome over a decline stored by Intelligence', async () => {
      confirmSkillAdditionMock.mockResolvedValue(outcomeOf({}))
      const { result, rerender } = renderHook(
        ({ proposal }) => useSkillActionCard(proposal),
        { wrapper, initialProps: { proposal: makeProposal() } },
      )

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())
      rerender({ proposal: makeProposal({ status: 'declined' }) })

      expect(result.current.title).toBe('Funções em Python adicionada')
    })
  })

  describe('focus', () => {
    it('moves focus to the result region when the card state changes', async () => {
      confirmSkillAdditionMock.mockResolvedValue(outcomeOf({}))
      const { result } = renderCard(makeProposal())
      const region = document.createElement('div')
      region.tabIndex = -1
      document.body.append(region)
      result.current.resultRef.current = region

      await act(async () => actionOf(result, 'Adicionar habilidade').handleSelect?.())

      expect(region).toHaveFocus()
      region.remove()
    })

    it('moves focus to the title after choosing an Objective in the picker', () => {
      const { result } = renderCard(pickerProposal())
      const heading = document.createElement('h3')
      heading.tabIndex = -1
      document.body.append(heading)
      result.current.titleRef.current = heading

      act(() => result.current.handleSelectGoal(GOAL_ID))

      expect(heading).toHaveFocus()
      heading.remove()
    })

    it('does not move focus on the first render', () => {
      const { result } = renderCard(makeProposal())

      expect(result.current.resultRef.current).toBeNull()
      expect(document.body).toHaveFocus()
    })
  })
})
