import { createRef } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { ResetPasswordPage } from '..'
import { useResetPasswordPage } from '../use-reset-password-page'

vi.mock('../use-reset-password-page', () => ({ useResetPasswordPage: vi.fn() }))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

const useResetPasswordPageMock = vi.mocked(useResetPasswordPage)

function createPageState(overrides: Record<string, unknown> = {}) {
  return {
    confirmationError: null,
    handleContinue: vi.fn(),
    handleRetry: vi.fn(),
    handleRequestNewLink: vi.fn(),
    headingRef: createRef<HTMLHeadingElement>(),
    isPasswordVisible: false,
    isSubmitting: false,
    message: null,
    password: '',
    passwordConfirmation: '',
    passwordError: null,
    requiresEmailConfirmation: false,
    result: 'form' as const,
    setPassword: vi.fn(),
    setPasswordConfirmation: vi.fn(),
    setPasswordVisible: vi.fn(),
    submit: vi.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof useResetPasswordPage>
}

describe('ResetPasswordPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useResetPasswordPageMock.mockReturnValue(createPageState())
  })

  it('renders the accessible password and confirmation form', () => {
    render(<ResetPasswordPage token={'a'.repeat(43)} />)

    expect(screen.getByRole('heading', { name: 'Redefinir senha' })).toBeVisible()
    expect(screen.getByLabelText('Nova senha')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Confirmar nova senha')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Redefinir senha' })).toBeEnabled()
  })

  it('renders field validation without losing input values', () => {
    useResetPasswordPageMock.mockReturnValue(
      createPageState({
        confirmationError: 'As senhas precisam ser iguais.',
        message: 'Revise os campos destacados.',
        password: 'password-123',
        passwordConfirmation: 'different',
        passwordError: null,
      }),
    )

    render(<ResetPasswordPage token={'a'.repeat(43)} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Revise os campos destacados.')
    expect(screen.getByText('As senhas precisam ser iguais.')).toBeVisible()
    expect(screen.getByLabelText('Nova senha')).toHaveValue('password-123')
  })

  it('renders successful reset and pending-confirmation explanation', () => {
    useResetPasswordPageMock.mockReturnValue(
      createPageState({
        requiresEmailConfirmation: true,
        result: 'reset',
      }),
    )

    render(<ResetPasswordPage token={'a'.repeat(43)} />)

    expect(screen.getByRole('heading', { name: 'Senha redefinida' })).toBeVisible()
    expect(screen.getByText(/Confirme seu e-mail antes de entrar/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
  })
})
