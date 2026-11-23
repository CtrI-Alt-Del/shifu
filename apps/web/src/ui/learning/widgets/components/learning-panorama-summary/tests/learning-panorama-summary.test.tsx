import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { LearningPanoramaSummary } from '..'
import { useLearningPanoramaSummary } from '../use-learning-panorama-summary'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))
vi.mock('../use-learning-panorama-summary', () => ({
  useLearningPanoramaSummary: vi.fn(),
}))

const useLearningPanoramaSummaryMock = vi.mocked(useLearningPanoramaSummary)
const handleRetryMock = vi.fn()

function makeHookValue(
  overrides: Partial<ReturnType<typeof useLearningPanoramaSummary>> = {},
): ReturnType<typeof useLearningPanoramaSummary> {
  return {
    state: 'success',
    cards: [
      { key: 'completed-skills', caption: 'Habilidades concluídas', value: 3 },
      { key: 'mastered-competencies', caption: 'Competências dominadas', value: 1400 },
    ],
    isRetrying: false,
    formatCount: (value) => value.toLocaleString('pt-BR'),
    handleRetry: handleRetryMock,
    ...overrides,
  }
}

describe('LearningPanoramaSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useLearningPanoramaSummaryMock.mockReturnValue(makeHookValue())
  })

  afterEach(() => {
    cleanup()
  })

  it('renders both Aprendizagem cards with their formatted counts and captions', () => {
    render(<LearningPanoramaSummary />)

    const completed = screen.getByRole('article', { name: 'Habilidades concluídas' })
    const mastered = screen.getByRole('article', { name: 'Competências dominadas' })

    expect(within(completed).getByText('Aprendizagem')).toBeVisible()
    expect(within(completed).getByText('3')).toBeVisible()
    expect(within(mastered).getByText('Aprendizagem')).toBeVisible()
    expect(within(mastered).getByText('1.400')).toBeVisible()
  })

  it('marks the Aprendizagem cards with the jade family only', () => {
    const { container } = render(<LearningPanoramaSummary />)

    const markers = container.querySelectorAll('span[aria-hidden="true"].rounded-full')
    expect(markers).toHaveLength(2)
    for (const marker of markers) {
      expect(marker).toHaveClass('bg-jade-fill')
      expect(marker).not.toHaveClass('bg-latao-fill')
    }
  })

  it('does not use engagement vocabulary in the learning cards', () => {
    render(<LearningPanoramaSummary />)

    expect(screen.queryByText(/XP|nível|sequência/i)).not.toBeInTheDocument()
  })

  it('renders zero counts when the account has no Objetivo yet', () => {
    useLearningPanoramaSummaryMock.mockReturnValue(
      makeHookValue({
        state: 'empty',
        cards: [
          { key: 'completed-skills', caption: 'Habilidades concluídas', value: 0 },
          { key: 'mastered-competencies', caption: 'Competências dominadas', value: 0 },
        ],
      }),
    )

    render(<LearningPanoramaSummary />)

    expect(
      within(screen.getByRole('article', { name: 'Habilidades concluídas' })).getByText(
        '0',
      ),
    ).toBeVisible()
    expect(
      within(screen.getByRole('article', { name: 'Competências dominadas' })).getByText(
        '0',
      ),
    ).toBeVisible()
  })

  it('shows a busy placeholder per card while the panorama loads', () => {
    useLearningPanoramaSummaryMock.mockReturnValue(makeHookValue({ state: 'loading' }))

    render(<LearningPanoramaSummary />)

    expect(
      screen.getByRole('status', { name: 'Carregando Habilidades concluídas' }),
    ).toHaveAttribute('aria-busy', 'true')
    expect(
      screen.getByRole('status', { name: 'Carregando Competências dominadas' }),
    ).toHaveAttribute('aria-busy', 'true')
    expect(screen.queryByText('Aprendizagem')).not.toBeInTheDocument()
  })

  it('shows an unavailable state on each card with a working retry', () => {
    useLearningPanoramaSummaryMock.mockReturnValue(makeHookValue({ state: 'error' }))

    render(<LearningPanoramaSummary />)

    expect(screen.getAllByRole('alert')).toHaveLength(2)
    expect(screen.getAllByText('Indisponível no momento.')).toHaveLength(2)
    expect(screen.getByText('Habilidades concluídas')).toBeVisible()
    expect(screen.getByText('Competências dominadas')).toBeVisible()

    const retryButtons = screen.getAllByRole('button', { name: 'Tentar novamente' })
    expect(retryButtons).toHaveLength(2)

    fireEvent.click(retryButtons[0])

    expect(handleRetryMock).toHaveBeenCalledTimes(1)
  })

  it('disables the retry buttons while a retry is in flight', () => {
    useLearningPanoramaSummaryMock.mockReturnValue(
      makeHookValue({ state: 'error', isRetrying: true }),
    )

    render(<LearningPanoramaSummary />)

    for (const button of screen.getAllByRole('button', { name: 'Tentar novamente' })) {
      expect(button).toBeDisabled()
    }
  })
})
