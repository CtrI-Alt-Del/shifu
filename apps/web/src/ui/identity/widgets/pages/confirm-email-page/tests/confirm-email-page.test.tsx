import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ConfirmEmailPage } from '..'
import { useConfirmEmailPage } from '../use-confirm-email-page'

vi.mock('../use-confirm-email-page', () => ({ useConfirmEmailPage: vi.fn() }))

const useConfirmEmailPageMock = vi.mocked(useConfirmEmailPage)

describe('ConfirmEmailPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useConfirmEmailPageMock.mockReturnValue({
      handleContinue: vi.fn(),
      headingRef: { current: null },
      redirectTo: 'login',
      result: 'invalid',
    })
  })

  it('renders the invalid recovery state without disclosing account details', () => {
    render(<ConfirmEmailPage />)
    expect(screen.getByRole('heading', { name: 'Link inválido' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
  })

  it('renders same-access continuation only for an activated result', () => {
    useConfirmEmailPageMock.mockReturnValue({
      handleContinue: vi.fn(),
      headingRef: { current: null },
      redirectTo: 'root',
      result: 'activated',
    })
    render(<ConfirmEmailPage />)
    expect(screen.getByRole('button', { name: 'Continuar' })).toBeEnabled()
  })
})
