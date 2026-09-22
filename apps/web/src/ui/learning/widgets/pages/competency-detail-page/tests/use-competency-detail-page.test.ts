import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import type { CompetencyDetail } from '@/core/learning/competency-detail'
import { RestError } from '@/core/errors/rest-error'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { useRpcContext } from '@/ui/shared/hooks/use-rpc-context'

import { useCompetencyDetailPage } from '../use-competency-detail-page'

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
}))

vi.mock('@/ui/shared/hooks/use-navigation', () => ({
  useNavigation: vi.fn(),
}))

vi.mock('@/ui/shared/hooks/use-rpc-context', () => ({
  useRpcContext: vi.fn(),
}))

const useQueryMock = vi.mocked(useQuery)
const useNavigationMock = vi.mocked(useNavigation)
const useRpcContextMock = vi.mocked(useRpcContext)

const props = {
  competencyId: '01SHF000000000000000000004',
  goalId: '01SHF000000000000000000012',
  skillId: '01SHF000000000000000000002',
}

const detail: CompetencyDetail = {
  availability: 'unavailable',
  competencyId: props.competencyId,
  competencyName: 'Variáveis e valores',
  focusCompetencyId: null,
  focusCompetencyName: null,
  goalId: props.goalId,
  skillId: props.skillId,
  skillName: 'Lógica de programação',
}

const getCompetencyDetailMock = vi.fn()
const navigateToMock = vi.fn()
const navigateToGoalDetailMock = vi.fn()
const navigateToPlannerMock = vi.fn()
const refetchMock = vi.fn(() => Promise.resolve({} as never))

function mockQuery(
  overrides: {
    data?: CompetencyDetail | null
    error?: Error | null
    isPending?: boolean
  } = {},
) {
  useQueryMock.mockReturnValue({
    data: null,
    error: null,
    isPending: false,
    refetch: refetchMock,
    ...overrides,
  } as never)
}

describe('useCompetencyDetailPage', () => {
  beforeEach(() => {
    getCompetencyDetailMock.mockReset()
    navigateToMock.mockReset()
    navigateToGoalDetailMock.mockReset()
    navigateToPlannerMock.mockReset()
    refetchMock.mockReset()
    useQueryMock.mockReset()
    useNavigationMock.mockReturnValue({
      navigateTo: navigateToMock,
      navigateToGoalDetail: navigateToGoalDetailMock,
      navigateToPlanner: navigateToPlannerMock,
    })
    useRpcContextMock.mockReturnValue({
      learningService: {
        getCompetencyDetail: getCompetencyDetailMock,
      },
    } as never)
    mockQuery()
  })

  it('configures the scoped query and delegates requests to Learning', async () => {
    const { result } = renderHook(() => useCompetencyDetailPage(props))
    const options = useQueryMock.mock.calls[0]?.[0]

    expect(options?.queryKey).toEqual([
      'learning',
      'competency-detail',
      props.goalId,
      props.skillId,
      props.competencyId,
    ])
    expect(options?.refetchOnWindowFocus).toBe(false)
    const retry = options?.retry
    const retryDelay = options?.retryDelay
    expect(typeof retry).toBe('function')
    expect(typeof retryDelay).toBe('function')
    if (typeof retry !== 'function' || typeof retryDelay !== 'function') return

    expect(retry(0, new RestError('Rate limited.', 429))).toBe(true)
    expect(retry(2, new RestError('Rate limited.', 429))).toBe(false)
    expect(retry(0, new RestError('Unavailable.', 503))).toBe(false)
    expect(retryDelay(0, new RestError('Rate limited.', 429))).toBe(1000)

    getCompetencyDetailMock.mockResolvedValue(detail)
    await (options?.queryFn as () => Promise<CompetencyDetail>)()

    expect(getCompetencyDetailMock).toHaveBeenCalledWith(
      props.goalId,
      props.skillId,
      props.competencyId,
    )
    expect(result.current.isLoading).toBe(false)
  })

  it('returns loading, detail and retry state from the query', () => {
    mockQuery({ data: detail, isPending: true })

    const { result } = renderHook(() => useCompetencyDetailPage(props))

    expect(result.current.isLoading).toBe(true)
    expect(result.current.detail).toBe(detail)
    expect(result.current.handleRetry).toBe(refetchMock)
    expect(result.current.error).toBeNull()
  })

  it('classifies a private absence as non-recoverable', () => {
    const error = new RestError('Recurso não encontrado.', 404)
    mockQuery({ error })

    const { result } = renderHook(() => useCompetencyDetailPage(props))

    expect(result.current.error).toBe(error)
    expect(result.current.isPrivateAbsence).toBe(true)
    expect(result.current.isRecoverableError).toBe(false)
  })

  it('classifies other REST failures as recoverable', () => {
    const error = new RestError('Serviço temporariamente indisponível.', 503)
    mockQuery({ error })

    const { result } = renderHook(() => useCompetencyDetailPage(props))

    expect(result.current.error).toBe(error)
    expect(result.current.isPrivateAbsence).toBe(false)
    expect(result.current.isRecoverableError).toBe(true)
  })

  it('redirects rejected sessions to login without exposing a recoverable state', async () => {
    mockQuery({
      error: new AuthError('authentication-rejected', 'Sua sessão expirou.', {
        statusCode: 401,
      }),
    })

    const { result } = renderHook(() => useCompetencyDetailPage(props))

    await waitFor(() => expect(navigateToMock).toHaveBeenCalledWith('login'))
    expect(result.current.isPrivateAbsence).toBe(false)
    expect(result.current.isRecoverableError).toBe(false)
  })
})
