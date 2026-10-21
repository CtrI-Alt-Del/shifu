import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { GamificationOverview } from '@/core/gamification/overview'

import { OverviewTabPanel } from '..'
import {
  type OverviewTabPanelController,
  useOverviewTabPanel,
} from '../use-overview-tab-panel'

vi.mock('../use-overview-tab-panel', () => ({ useOverviewTabPanel: vi.fn() }))

const useOverviewTabPanelMock = vi.mocked(useOverviewTabPanel)

const overview: GamificationOverview = {
  level: 5,
  totalXp: 1240,
  currentLevelXp: 1000,
  nextLevelXp: 1500,
  xpForNextLevel: 260,
  levelPercentage: 48,
  streak: {
    streak: { current: 3, longest: 9 },
    lastSevenDays: [
      { day: '2026-09-09', state: 'neutral' },
      { day: '2026-09-10', state: 'missed' },
      { day: '2026-09-11', state: 'practiced' },
      { day: '2026-09-12', state: 'current-streak' },
      { day: '2026-09-13', state: 'current-streak' },
      { day: '2026-09-14', state: 'current-streak' },
      { day: '2026-09-15', state: 'today-pending' },
    ],
    today: '2026-09-15',
    isTodayPending: true,
  },
  achievements: {
    recent: [
      {
        achievementId: 'consistencia-ii',
        name: 'Consistência II',
        criterionLabel: '7 dias consecutivos',
        xpReward: 50,
        achievedAt: '2026-09-13T12:00:00Z',
      },
      {
        achievementId: 'primeiro-passo',
        name: 'Primeiro Passo',
        criterionLabel: '1 diagnóstico concluído',
        xpReward: 25,
        achievedAt: '2026-09-11T12:00:00Z',
      },
    ],
    obtainedCount: 4,
    catalogCount: 12,
  },
}

function makeController(
  overrides: Partial<OverviewTabPanelController> = {},
): OverviewTabPanelController {
  return {
    overview,
    state: 'success',
    isRetrying: false,
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('OverviewTabPanel', () => {
  afterEach(cleanup)

  beforeEach(() => useOverviewTabPanelMock.mockReturnValue(makeController()))

  it('renders the level block with both thresholds, remaining XP and an accessible progress value', () => {
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(screen.getByText('05')).toBeVisible()
    expect(screen.getByText('1.240 XP acumulados')).toBeVisible()
    expect(screen.getByText('1.000 XP')).toBeVisible()
    expect(screen.getByText('1.500 XP')).toBeVisible()
    expect(screen.getByText('260 XP para o próximo nível')).toBeVisible()

    const progress = screen.getByRole('progressbar', {
      name: 'Progresso para o nível 6',
    })
    expect(progress).toHaveAttribute('aria-valuenow', '48')
    expect(progress).toHaveAttribute('aria-valuetext', '48% concluído, faltam 260 XP')
  })

  it('renders the streak block with the record, today line and seven named days', () => {
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(screen.getByText('3')).toBeVisible()
    expect(screen.getByText('dias seguidos')).toBeVisible()
    expect(screen.getByText(/Maior sequência: 9 dias/)).toBeVisible()
    expect(screen.getByText(/Hoje, 15 de setembro/)).toBeVisible()
    expect(screen.getByText('Pratique hoje para manter sua sequência.')).toBeVisible()

    const strip = screen.getByRole('list', { name: 'Últimos sete dias' })
    const days = within(strip).getAllByRole('listitem')
    expect(days).toHaveLength(7)
    expect(days[0]).toHaveAccessibleName('9 de setembro, sem registro')
    expect(days[1]).toHaveAccessibleName('10 de setembro, dia encerrado sem prática')
    expect(days[2]).toHaveAccessibleName('11 de setembro, dia de prática')
    expect(days[3]).toHaveAccessibleName('12 de setembro, dia da sequência atual')
    expect(days[6]).toHaveAccessibleName('15 de setembro, hoje, prática ainda pendente')
  })

  it('confirms today as practised when the day is no longer pending', () => {
    useOverviewTabPanelMock.mockReturnValue(
      makeController({
        overview: {
          ...overview,
          streak: { ...overview.streak, isTodayPending: false },
        },
      }),
    )
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(screen.getByText('Você já praticou hoje.')).toBeVisible()
  })

  it('renders the obtained ratio and each recent achievement with its own stored text', () => {
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    const summary = screen
      .getByRole('heading', { name: 'Suas conquistas' })
      .closest('section')
    expect(summary).toHaveTextContent('4 de 12 obtidas')

    const list = screen.getByRole('list', { name: 'Conquistas recentes' })
    const rows = within(list).getAllByRole('listitem')
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveAccessibleName(
      'Consistência II, 7 dias consecutivos, +50 XP, em 13 set 2026',
    )
    expect(rows[1]).toHaveAccessibleName(
      'Primeiro Passo, 1 diagnóstico concluído, +25 XP, em 11 set 2026',
    )
  })

  it('opens the Conquistas tab from the shortcut by pointer and by keyboard', async () => {
    const onViewAchievements = vi.fn()
    render(<OverviewTabPanel onViewAchievements={onViewAchievements} />)

    const shortcut = screen.getByRole('button', { name: 'Ver todas as conquistas' })
    await userEvent.click(shortcut)
    expect(onViewAchievements).toHaveBeenCalledOnce()

    shortcut.focus()
    await userEvent.keyboard('{Enter}')
    expect(onViewAchievements).toHaveBeenCalledTimes(2)
  })

  it('states that XP and level do not represent knowledge', () => {
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(
      screen.getByText(
        /não representam seu conhecimento nem o domínio das suas Competências/,
      ),
    ).toBeVisible()
  })

  it('announces the loading state', () => {
    useOverviewTabPanelMock.mockReturnValue(
      makeController({ state: 'loading', overview: null }),
    )
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(screen.getByLabelText('Carregando sua visão geral')).toBeVisible()
  })

  it('offers a working retry on the error state and disables it while retrying', () => {
    const handleRetry = vi.fn()
    useOverviewTabPanelMock.mockReturnValue(
      makeController({ state: 'error', overview: null, handleRetry }),
    )
    const { rerender } = render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(
      screen.getByRole('heading', {
        name: 'Não foi possível carregar sua visão geral',
      }),
    ).toBeVisible()
    screen.getByRole('button', { name: 'Tentar novamente' }).click()
    expect(handleRetry).toHaveBeenCalledOnce()

    useOverviewTabPanelMock.mockReturnValue(
      makeController({
        state: 'error',
        overview: null,
        isRetrying: true,
        handleRetry,
      }),
    )
    rerender(<OverviewTabPanel onViewAchievements={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('explains the initial state without fabricating a value', () => {
    useOverviewTabPanelMock.mockReturnValue(
      makeController({ state: 'empty', overview: null }),
    )
    render(<OverviewTabPanel onViewAchievements={vi.fn()} />)

    expect(
      screen.getByRole('heading', { name: 'Sua jornada começa agora' }),
    ).toBeVisible()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('list', { name: 'Últimos sete dias' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByText(
        /não representam seu conhecimento nem o domínio das suas Competências/,
      ),
    ).toBeVisible()
  })
})
