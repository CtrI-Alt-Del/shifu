import { act, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { usePasswordRecoveryStatusQuery } from '@/ui/identity/hooks/use-password-recovery-status-query'
import { useRequestPasswordRecoveryAction } from '@/ui/identity/hooks/use-request-password-recovery-action'

import { useForgotPasswordPage } from '../use-forgot-password-page'

vi.mock('@/ui/identity/hooks/use-password-recovery-status-query', () => ({
  usePasswordRecoveryStatusQuery: vi.fn(),
}))
vi.mock('@/ui/identity/hooks/use-request-password-recovery-action', () => ({
  useRequestPasswordRecoveryAction: vi.fn(),
}))

const requestPasswordRecoveryMock = vi.fn()
const retryPasswordRecoveryMock = vi.fn()
const refetchMock = vi.fn()
const usePasswordRecoveryStatusQueryMock = vi.mocked(usePasswordRecoveryStatusQuery)
const useRequestPasswordRecoveryActionMock = vi.mocked(useRequestPasswordRecoveryAction)

function submitEvent() {
  return {
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
  } as unknown as FormEvent<HTMLFormElement>
}

describe('useForgotPasswordPage', () => {
  beforeEach(() => {
    requestPasswordRecoveryMock.mockReset()
    retryPasswordRecoveryMock.mockReset()
    refetchMock.mockReset()
    useRequestPasswordRecoveryActionMock.mockReturnValue({
      error: null,
      isPending: false,
      requestPasswordRecovery: requestPasswordRecoveryMock,
      retryPasswordRecovery: retryPasswordRecoveryMock,
    })
    usePasswordRecoveryStatusQueryMock.mockReturnValue({
      error: null,
      isLoading: false,
      refetch: refetchMock,
      status: null,
    })
  })

  it('preserves the address and blocks malformed submissions', async () => {
    const { result } = renderHook(() => useForgotPasswordPage())
    act(() => result.current.setEmail('invalid-email'))

    await act(async () => result.current.submit(submitEvent()))

    expect(requestPasswordRecoveryMock).not.toHaveBeenCalled()
    expect(result.current.email).toBe('invalid-email')
    expect(result.current.emailError).toBe('Informe um e-mail válido.')
  })

  it('moves to the generic status state after an accepted request', async () => {
    requestPasswordRecoveryMock.mockResolvedValue({ accepted: true })
    const { result } = renderHook(() => useForgotPasswordPage())
    act(() => result.current.setEmail('ana@example.com'))

    await act(async () => result.current.submit(submitEvent()))

    expect(requestPasswordRecoveryMock).toHaveBeenCalledWith('ana@example.com')
    expect(result.current.mode).toBe('status')
  })

  it('retries delivery and refreshes the generic status', async () => {
    retryPasswordRecoveryMock.mockResolvedValue({
      retryAfterSeconds: null,
      state: 'ready',
    })
    usePasswordRecoveryStatusQueryMock.mockReturnValue({
      error: null,
      isLoading: false,
      refetch: refetchMock,
      status: { retryAfterSeconds: null, state: 'delivery_issue' },
    })
    const { result } = renderHook(() => useForgotPasswordPage())
    act(() => result.current.setEmail('ana@example.com'))
    await act(async () => result.current.submit(submitEvent()))
    await act(async () => result.current.handleRetry())

    expect(retryPasswordRecoveryMock).toHaveBeenCalledOnce()
    expect(refetchMock).toHaveBeenCalledOnce()
  })
})
