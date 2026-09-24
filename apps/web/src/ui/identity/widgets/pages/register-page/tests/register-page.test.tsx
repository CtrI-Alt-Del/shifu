import { createRef, type ReactNode } from 'react'

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { RegisterPage } from '..'
import { useRegisterPage } from '../use-register-page'

vi.mock('../use-register-page', () => ({ useRegisterPage: vi.fn() }))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

const useRegisterPageMock = vi.mocked(useRegisterPage)

function createPageState(overrides: Record<string, unknown> = {}) {
  return {
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
          state: { meta: { errors: unknown[] }; value: string }
        }) => ReactNode
        name: string
      }) =>
        children({
          handleBlur: vi.fn(),
          handleChange: vi.fn(),
          name,
          state: { meta: { errors: [] }, value: '' },
        }),
    },
    isSubmitting: false,
    message: null,
    submit: vi.fn((event: React.FormEvent<HTMLFormElement>) => event.preventDefault()),
    ...overrides,
  } as unknown as ReturnType<typeof useRegisterPage>
}

describe('RegisterPage', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useRegisterPageMock.mockReturnValue(createPageState())
  })

  it('renders public fields, password guidance, and the canonical login link', () => {
    render(<RegisterPage />)

    expect(screen.getByRole('heading', { name: 'Criar conta' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Nome de exibição' })).toBeEnabled()
    expect(screen.getByRole('textbox', { name: 'E-mail' })).toHaveAttribute(
      'type',
      'email',
    )
    expect(screen.getByLabelText('Senha')).toHaveAttribute('minLength', '8')
    expect(screen.getByText('Use pelo menos 8 caracteres.')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Entrar' })).toHaveAttribute(
      'href',
      ROUTES.login,
    )
  })

  it('renders field and submission errors returned by the page hook', () => {
    useRegisterPageMock.mockReturnValue(
      createPageState({
        form: {
          Field: ({
            children,
            name,
          }: {
            children: (field: {
              handleBlur: () => void
              handleChange: (value: string) => void
              name: string
              state: { meta: { errors: unknown[] }; value: string }
            }) => ReactNode
            name: string
          }) =>
            children({
              handleBlur: vi.fn(),
              handleChange: vi.fn(),
              name,
              state: {
                meta: { errors: name === 'email' ? ['Informe um e-mail válido.'] : [] },
                value: '',
              },
            }),
        },
        message: 'Revise os campos destacados',
      }),
    )

    render(<RegisterPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('Revise os campos destacados')
    expect(screen.getByText('Informe um e-mail válido.')).toBeVisible()
  })

  it('disables fields and delegates submission while registration is pending', () => {
    const pageState = createPageState({ isSubmitting: true })
    useRegisterPageMock.mockReturnValue(pageState)

    render(<RegisterPage />)
    fireEvent.submit(screen.getByRole('form', { name: 'Criar conta no Shifu' }))

    expect(screen.getByRole('button', { name: /Criando conta/ })).toBeDisabled()
    expect(screen.getByLabelText('Nome de exibição')).toBeDisabled()
    expect(screen.getByLabelText('E-mail')).toBeDisabled()
    expect(screen.getByLabelText('Senha')).toBeDisabled()
    expect(pageState.submit).toHaveBeenCalledOnce()
  })
})
