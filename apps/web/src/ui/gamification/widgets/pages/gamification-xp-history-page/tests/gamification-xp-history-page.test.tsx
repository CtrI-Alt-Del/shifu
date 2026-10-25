import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { XpHistoryEntry } from '@/core/gamification/xp-history'

import { GamificationXpHistoryPage } from '..'
import {
  type GamificationXpHistoryPageController,
  useGamificationXpHistoryPage,
} from '../use-gamification-xp-history-page'

// Entrance motion and counters settle at once, so assertions see the final
// state; the shared components own their own animated cases.
vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-gamification-xp-history-page', () => ({
  useGamificationXpHistoryPage: vi.fn(),
}))

const useGamificationXpHistoryPageMock = vi.mocked(useGamificationXpHistoryPage)

const entries: XpHistoryEntry[] = [
  {
    id: 'grant-1',
    amount: 60,
    source: 'diagnosis',
    title: 'Lógica de programação',
    detail: 'Diagnóstico concluído',
    // The fact happened two days before the concession.
    occurredAt: '2026-09-11T12:00:00Z',
    grantedAt: '2026-09-13T12:00:00Z',
  },
  {
    id: 'grant-2',
    amount: 50,
    source: 'achievement',
    title: 'Consistência II',
    detail: 'Conquista · 7 dias consecutivos',
    occurredAt: '2026-09-08T12:00:00Z',
    grantedAt: '2026-09-08T12:00:00Z',
  },
  {
    id: 'grant-3',
    amount: 50,
    source: 'competency-mastery',
    title: 'Condicionais',
    detail: 'Primeiro domínio de Competência',
    occurredAt: '2026-09-05T12:00:00Z',
    grantedAt: '2026-09-05T12:00:00Z',
  },
  {
    id: 'grant-4',
    amount: 100,
    source: 'skill-completion',
    title: 'Estruturas de dados',
    detail: 'Habilidade concluída',
    occurredAt: '2026-09-02T12:00:00Z',
    grantedAt: '2026-09-02T12:00:00Z',
  },
]

function makeController(
  overrides: Partial<GamificationXpHistoryPageController> = {},
): GamificationXpHistoryPageController {
  return {
    entries,
    totalXp: 260,
    state: 'success',
    isRetrying: false,
    handleRetry: vi.fn(),
    ...overrides,
  }
}

describe('GamificationXpHistoryPage', () => {
  afterEach(cleanup)

  beforeEach(() => useGamificationXpHistoryPageMock.mockReturnValue(makeController()))

  it('announces the loading state before the history resolves', () => {
    useGamificationXpHistoryPageMock.mockReturnValue(
      makeController({ state: 'loading', entries: [], totalXp: 0 }),
    )

    render(<GamificationXpHistoryPage />)

    expect(screen.getByLabelText('Carregando histórico de XP')).toHaveAttribute(
      'aria-busy',
      'true',
    )
    expect(screen.queryByRole('region', { name: 'Registros de XP' })).toBeNull()
  })

  it('renders the summary, the accumulated total and the preservation note', () => {
    render(<GamificationXpHistoryPage />)

    expect(screen.getByRole('heading', { name: 'Histórico de XP' })).toBeVisible()
    expect(
      screen.getByText(
        'Veja de onde veio seu XP, do registro mais recente ao mais antigo.',
      ),
    ).toBeVisible()
    expect(screen.getByText('XP acumulado')).toBeVisible()
    expect(screen.getByText('260 XP')).toBeVisible()
    expect(
      screen.getByText(
        'O XP recebido permanece no histórico mesmo se você remover um objetivo ou uma habilidade.',
      ),
    ).toBeVisible()
  })

  it('renders every record in the order the controller supplies', () => {
    render(<GamificationXpHistoryPage />)

    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(4)
    expect(items[0]).toHaveTextContent('Lógica de programação')
    expect(items[0]).toHaveTextContent('Diagnóstico concluído')
    expect(items[0]).toHaveTextContent('+60 XP')
    expect(items[1]).toHaveTextContent('Consistência II')
    expect(items[1]).toHaveTextContent('Conquista · 7 dias consecutivos')
    expect(items[2]).toHaveTextContent('Condicionais')
    expect(items[2]).toHaveTextContent('Primeiro domínio de Competência')
    expect(items[3]).toHaveTextContent('Estruturas de dados')
    expect(items[3]).toHaveTextContent('Habilidade concluída')
    expect(items[3]).toHaveTextContent('+100 XP')
  })

  it('identifies each record from its text alone, not only its mark', () => {
    render(<GamificationXpHistoryPage />)

    // The origin mark is decorative, so every fact a learner needs must be
    // readable from the row's own text (RP-13: never colour or icon alone).
    const row = screen.getAllByRole('listitem')[0]
    for (const fact of [
      'Lógica de programação',
      'Diagnóstico concluído',
      '13 set 2026',
      '+60 XP',
    ]) {
      expect(row).toHaveTextContent(fact)
    }
  })

  it('shows the fact date only when it differs from the concession date', () => {
    render(<GamificationXpHistoryPage />)

    const items = screen.getAllByRole('listitem')
    expect(within(items[0]).getByText('Fato em 11 set 2026')).toBeVisible()
    expect(within(items[1]).queryByText(/^Fato em/)).toBeNull()
    expect(within(items[2]).queryByText(/^Fato em/)).toBeNull()
  })

  it('offers no navigation from a record to its origin', () => {
    render(<GamificationXpHistoryPage />)

    const records = screen.getByRole('region', { name: 'Registros de XP' })
    expect(within(records).queryAllByRole('link')).toHaveLength(0)
    expect(within(records).queryAllByRole('button')).toHaveLength(0)
  })

  it('explains the empty history without rendering a record list', () => {
    useGamificationXpHistoryPageMock.mockReturnValue(
      makeController({ state: 'empty', entries: [], totalXp: 0 }),
    )

    render(<GamificationXpHistoryPage />)

    expect(
      screen.getByRole('heading', { name: 'Você ainda não recebeu XP' }),
    ).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Registros de XP' })).toBeNull()
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
    expect(screen.getByText('0 XP')).toBeVisible()
  })

  it('announces the error state and retries on request', async () => {
    const handleRetry = vi.fn()
    useGamificationXpHistoryPageMock.mockReturnValue(
      makeController({ state: 'error', entries: [], totalXp: 0, handleRetry }),
    )

    render(<GamificationXpHistoryPage />)

    expect(screen.getByRole('alert')).toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Não foi possível carregar seu histórico' }),
    ).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(handleRetry).toHaveBeenCalledOnce()
  })

  it('disables the retry control while a retry is in flight', () => {
    useGamificationXpHistoryPageMock.mockReturnValue(
      makeController({ state: 'error', entries: [], totalXp: 0, isRetrying: true }),
    )

    render(<GamificationXpHistoryPage />)

    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeDisabled()
  })
})
