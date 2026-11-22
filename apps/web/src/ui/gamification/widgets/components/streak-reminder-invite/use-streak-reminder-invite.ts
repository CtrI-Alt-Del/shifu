import { useLocation } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'

import { DEFAULT_STREAK_REMINDER_HOUR } from '@/ui/gamification/constants/streak-reminder-hour-options'
import { useBrowserPushNotificationEnrollment } from '@/ui/gamification/hooks/use-browser-push-notification-enrollment'
import { useChangeStreakReminderHourAction } from '@/ui/gamification/hooks/use-change-streak-reminder-hour-action'
import { useChangeStreakReminderPreferenceAction } from '@/ui/gamification/hooks/use-change-streak-reminder-preference-action'
import { useStreakReminderQuery } from '@/ui/gamification/hooks/use-streak-reminder-query'
import { showErrorToast, showInfoToast } from '@/ui/shared/notifications'

import { useAnswerStreakReminderInviteAction } from './use-answer-streak-reminder-invite-action'

export type StreakReminderInviteStep = 'invite' | 'hour'

const AUTOFOCUS_TARGET_ID_BY_STEP = {
  invite: 'streak-reminder-invite-enable',
  hour: 'streak-reminder-invite-hour',
} as const

export type UseStreakReminderInviteInput = { accountEmail: string }

const BLOCKED_MESSAGE = 'Sem problema. Você pode ativar os lembretes depois em Sua conta.'
const ANSWER_FAILURE_MESSAGE =
  'Não foi possível registrar sua resposta agora. Tente novamente.'
const ENROLLMENT_FAILURE_MESSAGE =
  'Não foi possível ativar os lembretes neste navegador. Tente de novo em Sua conta.'
const HOUR_FAILURE_MESSAGE = 'Não foi possível salvar o horário. Tente novamente.'

export function useStreakReminderInvite({ accountEmail }: UseStreakReminderInviteInput) {
  const { pathname } = useLocation()
  const { streakReminder, refetchStreakReminder } = useStreakReminderQuery()
  const { permission, enrollThisBrowser } =
    useBrowserPushNotificationEnrollment(accountEmail)
  const { answerStreakReminderInvite } = useAnswerStreakReminderInviteAction(accountEmail)
  const { changeStreakReminderPreference } =
    useChangeStreakReminderPreferenceAction(accountEmail)
  const { changeStreakReminderHour } = useChangeStreakReminderHourAction(accountEmail)

  const [isOpen, setIsOpen] = useState(false)
  const [step, setStep] = useState<StreakReminderInviteStep>('invite')
  const [hour, setHour] = useState(DEFAULT_STREAK_REMINDER_HOUR)
  const [isEnabling, setIsEnabling] = useState(false)
  const [isSavingHour, setIsSavingHour] = useState(false)
  const [selectPortalContainer, setSelectPortalContainer] = useState<HTMLElement | null>(
    null,
  )
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const previousPathnameRef = useRef(pathname)
  const hasOpenedRef = useRef(false)

  const inviteStatus = streakReminder?.inviteStatus ?? null
  const canOpen = inviteStatus === 'pending' && permission !== 'unsupported'
  const isBusy = isEnabling || isSavingHour

  useEffect(() => {
    if (previousPathnameRef.current === pathname) return
    previousPathnameRef.current = pathname
    void refetchStreakReminder()
  }, [pathname, refetchStreakReminder])

  useEffect(() => {
    if (!canOpen || hasOpenedRef.current) return
    hasOpenedRef.current = true
    const focusedElement = document.activeElement
    previousFocusRef.current =
      focusedElement instanceof HTMLElement && focusedElement !== document.body
        ? focusedElement
        : null
    setStep('invite')
    setHour(streakReminder?.hour ?? DEFAULT_STREAK_REMINDER_HOUR)
    setIsOpen(true)
  }, [canOpen, streakReminder?.hour])

  useEffect(() => {
    if (!isOpen || !selectPortalContainer) return
    // The invite opens on its primary action and the hour step on its field, so
    // the dialog container itself never holds the focus ring.
    selectPortalContainer
      .querySelector<HTMLElement>(`#${AUTOFOCUS_TARGET_ID_BY_STEP[step]}`)
      ?.focus()
  }, [isOpen, step, selectPortalContainer])

  async function answerInvite(): Promise<boolean> {
    try {
      await answerStreakReminderInvite()
      return true
    } catch {
      showErrorToast(ANSWER_FAILURE_MESSAGE)
      return false
    }
  }

  function handleHourChange(value: string | null) {
    if (value === null) return
    setHour(Number(value))
  }

  async function handleDecline() {
    if (isBusy) return
    setIsOpen(false)
    await answerInvite()
  }

  async function handleEnable() {
    if (isBusy) return
    setIsEnabling(true)
    try {
      if (!(await answerInvite())) return

      const outcome = await enrollThisBrowser()
      if (outcome === 'failed') {
        showErrorToast(ENROLLMENT_FAILURE_MESSAGE)
        setIsOpen(false)
        return
      }
      if (outcome !== 'enrolled') {
        showInfoToast(BLOCKED_MESSAGE)
        setIsOpen(false)
        return
      }

      try {
        await changeStreakReminderPreference(true)
      } catch {
        showErrorToast(ENROLLMENT_FAILURE_MESSAGE)
        setIsOpen(false)
        return
      }
      setStep('hour')
    } finally {
      setIsEnabling(false)
    }
  }

  async function handleSaveHour() {
    if (isBusy) return
    setIsSavingHour(true)
    try {
      await changeStreakReminderHour(hour)
      setIsOpen(false)
    } catch {
      showErrorToast(HOUR_FAILURE_MESSAGE)
    } finally {
      setIsSavingHour(false)
    }
  }

  function handleSkip() {
    if (isBusy) return
    setIsOpen(false)
  }

  function handleOpenChange(open: boolean) {
    if (open) return
    if (step === 'invite') void handleDecline()
    else handleSkip()
  }

  function handleOpenAutoFocus(event: Event) {
    event.preventDefault()
  }

  function handleCloseAutoFocus(event: Event) {
    const previousFocus = previousFocusRef.current
    if (!previousFocus?.isConnected) return
    event.preventDefault()
    previousFocus.focus()
  }

  return {
    isOpen,
    step,
    hour,
    isEnabling,
    isSavingHour,
    selectPortalContainer,
    setSelectPortalContainer,
    handleHourChange,
    handleDecline,
    handleEnable,
    handleSaveHour,
    handleSkip,
    handleOpenChange,
    handleOpenAutoFocus,
    handleCloseAutoFocus,
  }
}
