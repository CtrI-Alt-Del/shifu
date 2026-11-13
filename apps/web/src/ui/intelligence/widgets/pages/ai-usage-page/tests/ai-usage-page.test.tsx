import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AiUsagePage } from '..'
import { useAiUsagePage } from '../use-ai-usage-page'

vi.mock('../use-ai-usage-page', () => ({ useAiUsagePage: vi.fn() }))

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: () => ({ prefersReducedMotion: true }),
}))

const useAiUsagePageMock = vi.mocked(useAiUsagePage)
const handleRetryMock = vi.fn()

function createState(
  overrides: Partial<ReturnType<typeof useAiUsagePage>> = {},
): ReturnType<typeof useAiUsagePage> {
  return {
    viewState: 'ready',
    status: 'normal',
    percentage: 42,
    renewalText: 'Renova em 1º de dezembro de 2026',
    statusSentence: 'O Mentor e o planejamento assistido estão disponíveis.',
    handleRetry: handleRetryMock,
    ...overrides,
  }
}

describe('AiUsagePage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    handleRetryMock.mockReset()
    useAiUsagePageMock.mockReturnValue(createState())
  })

  it('shows only the percentage, the quota label, the renewal and one status sentence', () => {
    render(<AiUsagePage />)

    expect(screen.getByRole('region', { name: 'Uso da IA' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Uso da IA' })).toBeVisible()
    expect(
      screen.getByText('Quanto da sua cota mensal de IA você já usou.'),
    ).toBeVisible()
    expect(screen.getByText('42%')).toBeVisible()
    expect(screen.getByText('da cota usada')).toBeVisible()
    expect(screen.getByText('Renova em 1º de dezembro de 2026')).toBeVisible()
    expect(
      screen.getByText('O Mentor e o planejamento assistido estão disponíveis.'),
    ).toBeVisible()
    expect(screen.queryByRole('button')).toBeNull()
  })

  it('draws the progress bar for the percentage with the foreground fill', () => {
    render(<AiUsagePage />)

    const bar = screen.getByRole('progressbar', { name: 'Cota de IA usada' })

    expect(bar).toHaveAttribute('aria-valuenow', '42')
    expect(bar.firstElementChild).toHaveClass('bg-foreground')
    expect(screen.getByText('42%')).toHaveClass('font-serif', 'text-foreground')
  })

  it('caps the progress bar at 100 percent', () => {
    useAiUsagePageMock.mockReturnValue(
      createState({ status: 'blocked', percentage: 130 }),
    )

    render(<AiUsagePage />)

    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100')
  })

  it('shows the near-limit state with its sentence', () => {
    useAiUsagePageMock.mockReturnValue(
      createState({
        status: 'near_limit',
        percentage: 85,
        statusSentence:
          'Perto do limite. Quando a cota acabar, o Mentor e o planejamento assistido pausam até a renovação.',
      }),
    )

    render(<AiUsagePage />)

    expect(screen.getByText('85%')).toBeVisible()
    expect(screen.getByText(/^Perto do limite\./)).toHaveClass('text-selo-text')
    expect(screen.getByRole('progressbar').firstElementChild).toHaveClass('bg-selo-text')
  })

  it('shows the exhausted state with a tinted figure and the primary fill', () => {
    useAiUsagePageMock.mockReturnValue(
      createState({
        status: 'blocked',
        percentage: 100,
        statusSentence:
          'Cota esgotada. O Mentor e o planejamento assistido voltam em 1º de dezembro de 2026. Seus Objetivos e Atividades continuam disponíveis.',
      }),
    )

    render(<AiUsagePage />)

    expect(screen.getByText('100%')).toHaveClass('text-selo-text')
    expect(screen.getByRole('progressbar').firstElementChild).toHaveClass('bg-primary')
    expect(screen.getByText(/^Cota esgotada\./)).toBeVisible()
    expect(
      screen.getByText(/Seus Objetivos e Atividades continuam disponíveis/),
    ).toBeVisible()
  })

  it('announces the unavailable state and retries the reading', () => {
    useAiUsagePageMock.mockReturnValue(
      createState({
        viewState: 'unavailable',
        status: null,
        percentage: 0,
        renewalText: '',
        statusSentence: '',
      }),
    )

    render(<AiUsagePage />)

    expect(screen.getByRole('region', { name: 'Uso da IA' })).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível carregar o uso da IA agora. Tente de novo em instantes.',
    )
    expect(screen.queryByText('da cota usada')).toBeNull()

    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toHaveClass(
      'border-control-border!',
    )

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))

    expect(handleRetryMock).toHaveBeenCalledOnce()
  })

  it('shows an accessible loading state without figures while the first reading loads', () => {
    useAiUsagePageMock.mockReturnValue(
      createState({ viewState: 'loading', status: null, percentage: 0 }),
    )

    render(<AiUsagePage />)

    expect(
      screen.getByRole('status', { name: 'Carregando o uso da IA' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('da cota usada')).toBeNull()
    expect(screen.queryByRole('button')).toBeNull()
  })
})
