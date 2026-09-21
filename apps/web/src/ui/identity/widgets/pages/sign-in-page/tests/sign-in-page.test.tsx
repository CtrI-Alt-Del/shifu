import { createRef } from 'react'
import type { ReactNode } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { SignInPageStatus } from '../use-sign-in-page'
import { SignInPage } from '..'

const state = {
  alertRef: createRef<HTMLDivElement>(),
  form: {
    Field: ({
      children,
      name,
    }: {
      children: (field: {
        handleBlur: () => void
        handleChange: (value: string) => void
        name: string
        state: { value: string }
      }) => ReactNode
      name: string
    }) =>
      children({
        handleBlur: vi.fn(),
        handleChange: vi.fn(),
        name,
        state: { value: '' },
      }),
  },
  email: '',
  isPasswordVisible: false,
  isSubmitting: false,
  message: null as string | null,
  password: '',
  setEmail: vi.fn(),
  setPassword: vi.fn(),
  setPasswordVisible: vi.fn(),
  status: 'idle' as SignInPageStatus,
  submit: vi.fn((event: React.FormEvent<HTMLFormElement>) => event.preventDefault()),
}

vi.mock('../use-sign-in-page', () => ({
  useSignInPage: () => state,
}))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

describe('SignInPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    state.email = ''
    state.password = ''
    state.message = null
    state.isSubmitting = false
    state.isPasswordVisible = false
    state.status = 'idle'
    vi.clearAllMocks()
  })

  it('renders the accessible public form and canonical adjacent links', () => {
    render(<SignInPage />)

    expect(screen.getByRole('heading', { name: 'Entrar' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toHaveAttribute(
      'type',
      'email',
    )
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toHaveValue('')
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toHaveAttribute(
      'placeholder',
      'voce@exemplo.com',
    )
    expect(screen.getByLabelText('Senha')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText('Senha')).toHaveValue('')
    expect(screen.getByLabelText('Senha')).toHaveAttribute('placeholder', '••••••••')
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled()
    expect(screen.getByRole('link', { name: 'Esqueci minha senha' })).toHaveAttribute(
      'href',
      ROUTES.forgotPassword,
    )
    expect(screen.getByRole('link', { name: 'Criar conta' })).toHaveAttribute(
      'href',
      ROUTES.register,
    )
  })

  it('renders the submitting and error contracts without removing navigation', () => {
    state.isSubmitting = true
    state.message = 'Não foi possível entrar agora. Tente novamente.'
    state.status = 'unavailable'
    render(<SignInPage />)

    expect(screen.getByRole('alert')).toHaveTextContent(state.message)
    expect(screen.getByRole('button', { name: /Entrando/ })).toBeDisabled()
    expect(screen.getByLabelText('E-mail')).toBeDisabled()
    expect(screen.getByLabelText('Senha')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mostrar senha' })).toBeDisabled()
    expect(screen.getByRole('link', { name: 'Criar conta' })).toBeVisible()
  })

  it('delegates password visibility to the page hook', () => {
    render(<SignInPage />)

    fireEvent.click(screen.getByRole('button', { name: 'Mostrar senha' }))
    expect(state.setPasswordVisible).toHaveBeenCalledOnce()
  })
})
