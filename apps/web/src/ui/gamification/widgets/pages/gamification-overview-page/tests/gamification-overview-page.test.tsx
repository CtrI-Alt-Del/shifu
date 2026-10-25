import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { GamificationOverview } from '@/core/gamification/overview'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { GamificationOverviewPage } from '..'
import {
  type GamificationOverviewPageController,
  useGamificationOverviewPage,
} from '../use-gamification-overview-page'
import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

// Counters and entrance motion settle at once, so text assertions see final
// values; the animation cases opt back into motion explicitly.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-gamification-overview-page', () => ({
  useGamificationOverviewPage: vi.fn(),
}))
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

// Counters render the number in its own element, so whole sentences are
// matched on the paragraph that holds them.
function paragraph(text: string) {
  return (_: string, element: Element | null) =>
    element?.tagName === 'P' && element.textContent === text
}

const useGamificationOverviewPageMock = vi.mocked(useGamificationOverviewPage)

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
  overrides: Partial<GamificationOverviewPageController> = {},
): GamificationOverviewPageController {
  return {
    overview,
    state: 'success',
    isRetrying: false,
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('GamificationOverviewPage', () => {
  afterEach(() => {
    cleanup()
    vi.mocked(useReducedMotionPreference).mockReturnValue({ prefersReducedMotion: true })
  })

  beforeEach(() => useGamificationOverviewPageMock.mockReturnValue(makeController()))

  it('renders the level block with both thresholds, remaining XP and an accessible progress value', () => {
    render(<GamificationOverviewPage />)

    expect(screen.getByRole('heading', { level: 3, name: 'Nível 5' })).toBeVisible()
    expect(screen.getByText('1.240 XP')).toBeVisible()
    expect(screen.getByText('acumulados')).toBeVisible()
    expect(screen.getByText('Nível 5 · 1.000 XP')).toBeVisible()
    expect(screen.getByText('Nível 6 · 1.500 XP')).toBeVisible()
    expect(screen.getByText(paragraph('260 XP para alcançar o nível 6'))).toBeVisible()

    const progress = screen.getByRole('progressbar', {
      name: 'Progresso para o nível 6',
    })
    expect(progress).toHaveAttribute('aria-valuenow', '48')
    expect(progress).toHaveAttribute('aria-valuetext', '48% concluído, faltam 260 XP')
  })

  it('grows the level fill from empty to the current percentage', async () => {
    vi.mocked(useReducedMotionPreference).mockReturnValue({ prefersReducedMotion: false })
    render(<GamificationOverviewPage />)

    const fill = screen.getByRole('progressbar', { name: 'Progresso para o nível 6' })
      .firstElementChild as HTMLElement
    expect(fill.style.width).toBe('0%')
    await waitFor(() => expect(fill.style.width).toBe('48%'), { timeout: 3000 })
  })

  it('counts the XP total, remaining XP and streak up to their final values', async () => {
    vi.mocked(useReducedMotionPreference).mockReturnValue({ prefersReducedMotion: false })
    render(<GamificationOverviewPage />)

    // The entrance fade is still running, so presence is asserted here and
    // visibility is covered by the reduced-motion cases.
    expect(screen.getByText('0 XP')).toBeInTheDocument()
    await waitFor(
      () => {
        expect(screen.getByText('1.240 XP')).toBeInTheDocument()
        expect(
          screen.getByText(paragraph('260 XP para alcançar o nível 6')),
        ).toBeInTheDocument()
        expect(screen.getByText(paragraph('Recorde: 9 dias'))).toBeInTheDocument()
      },
      { timeout: 3000 },
    )
  })

  it('shows the level fill at its final width when motion is reduced', async () => {
    render(<GamificationOverviewPage />)

    const fill = screen.getByRole('progressbar', { name: 'Progresso para o nível 6' })
      .firstElementChild as HTMLElement
    expect(fill.style.width).toBe('48%')
  })

  it('renders the streak block with the record, today guidance and seven named days', () => {
    render(<GamificationOverviewPage />)

    expect(screen.getByRole('heading', { name: 'Constância' })).toBeVisible()
    expect(screen.getByText('3')).toBeVisible()
    expect(screen.getByText('dias seguidos')).toBeVisible()
    expect(screen.getByText(paragraph('Recorde: 9 dias'))).toBeVisible()
    expect(screen.getByText('Pratique hoje para manter a sequência.')).toBeVisible()

    const strip = screen.getByRole('list', { name: 'Últimos sete dias' })
    const days = within(strip).getAllByRole('listitem')
    expect(days).toHaveLength(7)
    expect(days[0]).toHaveAccessibleName('9 de setembro, sem registro')
    expect(days[1]).toHaveAccessibleName('10 de setembro, dia encerrado sem prática')
    expect(days[2]).toHaveAccessibleName('11 de setembro, dia de prática')
    expect(days[3]).toHaveAccessibleName('12 de setembro, dia da sequência atual')
    expect(days[6]).toHaveAccessibleName('15 de setembro, hoje, prática ainda pendente')
    expect(days[6]).toHaveTextContent('Hoje')
    expect(days[5]).toHaveTextContent('Seg14')
  })

  it('confirms today as practised when the day is no longer pending', () => {
    useGamificationOverviewPageMock.mockReturnValue(
      makeController({
        overview: {
          ...overview,
          streak: { ...overview.streak, isTodayPending: false },
        },
      }),
    )
    render(<GamificationOverviewPage />)

    expect(screen.getByText('Você já praticou hoje.')).toBeVisible()
  })

  it('renders the obtained ratio and each recent achievement with its own stored text', () => {
    render(<GamificationOverviewPage />)

    const summary = screen
      .getByRole('heading', { name: 'Conquistas recentes' })
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

  it('links the shortcut to the Conquistas route', () => {
    render(<GamificationOverviewPage />)

    expect(screen.getByRole('link', { name: 'Ver todas as conquistas' })).toHaveAttribute(
      'href',
      ROUTES.gamificationAchievements,
    )
  })

  it('states that XP does not measure Competency mastery', () => {
    render(<GamificationOverviewPage />)

    expect(
      screen.getByText(
        /XP reconhece sua prática\. O domínio das Competências é acompanhado nas Habilidades\./,
      ),
    ).toBeVisible()
  })

  it('renders the singular streak counts and the achievements empty sub-state', () => {
    useGamificationOverviewPageMock.mockReturnValue(
      makeController({
        overview: {
          ...overview,
          streak: { ...overview.streak, streak: { current: 1, longest: 1 } },
          achievements: { ...overview.achievements, recent: [] },
        },
      }),
    )
    render(<GamificationOverviewPage />)

    expect(screen.getByText('dia seguido')).toBeVisible()
    expect(screen.getByText(paragraph('Recorde: 1 dia'))).toBeVisible()
    expect(
      screen.getByText(/Você ainda não obteve conquistas\. Continue praticando/),
    ).toBeVisible()
    expect(
      screen.queryByRole('list', { name: 'Conquistas recentes' }),
    ).not.toBeInTheDocument()
  })

  it('announces the loading state', () => {
    useGamificationOverviewPageMock.mockReturnValue(
      makeController({ state: 'loading', overview: null }),
    )
    render(<GamificationOverviewPage />)

    expect(screen.getByLabelText('Carregando sua visão geral')).toBeVisible()
  })

  it('offers a working retry on the error state and disables it while retrying', () => {
    const handleRetry = vi.fn()
    useGamificationOverviewPageMock.mockReturnValue(
      makeController({ state: 'error', overview: null, handleRetry }),
    )
    const { rerender } = render(<GamificationOverviewPage />)

    expect(
      screen.getByRole('heading', {
        name: 'Não foi possível carregar sua visão geral',
      }),
    ).toBeVisible()
    screen.getByRole('button', { name: 'Tentar novamente' }).click()
    expect(handleRetry).toHaveBeenCalledOnce()

    useGamificationOverviewPageMock.mockReturnValue(
      makeController({
        state: 'error',
        overview: null,
        isRetrying: true,
        handleRetry,
      }),
    )
    rerender(<GamificationOverviewPage />)
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })

  it('explains the initial state without fabricating a value', () => {
    useGamificationOverviewPageMock.mockReturnValue(
      makeController({ state: 'empty', overview: null }),
    )
    render(<GamificationOverviewPage />)

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
