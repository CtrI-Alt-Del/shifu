import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AiQuotaWarningCard } from '..'
import { useAiQuotaWarningCard } from '../use-ai-quota-warning-card'

vi.mock('../use-ai-quota-warning-card', () => ({
  useAiQuotaWarningCard: vi.fn(),
}))

const useAiQuotaWarningCardMock = vi.mocked(useAiQuotaWarningCard)
const handleDismissMock = vi.fn()

function createState(
  overrides: Partial<ReturnType<typeof useAiQuotaWarningCard>> = {},
): ReturnType<typeof useAiQuotaWarningCard> {
  return {
    isDismissed: false,
    message:
      'Você já usou 85% da sua cota de IA deste mês. Quando ela acabar, o Mentor e o planejamento assistido pausam até 1º de dezembro de 2026.',
    handleDismiss: handleDismissMock,
    ...overrides,
  }
}

describe('AiQuotaWarningCard', () => {
  afterEach(cleanup)

  beforeEach(() => {
    handleDismissMock.mockReset()
    useAiQuotaWarningCardMock.mockReturnValue(createState())
  })

  it('announces the warning with an icon-only dismiss button and no usage link', () => {
    render(
      <AiQuotaWarningCard accountId='account-1' percentage={85} renewsOn='2026-12-01' />,
    )

    expect(screen.getByRole('status')).toHaveTextContent(
      'Você já usou 85% da sua cota de IA deste mês. Quando ela acabar, o Mentor e o planejamento assistido pausam até 1º de dezembro de 2026.',
    )
    const dismiss = screen.getByRole('button', { name: 'Dispensar aviso' })
    expect(dismiss).toBeEnabled()
    expect(dismiss).toHaveTextContent('')
    expect(screen.queryByRole('link')).toBeNull()
  })

  it('delegates the dismissal to the owning hook', () => {
    render(
      <AiQuotaWarningCard accountId='account-1' percentage={85} renewsOn='2026-12-01' />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Dispensar aviso' }))

    expect(handleDismissMock).toHaveBeenCalledOnce()
  })

  it('passes its account, percentage and renewal date to the owning hook', () => {
    render(
      <AiQuotaWarningCard accountId='account-1' percentage={85} renewsOn='2026-12-01' />,
    )

    expect(useAiQuotaWarningCardMock).toHaveBeenCalledWith(
      expect.objectContaining({
        accountId: 'account-1',
        percentage: 85,
        renewsOn: '2026-12-01',
      }),
    )
  })

  it('renders nothing once the warning is dismissed', () => {
    useAiQuotaWarningCardMock.mockReturnValue(createState({ isDismissed: true }))

    render(
      <AiQuotaWarningCard accountId='account-1' percentage={85} renewsOn='2026-12-01' />,
    )

    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Dispensar aviso' })).toBeNull()
  })
})
