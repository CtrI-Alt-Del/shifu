import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthError } from '@/core/errors/auth-error'
import { useAccountPage } from '../use-account-page'
import { useAccountProfileQuery } from '../use-account-profile-query'
vi.mock('../use-account-profile-query', () => ({ useAccountProfileQuery: vi.fn() }))
const useAccountProfileQueryMock = vi.mocked(useAccountProfileQuery)
describe('useAccountPage', () => {
  beforeEach(() => vi.clearAllMocks())
  it('exposes canonical query state and switches only supported tabs', async () => {
    const refetchAccountProfileMock = vi.fn().mockResolvedValue(undefined)
    const profile = {
      accountId: 'a',
      displayName: 'Maria',
      email: 'm@example.com',
      timeZone: null,
    }
    useAccountProfileQueryMock.mockReturnValue({
      accountProfile: profile,
      isLoadingAccountProfile: false,
      accountProfileError: null,
      refetchAccountProfile: refetchAccountProfileMock,
    })
    const { result } = renderHook(() => useAccountPage({ accountEmail: profile.email }))
    expect(useAccountProfileQueryMock).toHaveBeenCalledWith(profile.email)
    expect(result.current.activeTab).toBe('profile')
    expect(result.current.accountProfile).toBe(profile)
    act(() => result.current.handleTabChange('security'))
    expect(result.current.activeTab).toBe('security')
    act(() => result.current.handleTabChange('delete'))
    expect(result.current.activeTab).toBe('security')
    act(() => result.current.handleTabChange('profile'))
    expect(result.current.activeTab).toBe('profile')
    await result.current.refetchAccountProfile()
    expect(refetchAccountProfileMock).toHaveBeenCalledOnce()
  })
  it('exposes loading and recoverable failures without inventing empty profiles', () => {
    const failure = new AuthError('unavailable', 'Indisponível.')
    useAccountProfileQueryMock.mockReturnValue({
      accountProfile: null,
      isLoadingAccountProfile: true,
      accountProfileError: failure,
      refetchAccountProfile: vi.fn(),
    })
    const { result } = renderHook(() => useAccountPage({ accountEmail: 'm@example.com' }))
    expect(result.current.accountProfile).toBeNull()
    expect(result.current.isLoadingAccountProfile).toBe(true)
    expect(result.current.accountProfileError).toBe(failure)
  })
})
