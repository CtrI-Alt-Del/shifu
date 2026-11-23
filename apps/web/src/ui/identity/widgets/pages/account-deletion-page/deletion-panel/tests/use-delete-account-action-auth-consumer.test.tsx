import { act, cleanup, renderHook } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthError } from '@/core/errors/auth-error'
import { AuthContextProvider } from '@/ui/shared/contexts/auth-context'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'
import { useDeleteAccountAction } from '../use-delete-account-action'

const { queryClient, router } = vi.hoisted(() => ({
  queryClient: { clear: vi.fn() },
  router: { invalidate: vi.fn() },
}))

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => queryClient,
}))

vi.mock('@tanstack/react-router', () => ({
  useRouter: () => router,
}))

function wrapper({ children }: PropsWithChildren) {
  return <AuthContextProvider>{children}</AuthContextProvider>
}

describe('account deletion action through the browser auth context', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
  })

  it('uses the account deletion endpoints and verifies a signed status', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ state: 'prepared' }), { status: 201 }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            state: 'closed',
            closedAt: '2026-11-21T12:00:00Z',
            erasure: 'pending',
          }),
          { status: 202 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            state: 'closed',
            closedAt: '2026-11-21T12:00:00Z',
            erasure: 'completed',
          }),
          { status: 200 },
        ),
      )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useDeleteAccountAction(), { wrapper })

    await act(async () => result.current.submit('current-password'))
    await act(async () => result.current.checkStatus())

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/auth/account/deletion/prepare',
      expect.objectContaining({ method: 'POST', credentials: 'same-origin' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/auth/account/deletion',
      expect.objectContaining({ method: 'POST', credentials: 'same-origin' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      '/api/auth/account/deletion',
      expect.objectContaining({ method: 'GET', cache: 'no-store' }),
    )
    expect(result.current.errorMessage).toBeNull()
    expect(queryClient.clear).toHaveBeenCalledTimes(2)
    expect(router.invalidate).toHaveBeenCalledTimes(2)
  })

  it('maps a rejected current password from the account API', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ state: 'prepared' }), { status: 201 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ code: 'invalid_current_password' }), {
          status: 403,
        }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useDeleteAccountAction(), { wrapper })

    await act(async () => result.current.submit('wrong-password'))

    expect(result.current.errorMessage).toBe('A senha atual está incorreta.')
    expect(result.current.isPasswordInvalid).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('issues and validates browser capabilities through the auth context', async () => {
    const capability = `capability_${'a'.repeat(48)}`
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ capability }), { status: 201 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ state: 'revoked' }), { status: 200 }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    let issued = ''
    let validated: 'active' | 'revoked' = 'active'

    await act(async () => {
      issued = await result.current.issueBrowserDataCapability()
      validated = await result.current.validateBrowserDataCapability(issued)
    })

    expect(issued).toBe(capability)
    expect(validated).toBe('revoked')
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/identity/browser-data-capabilities',
      expect.objectContaining({ method: 'POST', cache: 'no-store' }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/identity/browser-data-validations',
      expect.objectContaining({ method: 'POST', cache: 'no-store' }),
    )
  })

  it('keeps POST uncertainty and distinguishes status network and body failures', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ code: 'identity_unavailable' }), {
          status: 503,
        }),
      )
      .mockRejectedValueOnce(new Error('status network failure'))
      .mockResolvedValueOnce(new Response('not-json', { status: 503 }))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    let deleteError: unknown
    const statusErrors: unknown[] = []

    await act(async () => {
      try {
        await result.current.deleteAccount('current-password')
      } catch (error) {
        deleteError = error
      }
      for (let index = 0; index < 2; index += 1) {
        try {
          await result.current.getAccountDeletionStatus()
        } catch (error) {
          statusErrors.push(error)
        }
      }
    })

    expect(deleteError).toBeInstanceOf(AuthError)
    expect(deleteError).toMatchObject({ kind: 'result-uncertain' })
    expect(statusErrors).toEqual([
      expect.objectContaining({ kind: 'unavailable' }),
      expect.objectContaining({ kind: 'invalid-response' }),
    ])
  })

  it('rejects an expired authentication session after a deletion request', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ code: 'unauthorized' }), { status: 401 }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    let deletionError: unknown

    await act(async () => {
      try {
        await result.current.deleteAccount('current-password')
      } catch (error) {
        deletionError = error
      }
    })

    expect(deletionError).toBeInstanceOf(AuthError)
    expect(deletionError).toMatchObject({ kind: 'authentication-rejected' })
  })

  it('maps expired preparation and malformed status responses safely', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ code: 'preparation_expired' }), {
          status: 403,
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            state: 'closed',
            closedAt: 'invalid-date',
            erasure: 'pending',
          }),
          { status: 200 },
        ),
      )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    let deletionError: unknown
    let statusError: unknown

    await act(async () => {
      try {
        await result.current.deleteAccount('current-password')
      } catch (error) {
        deletionError = error
      }
      try {
        await result.current.getAccountDeletionStatus()
      } catch (error) {
        statusError = error
      }
    })

    expect(deletionError).toBeInstanceOf(AuthError)
    expect(deletionError).toMatchObject({ kind: 'validation-failed' })
    expect(statusError).toBeInstanceOf(AuthError)
    expect(statusError).toMatchObject({ kind: 'invalid-response' })
  })

  it('preserves uncertainty when a deletion response is missing or malformed', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new Error('network failure'))
      .mockResolvedValueOnce(new Response('not-json', { status: 503 }))
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    const errors: unknown[] = []

    await act(async () => {
      for (let index = 0; index < 2; index += 1) {
        try {
          await result.current.deleteAccount('current-password')
        } catch (error) {
          errors.push(error)
        }
      }
    })

    expect(errors).toHaveLength(2)
    expect(errors).toEqual([
      expect.objectContaining({ kind: 'result-uncertain' }),
      expect.objectContaining({ kind: 'result-uncertain' }),
    ])
  })

  it('rejects malformed capability responses through the auth context', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ capability: 'short' }), { status: 201 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ state: 'unknown' }), { status: 200 }),
      )
    vi.stubGlobal('fetch', fetchMock)
    const { result } = renderHook(() => useAuthContext(), { wrapper })
    let issueError: unknown
    let validationError: unknown

    await act(async () => {
      try {
        await result.current.issueBrowserDataCapability()
      } catch (error) {
        issueError = error
      }
      try {
        await result.current.validateBrowserDataCapability(`capability_${'a'.repeat(48)}`)
      } catch (error) {
        validationError = error
      }
    })

    expect(issueError).toBeInstanceOf(AuthError)
    expect(validationError).toBeInstanceOf(AuthError)
    expect(issueError).toMatchObject({ kind: 'invalid-response' })
    expect(validationError).toMatchObject({ kind: 'invalid-response' })
  })
})
