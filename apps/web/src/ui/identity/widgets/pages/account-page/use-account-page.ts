import { useState } from 'react'
import type { AccountPageProps } from './index'
import { useAccountProfileQuery } from './use-account-profile-query'

export function useAccountPage({ accountEmail }: AccountPageProps) {
  const [activeTab, setActiveTab] = useState<'profile' | 'security'>('profile')
  const {
    accountProfile,
    isLoadingAccountProfile,
    accountProfileError,
    refetchAccountProfile,
  } = useAccountProfileQuery(accountEmail)
  function handleTabChange(value: string) {
    if (value === 'profile' || value === 'security') setActiveTab(value)
  }
  return {
    activeTab,
    accountProfile,
    isLoadingAccountProfile,
    accountProfileError,
    handleTabChange,
    refetchAccountProfile,
  }
}
