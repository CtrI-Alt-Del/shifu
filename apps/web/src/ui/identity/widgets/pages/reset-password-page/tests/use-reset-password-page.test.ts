import { act, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useResetPasswordAction } from '@/ui/identity/hooks/use-reset-password-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useResetPasswordPage } from '../use-reset-password-page'

vi.mock('@/ui/identity/hooks/use-reset-password-action', () => ({
  useResetPasswordAction: vi.fn(),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({ useNavigation: vi.fn() }))

const resetPasswordMock = vi.fn()
const getPasswordResetLinkStatusMock = vi.fn()
const navigateToMock = vi.fn()
const useResetPasswordActionMock = vi.mocked(useResetPasswordAction)
const useNavigationMock = vi.mocked(useNavigation)

function submitEvent() {
  return {
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
  } as unknown as FormEvent<HTMLFormElement>
}

describe('useResetPasswordPage', () => {
  beforeEach(() => {
    resetPasswordMock.mockReset()
    getPasswordResetLinkStatusMock.mockReset()
    getPasswordResetLinkStatusMock.mockResolvedValue({ result: 'valid' })
    navigateToMock.mockReset()
    useResetPasswordActionMock.mockReturnValue({
      error: null,
      getPasswordResetLinkStatus: getPasswordResetLinkStatusMock,
      isPending: false,
      resetPassword: resetPasswordMock,
    })
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToActivity: vi.fn(),
      navigateToGoalDetail: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
  })

  it('removes malformed token input without resolving or resetting it', async () => {
    const { result } = renderHook(() => useResetPasswordPage('invalid'))

    await act(async () => result.current.submit(submitEvent()))

    expect(resetPasswordMock).not.toHaveBeenCalled()
    expect(getPasswordResetLinkStatusMock).not.toHaveBeenCalled()
    expect(result.current.result).toBe('invalid')
  })

  it('validates matching minimum-length passwords before calling the action', async () => {
    const { result } = renderHook(() => useResetPasswordPage('a'.repeat(43)))
    await act(async () => {})
    act(() => {
      result.current.setPassword('short')
      result.current.setPasswordConfirmation('different')
    })

    await act(async () => result.current.submit(submitEvent()))

    expect(resetPasswordMock).not.toHaveBeenCalled()
    expect(result.current.passwordError).toBe('A senha deve ter pelo menos 8 caracteres.')
    expect(result.current.confirmationError).toBe('As senhas precisam ser iguais.')
  })

  it('resolves the link and automatically navigates to the validated sign-in destination', async () => {
    resetPasswordMock.mockResolvedValue({
      redirectTo: '/login',
      requiresEmailConfirmation: false,
      result: 'reset',
    })
    const { result } = renderHook(() => useResetPasswordPage('a'.repeat(43)))
    await act(async () => {})
    act(() => {
      result.current.setPassword('password-123')
      result.current.setPasswordConfirmation('password-123')
    })

    await act(async () => result.current.submit(submitEvent()))

    expect(resetPasswordMock).toHaveBeenCalledWith(
      'a'.repeat(43),
      'password-123',
      'password-123',
    )
    expect(result.current.result).toBe('reset')
    expect(getPasswordResetLinkStatusMock).toHaveBeenCalledWith('a'.repeat(43))
    expect(navigateToMock).toHaveBeenCalledWith('login')
  })
})
