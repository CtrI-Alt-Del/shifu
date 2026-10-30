import { Activity, createElement, type PropsWithChildren } from 'react'
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthError } from '@/core/errors/auth-error'
import { useSecurityForm } from '../use-security-form'
import { useChangeAccountPasswordAction } from '../use-change-account-password-action'
vi.mock('../use-change-account-password-action', () => ({
  useChangeAccountPasswordAction: vi.fn(),
}))
const useChangeAccountPasswordActionMock = vi.mocked(useChangeAccountPasswordAction)
const changeAccountPasswordMock = vi.fn()
const EVENT = {
  preventDefault: vi.fn(),
  stopPropagation: vi.fn(),
} as unknown as React.FormEvent<HTMLFormElement>
describe('useSecurityForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    changeAccountPasswordMock.mockResolvedValue({ changed: true })
    useChangeAccountPasswordActionMock.mockReturnValue({
      isPending: false,
      error: null,
      changeAccountPassword: changeAccountPasswordMock,
    })
  })
  it('validates current and new password without submitting', async () => {
    const { result } = renderHook(useSecurityForm)
    await act(async () => result.current.handleSubmit(EVENT))
    expect(result.current.errors.currentPassword).toBeDefined()
    expect(result.current.errors.newPassword).toBeDefined()
    expect(changeAccountPasswordMock).not.toHaveBeenCalled()
  })
  it.each(['12345678', '        ', '😀😀😀😀😀😀😀😀'])(
    'preserves whitespace and accepts eight Unicode characters',
    async (password) => {
      const { result } = renderHook(useSecurityForm)
      act(() => {
        result.current.handleCurrentPasswordChange(password)
        result.current.handleNewPasswordChange(password)
        result.current.handleTogglePasswordVisibility()
      })
      expect(result.current.isPasswordVisible).toBe(true)
      await act(async () => result.current.handleSubmit(EVENT))
      expect(changeAccountPasswordMock).toHaveBeenCalledWith({
        currentPassword: password,
        newPassword: password,
      })
      expect(result.current.isSuccess).toBe(true)
      expect(result.current.message).toContain('Este continua')
      expect(result.current.currentPassword).toBe('')
      expect(result.current.newPassword).toBe('')
      expect(result.current.isPasswordVisible).toBe(false)
    },
  )
  it.each(['invalid-current-password', 'result-uncertain', 'unavailable'] as const)(
    'clears secrets and exposes %s without retry',
    async (kind) => {
      changeAccountPasswordMock.mockRejectedValue(new AuthError(kind, 'Falha segura.'))
      const { result } = renderHook(useSecurityForm)
      act(() => {
        result.current.handleCurrentPasswordChange('old-password')
        result.current.handleNewPasswordChange('new-password')
      })
      await act(async () => result.current.handleSubmit(EVENT))
      expect(result.current.currentPassword).toBe('')
      expect(result.current.newPassword).toBe('')
      expect(result.current.message).toBe('Falha segura.')
      expect(result.current.isSuccess).toBe(false)
      expect(changeAccountPasswordMock).toHaveBeenCalledOnce()
      expect(result.current.errors.currentPassword).toBe(
        kind === 'invalid-current-password' ? 'Falha segura.' : undefined,
      )
    },
  )
  it('clears passwords and visibility when the mounted security activity becomes hidden', () => {
    let mode: 'visible' | 'hidden' = 'visible'
    function ActivityWrapper({ children }: PropsWithChildren) {
      return createElement(Activity, { mode, children })
    }
    const { result, rerender } = renderHook(useSecurityForm, { wrapper: ActivityWrapper })
    act(() => {
      result.current.handleCurrentPasswordChange('secret-current')
      result.current.handleNewPasswordChange('secret-new')
      result.current.handleTogglePasswordVisibility()
    })
    mode = 'hidden'
    rerender()
    mode = 'visible'
    rerender()
    expect(result.current.currentPassword).toBe('')
    expect(result.current.newPassword).toBe('')
    expect(result.current.isPasswordVisible).toBe(false)
  })
  it('rejects seven Unicode characters', async () => {
    const { result } = renderHook(useSecurityForm)
    act(() => {
      result.current.handleCurrentPasswordChange('old-password')
      result.current.handleNewPasswordChange('😀'.repeat(7))
    })
    await act(async () => result.current.handleSubmit(EVENT))
    expect(result.current.errors.newPassword).toBeDefined()
    expect(changeAccountPasswordMock).not.toHaveBeenCalled()
  })
  it('guards concurrent submissions until settled', async () => {
    let resolveChange: (value: { changed: true }) => void = () => undefined
    changeAccountPasswordMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveChange = resolve
        }),
    )
    const { result } = renderHook(useSecurityForm)
    act(() => {
      result.current.handleCurrentPasswordChange('old-password')
      result.current.handleNewPasswordChange('new-password')
    })
    act(() => {
      void result.current.handleSubmit(EVENT)
      void result.current.handleSubmit(EVENT)
    })
    await waitFor(() => expect(changeAccountPasswordMock).toHaveBeenCalledOnce())
    await act(async () => resolveChange({ changed: true }))
    expect(result.current.isSuccess).toBe(true)
  })
})
