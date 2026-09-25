import { useEffect, useRef, useState } from 'react'

import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type PendingConfirmationStatus = 'idle' | 'pending' | 'success' | 'error'

export function usePendingConfirmationPage() {
  const { exitPendingConfirmation } = useAuthContext()
  const { navigateTo } = useNavigation()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [status, setStatus] = useState<PendingConfirmationStatus>('idle')
  const alertRef = useRef<HTMLDivElement>(null)
  const isExitInFlightRef = useRef(false)

  useEffect(() => {
    if (status === 'error') alertRef.current?.focus()
  }, [status])

  async function handleExit() {
    if (isExitInFlightRef.current) return

    isExitInFlightRef.current = true
    setErrorMessage(null)
    setStatus('pending')

    try {
      await exitPendingConfirmation()
      setStatus('success')
      await navigateTo('login')
    } catch {
      isExitInFlightRef.current = false
      setErrorMessage('Não foi possível sair agora. Tente novamente.')
      setStatus('error')
    }
  }

  return {
    alertRef,
    errorMessage,
    handleExit,
    isExiting: status === 'pending',
    status,
  }
}
