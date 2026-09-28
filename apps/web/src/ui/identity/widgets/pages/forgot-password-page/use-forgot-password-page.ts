import { useEffect, useRef, useState, type FormEvent } from 'react'

import { usePasswordRecoveryStatusQuery } from '@/ui/identity/hooks/use-password-recovery-status-query'
import { useRequestPasswordRecoveryAction } from '@/ui/identity/hooks/use-request-password-recovery-action'

export type ForgotPasswordPageMode = 'form' | 'status'
export type ForgotPasswordPageStatus = 'loading' | 'ready' | 'cooldown' | 'delivery_issue'

export function useForgotPasswordPage() {
  const {
    isPending: isRequestPending,
    requestPasswordRecovery,
    retryPasswordRecovery,
  } = useRequestPasswordRecoveryAction()
  const [mode, setMode] = useState<ForgotPasswordPageMode>('form')
  const [email, setEmail] = useState('')
  const [emailError, setEmailError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [isRetrying, setIsRetrying] = useState(false)
  const statusRef = useRef<HTMLElement>(null)
  const statusQuery = usePasswordRecoveryStatusQuery(mode === 'status')

  const status: ForgotPasswordPageStatus =
    statusQuery.error || statusQuery.status?.state === 'delivery_issue'
      ? 'delivery_issue'
      : statusQuery.isLoading || !statusQuery.status
        ? 'loading'
        : statusQuery.status.state
  const retryAfterSeconds = statusQuery.status?.retryAfterSeconds ?? null
  const isSubmitting = isRequestPending || isRetrying

  useEffect(() => {
    if (mode === 'status') statusRef.current?.focus()
  }, [mode])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (isSubmitting) return

    const normalizedEmail = email.trim()
    if (!/^\S+@\S+\.\S+$/.test(normalizedEmail)) {
      setEmailError('Informe um e-mail válido.')
      setMessage('Revise o campo destacado.')
      return
    }

    setEmailError(null)
    setMessage(null)
    try {
      await requestPasswordRecovery(normalizedEmail)
      setMode('status')
    } catch {
      setMessage('Não foi possível solicitar a recuperação agora. Tente novamente.')
    }
  }

  async function handleRetry() {
    if (isSubmitting) return
    setIsRetrying(true)
    setMessage(null)
    try {
      await retryPasswordRecovery()
      await statusQuery.refetch()
    } catch {
      setMessage('Não foi possível solicitar a recuperação agora. Tente novamente.')
    } finally {
      setIsRetrying(false)
    }
  }

  function handleStartOver() {
    setMode('form')
    setEmailError(null)
    setMessage(null)
  }

  return {
    email,
    emailError,
    handleRetry,
    handleStartOver,
    isRetrying,
    isSubmitting,
    message,
    mode,
    retryAfterSeconds,
    status,
    statusRef,
    submit,
    setEmail,
  }
}
