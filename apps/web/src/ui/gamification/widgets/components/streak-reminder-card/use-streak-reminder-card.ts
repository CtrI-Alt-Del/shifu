import { useRouteContext } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'

import { DEFAULT_STREAK_REMINDER_HOUR } from '@/ui/gamification/constants/streak-reminder-hour-options'
import { useBrowserPushNotificationEnrollment } from '@/ui/gamification/hooks/use-browser-push-notification-enrollment'
import { useChangeStreakReminderHourAction } from '@/ui/gamification/hooks/use-change-streak-reminder-hour-action'
import { useChangeStreakReminderPreferenceAction } from '@/ui/gamification/hooks/use-change-streak-reminder-preference-action'
import { useStreakReminderQuery } from '@/ui/gamification/hooks/use-streak-reminder-query'
import { showErrorToast } from '@/ui/shared/notifications'

import { useStreakReminderPreferenceQuery } from './use-streak-reminder-preference-query'

export type StreakReminderCardNotice = 'blocked' | 'unsupported' | null

const SWITCH_FAILURE_MESSAGE =
  'Não foi possível atualizar os lembretes agora. Tente novamente.'
const ENROLLMENT_FAILURE_MESSAGE =
  'Não foi possível ativar os lembretes neste navegador. Tente novamente.'
const HOUR_FAILURE_MESSAGE = 'Não foi possível salvar o horário. Tente novamente.'

export function useStreakReminderCard() {
  const { email: accountEmail } = useRouteContext({ from: '/account/profile/' })
  const {
    streakReminder,
    streakReminderError,
    isLoadingStreakReminder,
    refetchStreakReminder,
  } = useStreakReminderQuery()
  const { preference, preferenceError, isLoadingPreference, refetchPreference } =
    useStreakReminderPreferenceQuery()
  const { permission, enrollThisBrowser, refreshThisBrowser } =
    useBrowserPushNotificationEnrollment(accountEmail)
  const { changeStreakReminderPreference } =
    useChangeStreakReminderPreferenceAction(accountEmail)
  const { changeStreakReminderHour } = useChangeStreakReminderHourAction(accountEmail)

  const [isSwitching, setIsSwitching] = useState(false)
  const [pendingHour, setPendingHour] = useState<number | null>(null)
  const hasCheckedRefreshRef = useRef(false)

  const isLoading = isLoadingStreakReminder || isLoadingPreference
  const hasError = Boolean(streakReminderError || preferenceError)
  const isEnabled = preference?.enabled ?? false
  const isHourPending = pendingHour !== null
  const hour = pendingHour ?? streakReminder?.hour ?? DEFAULT_STREAK_REMINDER_HOUR
  const notice: StreakReminderCardNotice =
    permission === 'denied'
      ? 'blocked'
      : permission === 'unsupported'
        ? 'unsupported'
        : null

  useEffect(() => {
    if (isLoading || hasCheckedRefreshRef.current) return
    hasCheckedRefreshRef.current = true
    // Only the state found on mount counts: turning the switch on enrolls the
    // browser by itself.
    if (isEnabled && permission === 'granted') void refreshThisBrowser()
  }, [isLoading, isEnabled, permission, refreshThisBrowser])

  async function handleSwitchChange(enabled: boolean) {
    if (isSwitching) return
    setIsSwitching(true)
    try {
      if (enabled && permission !== 'denied' && permission !== 'unsupported') {
        const outcome = await enrollThisBrowser()
        if (outcome === 'failed') {
          showErrorToast(ENROLLMENT_FAILURE_MESSAGE)
          return
        }
      }
      await changeStreakReminderPreference(enabled)
    } catch {
      showErrorToast(SWITCH_FAILURE_MESSAGE)
    } finally {
      setIsSwitching(false)
    }
  }

  async function handleHourChange(value: string | null) {
    if (value === null || isHourPending) return
    const nextHour = Number(value)
    if (nextHour === hour) return
    setPendingHour(nextHour)
    try {
      await changeStreakReminderHour(nextHour)
    } catch {
      showErrorToast(HOUR_FAILURE_MESSAGE)
    } finally {
      setPendingHour(null)
    }
  }

  function handleRetry() {
    void refetchStreakReminder()
    void refetchPreference()
  }

  return {
    hour,
    isLoading,
    hasError,
    isEnabled,
    isSwitching,
    isHourPending,
    notice,
    handleSwitchChange,
    handleHourChange,
    handleRetry,
  }
}
