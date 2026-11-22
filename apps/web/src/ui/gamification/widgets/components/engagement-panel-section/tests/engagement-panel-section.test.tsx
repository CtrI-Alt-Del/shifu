import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { BarChartProps } from '@/ui/shared/widgets/components/bar-chart'

import { EngagementPanelSection } from '..'
import { useEngagementPanelSection } from '../use-engagement-panel-section'

// Entrance motion settles at once, so assertions see the final state.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-engagement-panel-section', () => ({
  useEngagementPanelSection: vi.fn(),
}))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))
// The chart wrapper has its own public contract proven by its own suite; the
// frame, its title, summary and table stay real.
vi.mock('@/ui/shared/widgets/components/bar-chart', () => ({
  BarChart: ({ data, tone, title, highlightLast }: BarChartProps) => (
    <div
      aria-label={title}
      data-highlight-last={String(highlightLast)}
      data-points={data.length}
      data-tone={tone}
      role='img'
    />
  ),
}))

const useEngagementPanelSectionMock = vi.mocked(useEngagementPanelSection)

type EngagementPanelSectionController = ReturnType<typeof useEngagementPanelSection>

const monthDays: EngagementPanelSectionController['monthDays'] = [
  { day: '2026-11-19', state: 'current-streak' },
  { day: '2026-11-20', state: 'practiced' },
  { day: '2026-11-21', state: 'missed' },
  { day: '2026-11-22', state: 'today-pending' },
]

const weeklyXp: EngagementPanelSectionController['weeklyXp'] = [
  { key: '2026-11-09', label: '9 nov', value: 85, valueLabel: '85 XP' },
  { key: '2026-11-16', label: '16 nov', value: 150, valueLabel: '150 XP' },
]

function makeController(
  overrides: Partial<EngagementPanelSectionController> = {},
): EngagementPanelSectionController {
  return {
    state: 'success',
    monthLabel: 'Novembro de 2026',
    monthDays,
    recentAchievements: [
      {
        id: 'consistencia-ii',
        name: 'Consistência II',
        criterionLabel: '7 dias consecutivos',
        xpLabel: '+50 XP',
        achievedOn: '21 nov 2026',
        icon: 'flame',
      },
      {
        id: 'primeira-jornada',
        name: 'Primeira Jornada',
        criterionLabel: '1 Habilidade concluída',
        xpLabel: '+50 XP',
        achievedOn: '13 set 2026',
        icon: 'flag',
      },
    ],
    nextAchievement: {
      name: 'Consistência III',
      criterionLabel: '30 dias consecutivos',
      progressLabel: '12 de 30',
      progressPercentage: 40,
      hint: 'Baseada no seu recorde de sequência.',
    },
    weeklyXp,
    isRetrying: false,
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('EngagementPanelSection', () => {
  afterEach(cleanup)

  beforeEach(() => useEngagementPanelSectionMock.mockReturnValue(makeController()))

  it('renders the Engajamento heading above its three cards', () => {
    render(<EngagementPanelSection />)

    expect(screen.getByRole('heading', { level: 2, name: 'Engajamento' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Novembro de 2026' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Conquistas recentes' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'XP por semana' })).toBeVisible()
  })

  it('renders the current month display-only with each day as text and a Calendário link', () => {
    render(<EngagementPanelSection />)

    const card = screen.getByRole('article', { name: 'Novembro de 2026' })
    expect(within(card).queryByRole('button')).not.toBeInTheDocument()
    expect(
      within(card).getByText('quinta-feira, 19 de novembro, dia da sequência atual'),
    ).toBeInTheDocument()
    expect(
      within(card).getByText('sexta-feira, 20 de novembro, dia de prática'),
    ).toBeInTheDocument()
    expect(
      within(card).getByText('domingo, 22 de novembro, hoje, prática ainda pendente'),
    ).toBeInTheDocument()
    expect(within(card).getByRole('link', { name: 'Abrir calendário' })).toHaveAttribute(
      'href',
      ROUTES.gamificationCalendar,
    )
  })

  it('identifies every calendar state in the legend text', () => {
    render(<EngagementPanelSection />)

    const legend = screen.getByRole('region', { name: 'Estados dos dias' })
    for (const label of [
      'Sequência atual',
      'Dia de prática',
      'Hoje, ainda dá para praticar',
      'Sem prática',
    ]) {
      expect(within(legend).getByText(label)).toBeVisible()
    }
    // Descriptions stay as hidden text, set off from the label, and the swatches
    // are decorative.
    expect(
      within(legend).getByText(/Dia que faz parte da sequência ativa\./),
    ).toHaveClass('sr-only')
    expect(within(legend).getAllByRole('listitem')).toHaveLength(4)
    expect(legend.querySelectorAll('span[aria-hidden="true"]')).toHaveLength(4)
  })

  it('renders each recent achievement with its criterion, date and XP and links to Conquistas', () => {
    render(<EngagementPanelSection />)

    const card = screen.getByRole('article', { name: 'Conquistas recentes' })
    const rows = within(
      within(card).getByRole('list', { name: 'Conquistas recentes' }),
    ).getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('Consistência II')
    expect(rows[0]).toHaveTextContent('7 dias consecutivos · 21 nov 2026')
    expect(rows[0]).toHaveTextContent('+50 XP')
    expect(rows[1]).toHaveTextContent('Primeira Jornada')
    expect(
      within(card).getByRole('link', { name: 'Ver todas as conquistas' }),
    ).toHaveAttribute('href', ROUTES.gamificationAchievements)
  })

  it('shows the next achievement with its criterion, current and target values', () => {
    render(<EngagementPanelSection />)

    const next = screen.getByRole('region', { name: 'Próxima conquista' })
    expect(next).toHaveTextContent('Consistência III · 30 dias consecutivos')
    expect(next).toHaveTextContent('12 de 30')
    expect(next).toHaveTextContent('Baseada no seu recorde de sequência.')
    const progress = within(next).getByRole('progressbar', {
      name: 'Progresso para Consistência III',
    })
    expect(progress).toHaveAttribute('aria-valuenow', '40')
    expect(progress).toHaveAttribute('aria-valuetext', '12 de 30')
  })

  it('omits the next achievement when the learner holds every active achievement', () => {
    useEngagementPanelSectionMock.mockReturnValue(
      makeController({ nextAchievement: null }),
    )
    render(<EngagementPanelSection />)

    expect(screen.queryByText('Próxima conquista')).not.toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Conquistas recentes' })).toBeVisible()
  })

  it('explains an empty achievements list instead of rendering an empty list', () => {
    useEngagementPanelSectionMock.mockReturnValue(
      makeController({ recentAchievements: [] }),
    )
    render(<EngagementPanelSection />)

    expect(
      screen.getByText(/Você ainda não obteve conquistas\. Continue praticando/),
    ).toBeVisible()
    expect(
      screen.queryByRole('list', { name: 'Conquistas recentes' }),
    ).not.toBeInTheDocument()
  })

  it('renders XP por semana as a latão bar chart with its text summary and history link', () => {
    render(<EngagementPanelSection />)

    expect(
      screen.getByText('Últimas 12 semanas · XP mede engajamento, não conhecimento'),
    ).toBeVisible()
    const chart = screen.getByRole('img', { name: 'XP por semana' })
    expect(chart).toHaveAttribute('data-tone', 'latao')
    expect(chart).toHaveAttribute('data-points', '2')
    expect(chart).toHaveAttribute('data-highlight-last', 'true')
    const historyLink = screen.getByRole('link', { name: 'Ver histórico de XP' })
    expect(historyLink).toHaveAttribute('href', ROUTES.gamificationXpHistory)
    // The link sits in the card header, in the title row.
    expect(historyLink.parentElement).toBe(
      screen.getByRole('heading', { name: 'XP por semana' }).parentElement,
    )
  })

  it('replaces the chart with a captioned table of the same weeks', async () => {
    render(<EngagementPanelSection />)

    await userEvent.click(screen.getByRole('tab', { name: 'Tabela' }))

    const table = screen.getByRole('table', { name: 'XP por semana' })
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((cell) => cell.textContent),
    ).toEqual(['Semana', 'XP'])
    const rows = within(table).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('9 nov')
    expect(rows[0]).toHaveTextContent('85 XP')
    expect(rows[1]).toHaveTextContent('16 nov')
    expect(rows[1]).toHaveTextContent('150 XP')
    expect(screen.queryByRole('img', { name: 'XP por semana' })).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'Gráfico' }))
    expect(screen.getByRole('img', { name: 'XP por semana' })).toBeVisible()
  })

  it('announces the loading state and keeps the section heading', () => {
    useEngagementPanelSectionMock.mockReturnValue(
      makeController({
        state: 'loading',
        monthLabel: '',
        monthDays: [],
        recentAchievements: [],
        nextAchievement: null,
        weeklyXp: [],
      }),
    )
    render(<EngagementPanelSection />)

    expect(screen.getByRole('heading', { level: 2, name: 'Engajamento' })).toBeVisible()
    expect(screen.getByLabelText('Carregando seu engajamento')).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.queryByRole('img', { name: 'XP por semana' })).not.toBeInTheDocument()
  })

  it('offers a working retry on the unavailable state and disables it while retrying', async () => {
    const handleRetry = vi.fn()
    useEngagementPanelSectionMock.mockReturnValue(
      makeController({
        state: 'error',
        monthLabel: '',
        monthDays: [],
        recentAchievements: [],
        nextAchievement: null,
        weeklyXp: [],
        handleRetry,
      }),
    )
    const { rerender } = render(<EngagementPanelSection />)

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar seu engajamento',
    )
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(handleRetry).toHaveBeenCalledOnce()

    useEngagementPanelSectionMock.mockReturnValue(
      makeController({
        state: 'error',
        monthDays: [],
        recentAchievements: [],
        nextAchievement: null,
        weeklyXp: [],
        isRetrying: true,
        handleRetry,
      }),
    )
    rerender(<EngagementPanelSection />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })
})
