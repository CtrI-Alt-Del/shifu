import { createRef } from 'react'

import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { ForgotPasswordPage } from '..'
import { useForgotPasswordPage } from '../use-forgot-password-page'

vi.mock('../use-forgot-password-page', () => ({ useForgotPasswordPage: vi.fn() }))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

const useForgotPasswordPageMock = vi.mocked(useForgotPasswordPage)

function createPageState(overrides: Record<string, unknown> = {}) {
  return {
    email: '',
    emailError: null,
    handleRetry: vi.fn(),
    handleStartOver: vi.fn(),
    isRetrying: false,
    isSubmitting: false,
    message: null,
    mode: 'form' as const,
    retryAfterSeconds: null,
    setEmail: vi.fn(),
    status: 'loading' as const,
    statusRef: createRef<HTMLElement>(),
    submit: vi.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof useForgotPasswordPage>
}

describe('ForgotPasswordPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useForgotPasswordPageMock.mockReturnValue(createPageState())
  })

  it('renders the accessible public request form and login link', () => {
    render(<ForgotPasswordPage />)

    expect(screen.getByRole('heading', { name: 'Esqueci minha senha' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toBeEnabled()
    expect(
      screen.getByRole('button', { name: 'Enviar link de recuperação' }),
    ).toBeEnabled()
    expect(screen.getByRole('link', { name: 'Voltar para entrar' })).toHaveAttribute(
      'href',
      ROUTES.login,
    )
  })

  it('renders validation and pending states without hiding the entered address', () => {
    useForgotPasswordPageMock.mockReturnValue(
      createPageState({
        email: 'ana@example.com',
        emailError: 'Informe um e-mail válido.',
        isSubmitting: true,
        message: 'Revise o campo destacado.',
      }),
    )

    render(<ForgotPasswordPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Revise o campo destacado.')
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toHaveValue('ana@example.com')
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toBeDisabled()
  })

  it('renders generic delivery recovery and delegates both actions', () => {
    const pageState = createPageState({
      handleRetry: vi.fn(),
      mode: 'status',
      status: 'delivery_issue',
    })
    useForgotPasswordPageMock.mockReturnValue(pageState)

    render(<ForgotPasswordPage />)

    expect(
      screen.getByRole('heading', { name: 'Não foi possível entregar o link' }),
    ).toBeVisible()
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Usar outro e-mail' })).toBeEnabled()
  })
})
