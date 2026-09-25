import { act, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useRegisterAccountAction } from '@/ui/identity/hooks/use-register-account-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useRegisterPage } from '../use-register-page'

vi.mock('@/ui/identity/hooks/use-register-account-action', () => ({
  useRegisterAccountAction: vi.fn(),
}))
vi.mock('@/ui/shared/hooks/use-navigation', () => ({ useNavigation: vi.fn() }))

const registerAccountMock = vi.fn()
const navigateToMock = vi.fn()
const useRegisterAccountActionMock = vi.mocked(useRegisterAccountAction)
const useNavigationMock = vi.mocked(useNavigation)

function submitEvent() {
  return {
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
  } as unknown as FormEvent<HTMLFormElement>
}

describe('useRegisterPage', () => {
  beforeEach(() => {
    registerAccountMock.mockReset()
    navigateToMock.mockReset()
    useRegisterAccountActionMock.mockReturnValue({
      error: null,
      isPending: false,
      registerAccount: registerAccountMock,
    })
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToGoalDetail: vi.fn(),
      navigateToPlanner: vi.fn(),
    })
  })

  it('keeps valid fields and reports client validation without submitting', async () => {
    const { result } = renderHook(() => useRegisterPage())
    act(() => {
      result.current.form.setFieldValue('displayName', 'Ana')
      result.current.form.setFieldValue('email', 'invalid-email')
      result.current.form.setFieldValue('password', 'password-123')
    })

    await act(async () => result.current.submit(submitEvent()))

    expect(registerAccountMock).not.toHaveBeenCalled()
    expect(result.current.message).toBe('Revise os campos destacados')
    expect(result.current.form.state.values).toEqual({
      displayName: 'Ana',
      email: 'invalid-email',
      password: 'password-123',
    })
  })

  it('navigates to pending confirmation after registration', async () => {
    registerAccountMock.mockResolvedValue({ redirectTo: '/pending-confirmation' })
    const { result } = renderHook(() => useRegisterPage())
    act(() => {
      result.current.form.setFieldValue('displayName', 'Ana')
      result.current.form.setFieldValue('email', 'ana@example.com')
      result.current.form.setFieldValue('password', 'password-123')
    })

    await act(async () => result.current.submit(submitEvent()))

    expect(registerAccountMock).toHaveBeenCalledWith({
      displayName: 'Ana',
      email: 'ana@example.com',
      password: 'password-123',
    })
    expect(navigateToMock).toHaveBeenCalledWith('pendingConfirmation')
    expect(result.current.isSubmitting).toBe(false)
  })

  it('preserves entered fields and exposes a recoverable failure', async () => {
    registerAccountMock.mockRejectedValue(new Error('unavailable'))
    const { result } = renderHook(() => useRegisterPage())
    act(() => {
      result.current.form.setFieldValue('displayName', 'Ana')
      result.current.form.setFieldValue('email', 'ana@example.com')
      result.current.form.setFieldValue('password', 'password-123')
    })

    await act(async () => result.current.submit(submitEvent()))

    expect(result.current.message).toBe(
      'Não foi possível criar sua conta agora. Tente novamente.',
    )
    expect(result.current.form.state.values).toEqual({
      displayName: 'Ana',
      email: 'ana@example.com',
      password: 'password-123',
    })
    expect(result.current.isSubmitting).toBe(false)
  })
})
