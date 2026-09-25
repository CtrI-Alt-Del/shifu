import { useCallback, useEffect, useRef, useState } from 'react'

import { useResendConfirmationAction } from '@/ui/identity/hooks/use-resend-confirmation-action'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type PendingConfirmationPageState = 'ready' | 'cooldown' | 'delivery_issue'

export function usePendingConfirmationPage() {
  const { exitPendingConfirmation, getPendingConfirmationStatus } = useAuthContext()
  const { navigateTo } = useNavigation()
  const { resendConfirmation } = useResendConfirmationAction()
  const [state, setState] = useState<PendingConfirmationPageState>('cooldown')
  const [remainingSeconds, setRemainingSeconds] = useState(60)
  const [message, setMessage] = useState<string | null>(null)
  const [exitErrorMessage, setExitErrorMessage] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isResending, setIsResending] = useState(false)
  const [isExiting, setIsExiting] = useState(false)
  const alertRef = useRef<HTMLDivElement>(null)

  const refresh = useCallback(async () => {
    try {
      const status = await getPendingConfirmationStatus()
      setState(status.state)
      setRemainingSeconds(status.retryAfterSeconds ?? 0)
      setMessage(
        status.state === 'delivery_issue'
          ? 'Não foi possível entregar o link. Você pode tentar reenviar.'
          : null,
      )
    } catch {
      setState('delivery_issue')
      setMessage('Não foi possível atualizar a confirmação. Tente reenviar o link.')
    } finally {
      setIsLoading(false)
    }
  }, [getPendingConfirmationStatus])

  useEffect(() => {
    void refresh()
    const interval = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refresh()
    }, 10_000)
    function handleFocus() {
      void refresh()
    }
    window.addEventListener('focus', handleFocus)
    window.addEventListener('online', handleFocus)
    return () => {
      window.clearInterval(interval)
      window.removeEventListener('focus', handleFocus)
      window.removeEventListener('online', handleFocus)
    }
  }, [refresh])

  useEffect(() => {
    if (remainingSeconds <= 0) return
    const timeout = window.setTimeout(
      () => setRemainingSeconds((seconds) => seconds - 1),
      1_000,
    )
    return () => window.clearTimeout(timeout)
  }, [remainingSeconds])

  useEffect(() => {
    if (message || exitErrorMessage) alertRef.current?.focus()
  }, [exitErrorMessage, message])

  async function handleResend() {
    if (isResending || remainingSeconds > 0) return
    setIsResending(true)
    setMessage(null)
    try {
      const result = await resendConfirmation()
      setState(result.result === 'cooldown' ? 'cooldown' : 'ready')
      setRemainingSeconds(result.retryAfterSeconds ?? 60)
      setMessage('Se o envio for elegível, um novo link será preparado.')
      await refresh()
    } catch {
      setState('delivery_issue')
      setMessage('Não foi possível reenviar agora. Tente novamente.')
    } finally {
      setIsResending(false)
    }
  }

  async function handleExit() {
    if (isExiting) return
    setIsExiting(true)
    setExitErrorMessage(null)
    try {
      await exitPendingConfirmation()
      await navigateTo('login')
    } catch {
      setExitErrorMessage('Não foi possível sair agora. Tente novamente.')
    } finally {
      setIsExiting(false)
    }
  }

  return {
    alertRef,
    exitErrorMessage,
    handleExit,
    handleResend,
    isExiting,
    isLoading,
    isResending,
    message,
    remainingSeconds,
    state,
  }
}
