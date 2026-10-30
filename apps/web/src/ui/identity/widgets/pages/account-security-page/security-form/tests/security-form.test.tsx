import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SecurityForm } from '..'
import { useSecurityForm } from '../use-security-form'
vi.mock('../use-security-form', () => ({ useSecurityForm: vi.fn() }))
const useSecurityFormMock = vi.mocked(useSecurityForm)
function createResult(
  overrides: Partial<ReturnType<typeof useSecurityForm>> = {},
): ReturnType<typeof useSecurityForm> {
  return {
    alertRef: { current: null },
    currentPassword: '',
    newPassword: '',
    errors: {},
    isPending: false,
    isSuccess: false,
    isPasswordVisible: false,
    message: null,
    handleCurrentPasswordChange: vi.fn(),
    handleNewPasswordChange: vi.fn(),
    handleTogglePasswordVisibility: vi.fn(),
    handleSubmit: vi.fn((event) => event.preventDefault()),
    ...overrides,
  }
}
describe('SecurityForm', () => {
  afterEach(cleanup)
  beforeEach(() => useSecurityFormMock.mockReturnValue(createResult()))
  it('shows two password fields without confirmation and delegates input, visibility and submit', () => {
    const result = createResult()
    useSecurityFormMock.mockReturnValue(result)
    render(<SecurityForm />)
    expect(screen.getByRole('form', { name: 'Alterar senha' })).toHaveAttribute(
      'method',
      'post',
    )
    expect(screen.getByLabelText('Senha atual')).toHaveAttribute('type', 'password')
    expect(screen.getByLabelText(/Nova senha/)).toHaveAttribute(
      'autocomplete',
      'new-password',
    )
    fireEvent.change(screen.getByLabelText('Senha atual'), { target: { value: 'old' } })
    fireEvent.change(screen.getByLabelText(/Nova senha/), { target: { value: 'new' } })
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar senhas' }))
    fireEvent.submit(screen.getByRole('form', { name: 'Alterar senha' }))
    expect(result.handleCurrentPasswordChange).toHaveBeenCalledWith('old')
    expect(result.handleNewPasswordChange).toHaveBeenCalledWith('new')
    expect(result.handleTogglePasswordVisibility).toHaveBeenCalledOnce()
    expect(result.handleSubmit).toHaveBeenCalledOnce()
    expect(screen.getByText(/Este continua/)).toBeVisible()
  })
  it('renders pending, field rejection, uncertainty and confirmed success accessibly', () => {
    useSecurityFormMock.mockReturnValue(
      createResult({
        isPending: true,
        errors: {
          currentPassword: 'Senha atual incorreta.',
          newPassword: 'Muito curta.',
        },
        message: 'Resultado não confirmado.',
      }),
    )
    const { rerender } = render(<SecurityForm />)
    expect(screen.getByRole('button', { name: 'Alterando…' })).toBeDisabled()
    expect(screen.getByLabelText('Senha atual')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('alert')).toHaveTextContent('Resultado não confirmado.')
    useSecurityFormMock.mockReturnValue(
      createResult({
        isSuccess: true,
        isPasswordVisible: true,
        message: 'Senha alterada.',
      }),
    )
    rerender(<SecurityForm />)
    expect(screen.getByRole('status')).toHaveTextContent('Senha alterada.')
    expect(screen.getByLabelText('Senha atual')).toHaveAttribute('type', 'text')
    expect(screen.getByRole('button', { name: 'Ocultar senhas' })).toBeVisible()
  })
})
