import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { useDeleteAccountAction } from '../use-delete-account-action'

const { auth, queryClient, router } = vi.hoisted(() => ({
  auth: {
    prepareAccountDeletion: vi.fn(),
    deleteAccount: vi.fn(),
    getAccountDeletionStatus: vi.fn(),
  },
  queryClient: { clear: vi.fn() },
  router: { invalidate: vi.fn() },
}))

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => queryClient,
}))

vi.mock('@tanstack/react-router', () => ({
  useRouter: () => router,
}))

vi.mock('@/ui/shared/contexts/auth-context/use-auth-context', () => ({
  useAuthContext: () => auth,
}))

describe('useDeleteAccountAction', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    auth.prepareAccountDeletion.mockResolvedValue(undefined)
    auth.deleteAccount.mockResolvedValue(undefined)
    auth.getAccountDeletionStatus.mockResolvedValue({
      state: 'closed',
      closedAt: '2026-11-21T12:00:00Z',
      erasure: 'pending',
    })
  })

  it('prepares, closes and invalidates the signed-in browser after success', async () => {
    const { result } = renderHook(() => useDeleteAccountAction())
    const dispatch = vi.spyOn(window, 'dispatchEvent')

    await act(async () => result.current.submit('current-password'))

    expect(auth.prepareAccountDeletion).toHaveBeenCalledOnce()
    expect(auth.deleteAccount).toHaveBeenCalledWith('current-password')
    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'shifu:account-closure-committed' }),
    )
    expect(window.localStorage.getItem('shifu:account-closure-committed')).toBeTruthy()
    expect(queryClient.clear).toHaveBeenCalledOnce()
    expect(router.invalidate).toHaveBeenCalledWith({ sync: true })
    expect(result.current.isSubmitting).toBe(false)
    dispatch.mockRestore()
  })

  it('marks an invalid current password without checking closure status', async () => {
    auth.deleteAccount.mockRejectedValue(
      new AuthError('invalid-current-password', 'Senha incorreta.'),
    )
    const { result } = renderHook(() => useDeleteAccountAction())

    await act(async () => result.current.submit('wrong-password'))

    expect(result.current.errorMessage).toBe('Senha incorreta.')
    expect(result.current.isPasswordInvalid).toBe(true)
    expect(result.current.canCheckStatus).toBe(false)
    expect(auth.getAccountDeletionStatus).not.toHaveBeenCalled()
  })

  it('shows a safe message for an unexpected preparation failure', async () => {
    auth.prepareAccountDeletion.mockRejectedValue(new Error('unexpected failure'))
    const { result } = renderHook(() => useDeleteAccountAction())

    await act(async () => result.current.submit('current-password'))

    expect(result.current.errorMessage).toBe(
      'Não foi possível concluir agora. Tente novamente.',
    )
    expect(auth.deleteAccount).not.toHaveBeenCalled()
  })

  it('recovers an uncertain closure from the signed status', async () => {
    auth.deleteAccount.mockRejectedValue(
      new AuthError('result-uncertain', 'Resposta perdida.'),
    )
    const { result } = renderHook(() => useDeleteAccountAction())

    await act(async () => result.current.submit('current-password'))

    expect(auth.getAccountDeletionStatus).toHaveBeenCalledOnce()
    expect(result.current.errorMessage).toBeNull()
    expect(queryClient.clear).toHaveBeenCalledOnce()
    expect(router.invalidate).toHaveBeenCalledWith({ sync: true })
  })

  it('keeps manual status recovery available when automatic recovery fails', async () => {
    auth.deleteAccount.mockRejectedValue(
      new AuthError('result-uncertain', 'Resposta perdida.'),
    )
    auth.getAccountDeletionStatus.mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useDeleteAccountAction())

    await act(async () => result.current.submit('current-password'))

    expect(result.current.canCheckStatus).toBe(true)
    expect(result.current.errorMessage).toBe('Resposta perdida.')
    expect(queryClient.clear).not.toHaveBeenCalled()
  })

  it('reports an unverified manual status check as a connection error', async () => {
    auth.getAccountDeletionStatus.mockRejectedValue(new Error('offline'))
    const { result } = renderHook(() => useDeleteAccountAction())

    await act(async () => result.current.checkStatus())

    expect(result.current.errorMessage).toBe(
      'Não foi possível confirmar o estado. Uma falha de conexão não confirma o encerramento.',
    )
    expect(result.current.isCheckingStatus).toBe(false)
    expect(queryClient.clear).not.toHaveBeenCalled()
  })

  it('clears password and status feedback when the dialog opens', () => {
    auth.deleteAccount.mockRejectedValue(
      new AuthError('invalid-current-password', 'Senha incorreta.'),
    )
    const { result } = renderHook(() => useDeleteAccountAction())

    return act(async () => {
      await result.current.submit('wrong-password')
      result.current.clearFeedback()
      expect(result.current.errorMessage).toBeNull()
      expect(result.current.isPasswordInvalid).toBe(false)
      expect(result.current.canCheckStatus).toBe(false)
    })
  })
})
