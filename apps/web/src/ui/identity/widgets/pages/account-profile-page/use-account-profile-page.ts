import type { AccountProfilePageProps } from './index'
import { useAccountProfileQuery } from './use-account-profile-query'

export function useAccountProfilePage({ accountEmail }: AccountProfilePageProps) {
  const {
    accountProfile,
    isLoadingAccountProfile,
    accountProfileError,
    refetchAccountProfile,
  } = useAccountProfileQuery(accountEmail)
  return {
    accountProfile,
    isLoadingAccountProfile,
    accountProfileError,
    refetchAccountProfile,
  }
}
