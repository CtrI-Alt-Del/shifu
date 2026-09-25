import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PendingConfirmationPage } from '..'
import { usePendingConfirmationPage } from '../use-pending-confirmation-page'

vi.mock('../use-pending-confirmation-page', () => ({
  usePendingConfirmationPage: vi.fn(),
}))

const usePendingConfirmationPageMock = vi.mocked(usePendingConfirmationPage)
const handleExitMock = vi.fn()

type PendingConfirmationController = ReturnType<typeof usePendingConfirmationPage>

function createController(
  overrides: Partial<PendingConfirmationController> = {},
): PendingConfirmationController {
  return {
    alertRef: { current: null },
    errorMessage: null,
    handleExit: handleExitMock,
    isExiting: false,
    status: 'idle',
    ...overrides,
  }
}

describe('PendingConfirmationPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    usePendingConfirmationPageMock.mockReturnValue(createController())
  })

  it('renders the restricted confirmation state with a standalone Sair action', () => {
    render(<PendingConfirmationPage />)

    expect(screen.getByRole('heading', { name: 'Aguardando confirmação' })).toBeVisible()
    expect(screen.getByText(/Confirme seu e-mail/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Sair' })).toBeEnabled()
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(handleExitMock).toHaveBeenCalledOnce()
  })

  it('renders pending, safe failure and success states', () => {
    usePendingConfirmationPageMock.mockReturnValue(
      createController({ isExiting: true, status: 'pending' }),
    )
    const { rerender } = render(<PendingConfirmationPage />)

    expect(screen.getByRole('button', { name: 'Saindo...' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Saindo...' })).toHaveAttribute(
      'aria-busy',
      'true',
    )

    usePendingConfirmationPageMock.mockReturnValue(
      createController({
        errorMessage: 'Não foi possível sair agora. Tente novamente.',
        status: 'error',
      }),
    )
    rerender(<PendingConfirmationPage />)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Não foi possível sair agora. Tente novamente.',
    )
    expect(screen.getByRole('button', { name: 'Sair' })).toBeEnabled()

    usePendingConfirmationPageMock.mockReturnValue(
      createController({ status: 'success' }),
    )
    rerender(<PendingConfirmationPage />)
    expect(screen.getByRole('status')).toHaveTextContent(
      'Saída concluída. Redirecionando para Entrar...',
    )
    expect(screen.queryByRole('button', { name: 'Sair' })).not.toBeInTheDocument()
  })
})
