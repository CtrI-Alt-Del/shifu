import { cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  useBlocker: vi.fn(),
  access: vi.fn(),
  abandonDiagnostic: vi.fn(),
  clearDiagnosticRun: vi.fn(),
}))

vi.mock('@tanstack/react-router', () => ({ useBlocker: mocks.useBlocker }))
vi.mock('@tanstack/react-start', () => ({
  createServerFn: () => {
    let validate = (data: unknown) => data
    const builder = {
      middleware: () => builder,
      validator: (next: (data: unknown) => unknown) => {
        validate = next
        return builder
      },
      handler:
        (handler: (input: unknown) => unknown) =>
        async (input: { data?: unknown } = {}) =>
          handler({
            data: validate(input.data),
            context: { requestId: '11111111-1111-4111-8111-111111111111' },
          }),
    }
    return builder
  },
}))
vi.mock('@/start', () => ({ serverFunctionTelemetryMiddleware: {} }))
vi.mock('@tanstack/react-start/server', () => ({
  getRequest: () => new Request('http://shifu.test'),
}))
vi.mock('@/provision/auth/better-auth/better-auth-config', () => ({
  BetterAuthConfig: () => ({ identityURL: 'http://api.test' }),
}))
vi.mock('@/provision/auth/better-auth/better-auth-provider', () => ({
  getBetterAuthProvider: () => ({ getCurrentAccess: mocks.access }),
}))
vi.mock('@/rest/axios/server-request-client', () => ({
  createServerRequestClient: vi.fn(() => ({})),
}))
vi.mock('@/rest/services/learning-service', () => ({
  LearningService: () => ({ abandonDiagnostic: mocks.abandonDiagnostic }),
}))
vi.mock('@/ui/learning/diagnostic-run-session', () => ({
  clearDiagnosticRun: mocks.clearDiagnosticRun,
}))

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import {
  abandonDiagnosticAction,
  useDiagnosticLeaveGuard,
} from '@/ui/learning/hooks/use-diagnostic-leave-guard'

const ids = {
  goalId: '01J00000000000000000000001',
  skillId: '01J00000000000000000000002',
  diagnosticRunId: '11111111-1111-4111-8111-111111111111',
}

function renderGuard(status: 'unblocked' | 'blocked') {
  const reset = vi.fn()
  const proceed = vi.fn()
  mocks.useBlocker.mockReturnValue({ status, reset, proceed })
  const hook = renderHook(() => useDiagnosticLeaveGuard({ ...ids, isActive: true }))
  return { ...hook, reset, proceed }
}

describe('useDiagnosticLeaveGuard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.access.mockResolvedValue({ accessToken: 'token' })
    mocks.abandonDiagnostic.mockResolvedValue({ kind: 'success' })
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(window, 'alert').mockImplementation(() => undefined)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('blocks only navigation outside the active skill path', () => {
    renderGuard('unblocked')
    const options = mocks.useBlocker.mock.calls[0]?.[0] as {
      shouldBlockFn: (input: { next: { pathname: string } }) => boolean
    }

    expect(
      options.shouldBlockFn({
        next: { pathname: `/learning/goals/${ids.goalId}/skills/${ids.skillId}` },
      }),
    ).toBe(false)
    expect(options.shouldBlockFn({ next: { pathname: '/learning/goals/other' } })).toBe(
      true,
    )
  })

  it('resets a blocked transition when the learner declines', () => {
    vi.mocked(window.confirm).mockReturnValue(false)
    const { reset } = renderGuard('blocked')

    expect(reset).toHaveBeenCalledOnce()
    expect(mocks.abandonDiagnostic).not.toHaveBeenCalled()
  })

  it('resets and alerts when the diagnostic cannot be abandoned', async () => {
    mocks.access.mockResolvedValue(null)
    const { reset } = renderGuard('blocked')

    await waitFor(() => expect(reset).toHaveBeenCalledOnce())
    expect(window.alert).toHaveBeenCalledWith(
      'Não foi possível descartar o diagnóstico. Tente novamente.',
    )
  })

  it('clears the run and proceeds for a fresh diagnostic', async () => {
    const { proceed } = renderGuard('blocked')

    await waitFor(() => expect(proceed).toHaveBeenCalledOnce())
    expect(mocks.clearDiagnosticRun).toHaveBeenCalledWith(ids.goalId, ids.skillId)
  })

  it('maps abandon failures to stable diagnostic outcomes', async () => {
    await expect(abandonDiagnosticAction({ data: ids })).resolves.toEqual({
      kind: 'success',
    })
    mocks.abandonDiagnostic.mockRejectedValueOnce(
      new AuthError('authentication-rejected', 'expired', { statusCode: 401 }),
    )
    await expect(abandonDiagnosticAction({ data: ids })).resolves.toEqual({
      kind: 'unavailable',
    })
    mocks.abandonDiagnostic.mockRejectedValueOnce(new RestError('stale', 409))
    await expect(abandonDiagnosticAction({ data: ids })).resolves.toEqual({
      kind: 'stale',
    })
    mocks.abandonDiagnostic.mockRejectedValueOnce(new Error('down'))
    await expect(abandonDiagnosticAction({ data: ids })).resolves.toEqual({
      kind: 'unavailable',
    })
  })

  it('warns about a rejected diagnostic transition and resets', async () => {
    mocks.abandonDiagnostic.mockRejectedValue(new Error('unexpected'))
    const { proceed, reset } = renderGuard('blocked')

    await waitFor(() => expect(reset).toHaveBeenCalledOnce())
    expect(proceed).not.toHaveBeenCalled()
    expect(window.alert).toHaveBeenCalled()
  })
})
