import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PendingConfirmationPage } from '..'
import { usePendingConfirmationPage } from '../use-pending-confirmation-page'

vi.mock('../use-pending-confirmation-page', () => ({
  usePendingConfirmationPage: vi.fn(),
}))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children }: { children: ReactNode }) => <a href='/login'>{children}</a>,
}))

const usePendingConfirmationPageMock = vi.mocked(usePendingConfirmationPage)
const handleExitMock = vi.fn()
const handleResendMock = vi.fn()

type PendingConfirmationController = ReturnType<typeof usePendingConfirmationPage>

function createController(
  overrides: Partial<PendingConfirmationController> = {},
): PendingConfirmationController {
  return {
    alertRef: { current: null },
    exitErrorMessage: null,
    handleExit: handleExitMock,
    handleResend: handleResendMock,
    isExiting: false,
    isLoading: false,
    isResending: false,
    message: null,
    remainingSeconds: 0,
    state: 'ready',
    ...overrides,
  }
}

describe('PendingConfirmationPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    usePendingConfirmationPageMock.mockReturnValue(createController())
  })

  it('renders restricted confirmation actions', () => {
    render(<PendingConfirmationPage />)

    expect(screen.getByRole('heading', { name: 'Confirme seu e-mail' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Reenviar link' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))

    expect(handleResendMock).toHaveBeenCalledOnce()
    expect(handleExitMock).toHaveBeenCalledOnce()
  })

  it('announces a delivery issue and disables both pending actions', () => {
    usePendingConfirmationPageMock.mockReturnValue(
      createController({
        exitErrorMessage: 'Não foi possível sair agora. Tente novamente.',
        isExiting: true,
        isResending: true,
        message: 'Não foi possível entregar o link. Você pode tentar reenviar.',
        remainingSeconds: 24,
        state: 'delivery_issue',
      }),
    )
    render(<PendingConfirmationPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível sair agora')
    expect(screen.getByRole('button', { name: 'Reenviando...' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Saindo...' })).toBeDisabled()
  })
})
