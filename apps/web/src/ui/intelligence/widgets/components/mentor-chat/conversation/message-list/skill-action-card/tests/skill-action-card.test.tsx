import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from '@tanstack/react-router'
import { createRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import { SkillActionCard } from '..'
import { useSkillActionCard } from '../use-skill-action-card'

vi.mock('../use-skill-action-card', () => ({ useSkillActionCard: vi.fn() }))
const useSkillActionCardMock = vi.mocked(useSkillActionCard)
const handleSelectMock = vi.fn()
const handleSelectGoalMock = vi.fn()
const handleSwapMock = vi.fn()

const proposal: MentorActionProposal = {
  id: '01J7T8AC91Z5K8M4JQ8C2D6F0A',
  sourceMessageId: '01J7T8AC91Z5K8M4JQ8C2D6F0B',
  kind: 'add_skill',
  skillId: '01J7T8AC91Z5K8M4JQ8C2D6F0C',
  skillName: 'Funções em Python',
  goalId: null,
  goalTitle: null,
  skillExperienceId: null,
  candidateGoals: [],
  justification: null,
  status: 'pending',
  outcome: null,
  rejectionReason: null,
  resolvedGoalId: null,
  resolvedSkillExperienceId: null,
  createdAt: '2026-10-23T12:00:00Z',
}

function makeHookValue(
  overrides: Partial<ReturnType<typeof useSkillActionCard>> = {},
): ReturnType<typeof useSkillActionCard> {
  return {
    icon: { name: 'graduation-cap', tone: 'jade' },
    title: 'Adicionar Funções em Python?',
    destination: 'Objetivo: Aprender a programar',
    reason: 'Você pediu ao Mentor para adicionar esta Habilidade.',
    actions: [],
    picker: null,
    swap: null,
    otherGoalExperiences: [],
    resultRef: createRef<HTMLOutputElement>(),
    titleRef: createRef<HTMLHeadingElement>(),
    handleSelectGoal: handleSelectGoalMock,
    ...overrides,
  }
}

async function renderCard() {
  const root = createRootRoute({
    component: () => (
      <>
        <SkillActionCard proposal={proposal} />
        <Outlet />
      </>
    ),
  })
  const goal = createRoute({
    getParentRoute: () => root,
    path: ROUTES.learningGoal,
    component: () => <h1>Objetivo aberto</h1>,
  })
  const skill = createRoute({
    getParentRoute: () => root,
    path: ROUTES.learningSkill,
    component: () => <h1>Habilidade aberta</h1>,
  })
  const router = createRouter({
    routeTree: root.addChildren([goal, skill]),
    history: createMemoryHistory({ initialEntries: ['/'] }),
    defaultNotFoundComponent: () => <p>Not found</p>,
  })
  render(<RouterProvider router={router} />)
  await screen.findByRole('region')
  return router
}

function leafRoute(router: { state: { matches: unknown[] } }) {
  const { routeId, params } = router.state.matches.at(-1) as {
    routeId: string
    params: Record<string, string>
  }
  return { routeId, params }
}

describe('SkillActionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'scrollTo').mockImplementation(() => undefined)
    useSkillActionCardMock.mockReturnValue(makeHookValue())
  })
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('renders the Objective picker with the containing Objective disabled and its reason', async () => {
    useSkillActionCardMock.mockReturnValue(
      makeHookValue({
        destination: undefined,
        reason: undefined,
        isTitleVisible: false,
        picker: {
          hint: 'Escolha um Objetivo para revisar a proposta de adição.',
          candidates: [
            {
              goalId: 'goal-1',
              title: 'Aprender a programar',
              isDisabled: false,
              isSelected: false,
            },
            {
              goalId: 'goal-2',
              title: 'Construir meu portfólio',
              isDisabled: true,
              isSelected: false,
            },
          ],
        },
        actions: [
          {
            key: 'decline',
            label: 'Recusar',
            variant: 'outline',
            handleSelect: handleSelectMock,
          },
        ],
      }),
    )
    await renderCard()

    expect(screen.getByRole('group', { name: 'Objetivo' })).toHaveAccessibleDescription(
      'Escolha um Objetivo para revisar a proposta de adição.',
    )
    const available = screen.getByRole('button', { name: 'Aprender a programar' })
    const containing = screen.getByRole('button', { name: /Construir meu portfólio/ })
    expect(available).toHaveAttribute('aria-pressed', 'false')
    expect(containing).toHaveAttribute('aria-disabled', 'true')
    expect(containing).toHaveAccessibleDescription('Já contém esta Habilidade')
    expect(screen.getByText('Já contém esta Habilidade')).toBeVisible()
    fireEvent.click(containing)
    expect(handleSelectGoalMock).not.toHaveBeenCalled()
    fireEvent.click(available)
    expect(handleSelectGoalMock).toHaveBeenCalledWith('goal-1')
    fireEvent.click(screen.getByRole('button', { name: 'Recusar' }))
    expect(handleSelectMock).toHaveBeenCalledOnce()
  })

  it('keeps the previously chosen Objective pressed when the picker is reopened', async () => {
    useSkillActionCardMock.mockReturnValue(
      makeHookValue({
        picker: {
          hint: 'Escolha um Objetivo para revisar a proposta de adição.',
          candidates: [
            {
              goalId: 'goal-1',
              title: 'Aprender a programar',
              isDisabled: false,
              isSelected: true,
            },
          ],
        },
      }),
    )
    await renderCard()

    expect(screen.getByRole('button', { name: 'Aprender a programar' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('shows the proposal with a Trocar Objetivo control that delegates the swap', async () => {
    useSkillActionCardMock.mockReturnValue(
      makeHookValue({
        swap: { label: 'Trocar Objetivo', handleSelect: handleSwapMock },
        actions: [
          { key: 'decline', label: 'Recusar', variant: 'outline' },
          {
            key: 'confirm',
            label: 'Adicionar habilidade',
            variant: 'primary',
            handleSelect: handleSelectMock,
          },
        ],
      }),
    )
    await renderCard()

    expect(screen.getByText('Objetivo: Aprender a programar')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Trocar Objetivo' }))
    expect(handleSwapMock).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Adicionar habilidade' }))
    expect(handleSelectMock).toHaveBeenCalledOnce()
  })

  it('renders Ver Objetivo as a typed link to the Objective route with its params', async () => {
    useSkillActionCardMock.mockReturnValue(
      makeHookValue({
        title: 'Funções em Python adicionada',
        reason: undefined,
        statusText: 'Adição concluída',
        actions: [
          {
            key: 'view',
            label: 'Ver Objetivo',
            variant: 'outline',
            destination: { kind: 'goal', goalId: 'goal-1' },
          },
        ],
      }),
    )
    const router = await renderCard()

    const link = screen.getByRole('link', { name: 'Ver Objetivo' })
    expect(link).toHaveAttribute('href', '/learning/goals/goal-1')
    fireEvent.click(link)
    await waitFor(() =>
      expect(router.state.location.pathname).toBe('/learning/goals/goal-1'),
    )
    expect(leafRoute(router)).toEqual({
      routeId: ROUTES.learningGoal,
      params: { goalId: 'goal-1' },
    })
  })

  it('renders Ver Habilidade as a typed link to the Skill route with both params', async () => {
    useSkillActionCardMock.mockReturnValue(
      makeHookValue({
        title: 'Funções em Python já está no Objetivo',
        actions: [
          {
            key: 'view',
            label: 'Ver Habilidade',
            variant: 'outline',
            destination: { kind: 'skill', goalId: 'goal-1', skillId: 'skill-9' },
          },
        ],
      }),
    )
    const router = await renderCard()

    const link = screen.getByRole('link', { name: 'Ver Habilidade' })
    expect(link).toHaveAttribute('href', '/learning/goals/goal-1/skills/skill-9')
    fireEvent.click(link)
    await waitFor(() =>
      expect(router.state.location.pathname).toBe(
        '/learning/goals/goal-1/skills/skill-9',
      ),
    )
    expect(leafRoute(router)).toEqual({
      routeId: ROUTES.learningSkill,
      params: { goalId: 'goal-1', skillId: 'skill-9' },
    })
  })

  it('exposes the status text and no buttons while a confirmation is processing', async () => {
    useSkillActionCardMock.mockReturnValue(
      makeHookValue({
        title: 'Adicionando Funções em Python',
        reason: undefined,
        result: 'A confirmação está em andamento. Aguarde o resultado.',
        statusText: 'Adicionando habilidade…',
        actions: [],
      }),
    )
    await renderCard()

    expect(screen.getByRole('status')).toHaveTextContent('Adicionando habilidade…')
    expect(screen.queryByRole('button')).toBeNull()
  })

  describe('other Goal experience notice', () => {
    const careerExperience: SkillExperienceReference = {
      goalId: 'goal-career',
      goalTitle: 'Carreira em dados',
      skillExperienceId: 'experience-career',
      skillId: 'skill-9',
      status: 'completed',
    }
    const portfolioExperience: SkillExperienceReference = {
      goalId: 'goal-portfolio',
      goalTitle: 'Construir meu portfólio',
      skillExperienceId: 'experience-portfolio',
      skillId: 'skill-9',
      status: 'learning',
    }
    const proposalActions: ReturnType<typeof useSkillActionCard>['actions'] = [
      { key: 'decline', label: 'Recusar', variant: 'outline' },
      {
        key: 'confirm',
        label: 'Adicionar habilidade',
        variant: 'primary',
        handleSelect: handleSelectMock,
      },
    ]

    it('explains the new experience starts from zero and links to the existing one', async () => {
      useSkillActionCardMock.mockReturnValue(
        makeHookValue({
          actions: proposalActions,
          otherGoalExperiences: [careerExperience],
        }),
      )
      const router = await renderCard()

      const notice = screen.getByRole('note')
      expect(notice).toHaveTextContent('Você já tem esta Habilidade em outro Objetivo')
      expect(notice).toHaveTextContent(
        'No Objetivo “Carreira em dados”, ela está concluída. Aqui ela começa do zero, com um novo diagnóstico, e nenhum resultado é copiado.',
      )
      const link = screen.getByRole('link', { name: 'Ver em Carreira em dados' })
      expect(link).toHaveAttribute('href', '/learning/goals/goal-career/skills/skill-9')
      fireEvent.click(link)
      await waitFor(() =>
        expect(router.state.location.pathname).toBe(
          '/learning/goals/goal-career/skills/skill-9',
        ),
      )
      expect(leafRoute(router)).toEqual({
        routeId: ROUTES.learningSkill,
        params: { goalId: 'goal-career', skillId: 'skill-9' },
      })
    })

    it('lists each other Goal with its own status and link, and the zero-start sentence once', async () => {
      useSkillActionCardMock.mockReturnValue(
        makeHookValue({
          actions: proposalActions,
          otherGoalExperiences: [careerExperience, portfolioExperience],
        }),
      )
      await renderCard()

      const notice = screen.getByRole('note')
      expect(notice).toHaveTextContent(
        'No Objetivo “Carreira em dados”, ela está concluída.',
      )
      expect(notice).toHaveTextContent(
        'No Objetivo “Construir meu portfólio”, ela está em aprendizado.',
      )
      expect(notice.textContent?.match(/começa do zero/g)).toHaveLength(1)
      expect(screen.getByRole('link', { name: 'Ver em Carreira em dados' })).toBeVisible()
      expect(
        screen.getByRole('link', { name: 'Ver em Construir meu portfólio' }),
      ).toHaveAttribute('href', '/learning/goals/goal-portfolio/skills/skill-9')
    })

    it('keeps Adicionar habilidade enabled and after the notice', async () => {
      useSkillActionCardMock.mockReturnValue(
        makeHookValue({
          actions: proposalActions,
          otherGoalExperiences: [careerExperience],
        }),
      )
      await renderCard()

      const confirm = screen.getByRole('button', { name: 'Adicionar habilidade' })
      expect(confirm).toBeEnabled()
      expect(
        screen.getByRole('note').compareDocumentPosition(confirm) &
          Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeGreaterThan(0)
      fireEvent.click(confirm)
      expect(handleSelectMock).toHaveBeenCalledOnce()
    })

    it('renders no notice without other experiences', async () => {
      useSkillActionCardMock.mockReturnValue(makeHookValue({ actions: proposalActions }))
      await renderCard()

      expect(screen.queryByRole('note')).toBeNull()
      expect(screen.queryByText(/Você já tem esta Habilidade/)).toBeNull()
    })
  })
})
