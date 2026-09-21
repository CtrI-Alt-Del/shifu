import { act, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { useSignInAction } from '@/ui/identity/hooks/use-sign-in-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

import { useSignInPage } from '../use-sign-in-page'

vi.mock('@/ui/identity/hooks/use-sign-in-action', () => ({
  useSignInAction: vi.fn(),
}))

vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: vi.fn(),
}))

const signInMock = vi.fn()
const navigateToMock = vi.fn()
const useSignInActionMock = vi.mocked(useSignInAction)
const useNavigationMock = vi.mocked(useNavigation)

function submitEvent() {
  return {
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
  } as unknown as FormEvent<HTMLFormElement>
}

describe('useSignInPage', () => {
  beforeEach(() => {
    signInMock.mockReset()
    navigateToMock.mockReset()
    useSignInActionMock.mockReturnValue({
      error: null,
      isPending: false,
      signIn: signInMock,
    })
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToPath: vi.fn(),
    })
  })

  it('starts with an empty sign-in form', () => {
    const { result } = renderHook(() => useSignInPage())

    expect(result.current.email).toBe('')
    expect(result.current.password).toBe('')
  })

  it('clears only the password for rejected credentials and focuses the alert', async () => {
    signInMock.mockRejectedValue(
      new AuthError('authentication-rejected', 'E-mail ou senha inválidos.', {
        statusCode: 401,
      }),
    )
    const { result } = renderHook(() => useSignInPage())

    act(() => {
      result.current.setEmail('learner@example.com')
      result.current.setPassword('wrong-password')
    })
    await act(async () => result.current.submit(submitEvent()))

    expect(result.current.status).toBe('invalid')
    expect(result.current.email).toBe('learner@example.com')
    expect(result.current.password).toBe('')
    expect(result.current.message).toBe('E-mail ou senha inválidos.')
  })

  it('preserves both fields for infrastructure and throttling failures', async () => {
    signInMock.mockRejectedValueOnce(
      new AuthError('unavailable', 'Não foi possível entrar agora. Tente novamente.', {
        statusCode: 503,
      }),
    )
    const { result } = renderHook(() => useSignInPage())

    act(() => {
      result.current.setEmail('learner@example.com')
      result.current.setPassword('correct-password')
    })
    await act(async () => result.current.submit(submitEvent()))

    expect(result.current.status).toBe('unavailable')
    expect(result.current.password).toBe('correct-password')

    signInMock.mockRejectedValueOnce(
      new AuthError(
        'unavailable',
        'Muitas tentativas. Aguarde um momento e tente novamente.',
        {
          statusCode: 429,
        },
      ),
    )
    await act(async () => result.current.submit(submitEvent()))

    expect(result.current.status).toBe('throttled')
    expect(result.current.email).toBe('learner@example.com')
    expect(result.current.password).toBe('correct-password')
  })

  it('navigates to the destination returned by the authentication boundary', async () => {
    signInMock.mockResolvedValue({ access: 'protected', redirectTo: 'root' })
    const { result } = renderHook(() => useSignInPage())

    await act(async () => result.current.submit(submitEvent()))

    expect(navigateToMock).toHaveBeenCalledWith('root')
  })
})
