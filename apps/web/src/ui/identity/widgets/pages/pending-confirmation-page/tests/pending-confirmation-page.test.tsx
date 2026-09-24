import { cleanup, render, screen } from '@testing-library/react'
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

describe('PendingConfirmationPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    usePendingConfirmationPageMock.mockReturnValue({
      alertRef: { current: null },
      handleResend: vi.fn(),
      isLoading: false,
      isResending: false,
      message: null,
      remainingSeconds: 0,
      state: 'ready',
    })
  })

  it('renders the restricted pending state and an operable resend action', () => {
    render(<PendingConfirmationPage />)
    expect(screen.getByRole('heading', { name: 'Confirme seu e-mail' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Reenviar link' })).toBeEnabled()
  })

  it('announces delivery recovery and keeps the cooldown action disabled', () => {
    usePendingConfirmationPageMock.mockReturnValue({
      alertRef: { current: null },
      handleResend: vi.fn(),
      isLoading: false,
      isResending: false,
      message: 'Não foi possível entregar o link. Você pode tentar reenviar.',
      remainingSeconds: 24,
      state: 'delivery_issue',
    })
    render(<PendingConfirmationPage />)
    expect(screen.getByRole('alert')).toHaveTextContent('Não foi possível entregar')
    expect(screen.getByRole('button', { name: 'Reenviar link em 24s' })).toBeDisabled()
  })
})
