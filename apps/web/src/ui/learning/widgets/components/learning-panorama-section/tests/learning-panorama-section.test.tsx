import {
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  RouterProvider,
} from '@tanstack/react-router'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { LearningPanorama } from '@/core/learning/learning-panorama'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { BarChartProps } from '@/ui/shared/widgets/components/bar-chart'
import type { ChartDatum } from '@/ui/shared/widgets/components/chart-frame'
import type { LineChartProps } from '@/ui/shared/widgets/components/line-chart'

import { LearningPanoramaSection } from '..'
import { useSkillEvolutionCard } from '../skill-evolution-card/use-skill-evolution-card'
import { useLearningPanoramaSection } from '../use-learning-panorama-section'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-learning-panorama-section', () => ({
  useLearningPanoramaSection: vi.fn(),
}))
vi.mock('../skill-evolution-card/use-skill-evolution-card', () => ({
  useSkillEvolutionCard: vi.fn(),
}))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))
vi.mock('@/ui/shared/widgets/components/bar-chart', () => ({
  BarChart: ({ data, tone, title, highlightLast }: BarChartProps) => (
    <div
      data-highlight-last={String(highlightLast)}
      data-testid='bar-chart'
      data-title={title}
      data-tone={tone}
    >
      {data.map((datum) => datum.valueLabel).join('|')}
    </div>
  ),
}))
vi.mock('@/ui/shared/widgets/components/line-chart', () => ({
  LineChart: ({ data, title }: LineChartProps) => (
    <div data-testid='line-chart' data-title={title}>
      {data.length}
    </div>
  ),
}))

const useLearningPanoramaSectionMock = vi.mocked(useLearningPanoramaSection)
const useSkillEvolutionCardMock = vi.mocked(useSkillEvolutionCard)
const handleRetryMock = vi.fn()

const panorama: LearningPanorama = {
  hasGoals: true,
  completedSkillCount: 3,
  masteredCompetencyCount: 14,
  stageDistribution: {
    notStarted: 2,
    diagnosing: 1,
    learning: 3,
    completed: 3,
    goalCount: 3,
  },
  resumeItems: [
    {
      skillExperienceId: 'exp-python',
      goalId: 'goal-data',
      goalTitle: 'Carreira em dados',
      skillId: 'skill-python',
      skillName: 'Python para análise de dados',
      status: 'learning',
      focusCompetencyName: 'Limpeza de tabelas',
      lastSubmittedAt: '2026-11-21T14:02:00Z',
    },
    {
      skillExperienceId: 'exp-sql',
      goalId: 'goal-data',
      goalTitle: 'Carreira em dados',
      skillId: 'skill-sql',
      skillName: 'SQL básico',
      status: 'diagnosing',
      focusCompetencyName: null,
      lastSubmittedAt: null,
    },
  ],
  weeklyEvaluatedActivities: [],
  evolutionOptions: [
    {
      skillExperienceId: 'exp-python',
      goalTitle: 'Carreira em dados',
      skillName: 'Python para análise de dados',
      status: 'learning',
    },
  ],
  defaultEvolutionSkillExperienceId: 'exp-python',
  completedSkills: [
    {
      skillExperienceId: 'exp-logic-b',
      goalId: 'goal-b',
      goalTitle: 'Aprender a programar',
      skillId: 'skill-logic',
      skillName: 'Lógica de programação',
      finalResult: 91,
      completedOn: '2026-09-13',
    },
    {
      skillExperienceId: 'exp-logic-a',
      goalId: 'goal-a',
      goalTitle: 'Carreira em dados',
      skillId: 'skill-logic',
      skillName: 'Lógica de programação',
      finalResult: null,
      completedOn: '2026-08-10',
    },
  ],
  recentMasteries: [
    {
      skillExperienceId: 'exp-logic-b',
      goalId: 'goal-b',
      goalTitle: 'Aprender a programar',
      skillId: 'skill-logic',
      skillName: 'Lógica de programação',
      competencyId: 'comp-functions',
      competencyName: 'Funções',
      masteredOn: '2026-09-13',
    },
  ],
}

const weeklyData: ChartDatum[] = [
  { key: '2026-09-28', label: '28 set', value: 3, valueLabel: '3 atividades' },
  { key: '2026-10-05', label: '5 out', value: 1, valueLabel: '1 atividade' },
]

function makeHookValue(
  overrides: Partial<ReturnType<typeof useLearningPanoramaSection>> = {},
): ReturnType<typeof useLearningPanoramaSection> {
  return {
    state: 'success',
    panorama,
    isRetrying: false,
    weeklyData,
    hasWeeklyData: true,
    stageItems: [
      { key: 'not-started', label: 'Não iniciadas', count: 2 },
      { key: 'diagnosing', label: 'Em diagnóstico', count: 1 },
      { key: 'learning', label: 'Em aprendizado', count: 3 },
      { key: 'completed', label: 'Concluídas', count: 3 },
    ],
    stageSummary: '9 Habilidades em 3 Objetivos',
    handleRetry: handleRetryMock,
    ...overrides,
  }
}

function makeEvolutionHookValue(): ReturnType<typeof useSkillEvolutionCard> {
  return {
    state: 'success',
    selectedSkillExperienceId: 'exp-python',
    selectOptions: [{ value: 'exp-python', label: 'Python para análise de dados' }],
    evolutionData: [],
    baselineLabel: undefined,
    description: 'Resultado da Habilidade após cada avaliação',
    isRetrying: false,
    handleSelectSkillExperience: vi.fn(),
    handleRetry: vi.fn(),
  }
}

async function renderSection() {
  const root = createRootRoute({
    component: () => (
      <>
        <LearningPanoramaSection />
        <Outlet />
      </>
    ),
  })
  const skill = createRoute({
    getParentRoute: () => root,
    path: ROUTES.learningSkill,
    component: () => <h1>Habilidade aberta</h1>,
  })
  const router = createRouter({
    routeTree: root.addChildren([skill]),
    history: createMemoryHistory({ initialEntries: ['/'] }),
  })
  render(<RouterProvider router={router} />)
  await screen.findByRole('heading', { name: 'Aprendizagem' })
  return router
}

function leafRoute(router: { state: { matches: unknown[] } }) {
  const { routeId, params } = router.state.matches.at(-1) as {
    routeId: string
    params: Record<string, string>
  }
  return { routeId, params }
}

describe('LearningPanoramaSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // The router restores scroll on navigation, which jsdom does not implement.
    vi.spyOn(window, 'scrollTo').mockImplementation(() => {})
    useLearningPanoramaSectionMock.mockReturnValue(makeHookValue())
    useSkillEvolutionCardMock.mockReturnValue(makeEvolutionHookValue())
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('keeps the Aprendizagem heading and shows a busy placeholder while loading', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({ state: 'loading', panorama: null }),
    )

    await renderSection()

    expect(
      screen.getByRole('status', { name: 'Carregando sua aprendizagem' }),
    ).toHaveAttribute('aria-busy', 'true')
    expect(
      screen.queryByRole('heading', { name: 'Continue de onde parou' }),
    ).not.toBeInTheDocument()
  })

  it('shows the unavailable state and retries the panorama read', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({ state: 'error', panorama: null }),
    )

    await renderSection()

    const alert = screen.getByRole('alert')
    expect(
      within(alert).getByText('Não foi possível carregar sua aprendizagem'),
    ).toBeVisible()

    fireEvent.click(within(alert).getByRole('button', { name: 'Tentar novamente' }))

    expect(handleRetryMock).toHaveBeenCalledTimes(1)
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument()
  })

  it('disables the retry button while a retry is in flight', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({ state: 'error', panorama: null, isRetrying: true }),
    )

    await renderSection()

    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('explains the empty panorama and offers Criar objetivo without any chart', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({ state: 'empty', panorama: null }),
    )

    await renderSection()

    expect(screen.getByText('Sua aprendizagem começa com um Objetivo')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Criar objetivo' })).toHaveAttribute(
      'href',
      ROUTES.learningGoalsNew,
    )
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument()
    expect(screen.queryByTestId('line-chart')).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: 'Gráfico' })).not.toBeInTheDocument()
  })

  it('lists the stage distribution with labels and counts', async () => {
    await renderSection()

    const stages = screen.getByRole('region', { name: 'Habilidades por etapa' })
    expect(within(stages).getByText('9 Habilidades em 3 Objetivos')).toBeVisible()
    const items = within(stages).getAllByRole('listitem')
    expect(items.map((item) => item.textContent)).toEqual([
      'Não iniciadas2',
      'Em diagnóstico1',
      'Em aprendizado3',
      'Concluídas3',
    ])
  })

  it('shows Continue items with Objetivo, stage and focus only for the learning stage', async () => {
    await renderSection()

    const resume = screen.getByRole('region', { name: 'Continue de onde parou' })
    expect(within(resume).getByText('Python para análise de dados')).toBeVisible()
    expect(
      within(resume).getByText('Objetivo: Carreira em dados · Foco: Limpeza de tabelas'),
    ).toBeVisible()
    expect(within(resume).getByText('Em aprendizado')).toBeVisible()
    expect(within(resume).getByText('SQL básico')).toBeVisible()
    expect(within(resume).getByText('Objetivo: Carreira em dados')).toBeVisible()
    expect(within(resume).getByText('Em diagnóstico')).toBeVisible()
    expect(resume.textContent).not.toMatch(/próxima|recomend/i)
  })

  it('opens the experience skill page from a Continuar link', async () => {
    const router = await renderSection()

    const links = screen.getAllByRole('link', { name: 'Continuar' })
    expect(links).toHaveLength(2)
    expect(links[0]).toHaveAttribute(
      'href',
      '/learning/goals/goal-data/skills/skill-python',
    )

    fireEvent.click(links[0])

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Habilidade aberta' })).toBeVisible(),
    )
    expect(leafRoute(router)).toEqual({
      routeId: ROUTES.learningSkill,
      params: { goalId: 'goal-data', skillId: 'skill-python' },
    })
  })

  it('tells the learner when no experience is in diagnosis or learning', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({ panorama: { ...panorama, resumeItems: [] } }),
    )

    await renderSection()

    expect(
      screen.getByText('Nenhuma Habilidade em diagnóstico ou em aprendizado no momento.'),
    ).toBeVisible()
    expect(screen.queryByRole('link', { name: 'Continuar' })).not.toBeInTheDocument()
  })

  it('renders the weekly chart with the count-not-performance footnote', async () => {
    await renderSection()

    const weekly = screen.getByRole('region', { name: 'Atividades avaliadas por semana' })
    expect(
      within(weekly).getByText('Últimas 8 semanas, em todas as suas Habilidades'),
    ).toBeVisible()
    const chart = within(weekly).getByTestId('bar-chart')
    expect(chart).toHaveAttribute('data-tone', 'jade')
    expect(chart).toHaveAttribute('data-highlight-last', 'true')
    expect(chart).toHaveAttribute('data-title', 'Atividades avaliadas por semana')
    expect(chart).toHaveTextContent('3 atividades|1 atividade')
    expect(
      within(weekly).getByText(
        'O valor é uma contagem de atividades avaliadas e não representa desempenho.',
      ),
    ).toBeVisible()
  })

  it('switches the weekly chart to a table of the same values', async () => {
    await renderSection()

    const weekly = screen.getByRole('region', { name: 'Atividades avaliadas por semana' })
    await userEvent.setup().click(within(weekly).getByRole('tab', { name: 'Tabela' }))

    const table = await within(weekly).findByRole('table', {
      name: 'Atividades avaliadas por semana',
    })
    expect(
      within(table)
        .getAllByRole('row')
        .map((row) => row.textContent),
    ).toEqual([
      'Semana iniciada emAtividades avaliadas',
      '28 set3 atividades',
      '5 out1 atividade',
    ])
    expect(
      within(weekly).getByText(
        'O valor é uma contagem de atividades avaliadas e não representa desempenho.',
      ),
    ).toBeVisible()
  })

  it('explains that the weekly chart appears after the first evaluations', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({ hasWeeklyData: false }),
    )

    await renderSection()

    const weekly = screen.getByRole('region', { name: 'Atividades avaliadas por semana' })
    expect(
      within(weekly).getByText(/aparecerão depois das primeiras avaliações/),
    ).toBeVisible()
    expect(within(weekly).queryByTestId('bar-chart')).not.toBeInTheDocument()
    expect(within(weekly).queryByRole('tab', { name: 'Tabela' })).not.toBeInTheDocument()
  })

  it('renders the evolution card inside the section from the default selection', async () => {
    await renderSection()

    const evolution = screen.getByRole('region', { name: 'Evolução de uma Habilidade' })
    expect(within(evolution).getByTestId('line-chart')).toBeVisible()
    expect(useSkillEvolutionCardMock).toHaveBeenCalledWith({
      options: panorama.evolutionOptions,
      defaultSkillExperienceId: 'exp-python',
    })
  })

  it('lists both completions of the same Habilidade newest first with their Objetivo, result and date', async () => {
    await renderSection()

    const completed = screen.getByRole('region', { name: 'Habilidades concluídas' })
    const rows = within(completed).getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('Lógica de programação')
    expect(rows[0]).toHaveTextContent('Aprender a programar')
    expect(rows[0]).toHaveTextContent('13 set')
    expect(rows[0]).toHaveTextContent('91%')
    expect(rows[1]).toHaveTextContent('Carreira em dados')
    expect(rows[1]).toHaveTextContent('10 ago')
    expect(rows[1]).toHaveTextContent('—')
  })

  it('opens the skill page when a completed row is activated', async () => {
    const router = await renderSection()

    const completed = screen.getByRole('region', { name: 'Habilidades concluídas' })
    const links = within(completed).getAllByRole('link')
    expect(links[0]).toHaveAttribute('href', '/learning/goals/goal-b/skills/skill-logic')

    fireEvent.click(links[0])

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Habilidade aberta' })).toBeVisible(),
    )
    expect(leafRoute(router).params).toEqual({ goalId: 'goal-b', skillId: 'skill-logic' })
  })

  it('shows the recent masteries with Competência, Habilidade, Objetivo and date', async () => {
    await renderSection()

    const masteries = screen.getByRole('region', { name: 'Domínios recentes' })
    expect(within(masteries).getByText('Funções')).toBeVisible()
    expect(
      within(masteries).getByText(
        'Lógica de programação · Aprender a programar · 13 set',
      ),
    ).toBeVisible()
  })

  it('shows empty messages for the completed and mastery lists', async () => {
    useLearningPanoramaSectionMock.mockReturnValue(
      makeHookValue({
        panorama: { ...panorama, completedSkills: [], recentMasteries: [] },
      }),
    )

    await renderSection()

    expect(screen.getByText('Você ainda não concluiu nenhuma Habilidade.')).toBeVisible()
    expect(screen.getByText('Nenhuma Competência dominada recentemente.')).toBeVisible()
  })

  it('never shows engagement vocabulary in the learning section', async () => {
    await renderSection()

    expect(screen.getByRole('region', { name: 'Aprendizagem' }).textContent).not.toMatch(
      /\bXP\b|nível|sequência/i,
    )
  })
})
