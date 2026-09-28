import { useEffect, useRef, useState, type FormEvent } from 'react'

import { ROUTES } from '@/constants/routes'
import { useResetPasswordAction } from '@/ui/identity/hooks/use-reset-password-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type ResetPasswordPageResult =
  | 'resolving'
  | 'form'
  | 'reset'
  | 'expired'
  | 'used'
  | 'invalid'
  | 'unavailable'

export function useResetPasswordPage(token: string | undefined) {
  const { getPasswordResetLinkStatus, resetPassword } = useResetPasswordAction()
  const { navigateTo } = useNavigation()
  const initialToken = useRef(token).current
  const [result, setResult] = useState<ResetPasswordPageResult>(
    isRecoveryToken(initialToken) ? 'resolving' : 'invalid',
  )
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [passwordError, setPasswordError] = useState<string | null>(null)
  const [confirmationError, setConfirmationError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [requiresEmailConfirmation, setRequiresEmailConfirmation] = useState(false)
  const [isPasswordVisible, setPasswordVisible] = useState(false)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    window.history.replaceState({}, '', ROUTES.resetPassword)
  }, [])

  useEffect(() => {
    if (!isRecoveryToken(initialToken)) return

    let isCurrent = true
    void getPasswordResetLinkStatus(initialToken)
      .then((response) => {
        if (isCurrent) setResult(response.result === 'valid' ? 'form' : response.result)
      })
      .catch(() => {
        if (isCurrent) {
          setResult('unavailable')
          setMessage('Não foi possível verificar este link agora. Tente novamente.')
        }
      })

    return () => {
      isCurrent = false
    }
  }, [getPasswordResetLinkStatus, initialToken])

  useEffect(() => {
    if (result !== 'form') headingRef.current?.focus()
  }, [result])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    event.stopPropagation()
    if (isSubmitting || result !== 'form') return

    const nextPasswordError =
      password.length < 8 ? 'A senha deve ter pelo menos 8 caracteres.' : null
    const nextConfirmationError =
      password !== passwordConfirmation ? 'As senhas precisam ser iguais.' : null
    setPasswordError(nextPasswordError)
    setConfirmationError(nextConfirmationError)
    if (nextPasswordError || nextConfirmationError) {
      setMessage('Revise os campos destacados.')
      return
    }

    if (!isRecoveryToken(initialToken)) {
      setResult('invalid')
      return
    }

    setMessage(null)
    setIsSubmitting(true)
    try {
      const response = await resetPassword(initialToken, password, passwordConfirmation)
      if (response.result === 'reset') {
        setRequiresEmailConfirmation(response.requiresEmailConfirmation)
        setResult('reset')
      }
      if (response.result !== 'reset') setResult(response.result)
      setPassword('')
      setPasswordConfirmation('')
      if (response.result === 'reset') await navigateTo('login')
    } catch {
      setResult('unavailable')
      setMessage('Não foi possível redefinir sua senha agora. Tente novamente.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleContinue() {
    await navigateTo('login')
  }

  async function handleRequestNewLink() {
    await navigateTo('forgotPassword')
  }

  function handleRetry() {
    setMessage(null)
    if (!isRecoveryToken(initialToken)) return
    setResult('resolving')
    void getPasswordResetLinkStatus(initialToken)
      .then((response) =>
        setResult(response.result === 'valid' ? 'form' : response.result),
      )
      .catch(() => {
        setResult('unavailable')
        setMessage('Não foi possível verificar este link agora. Tente novamente.')
      })
  }

  return {
    confirmationError,
    handleContinue,
    handleRetry,
    handleRequestNewLink,
    headingRef,
    isPasswordVisible,
    isSubmitting,
    message,
    password,
    passwordConfirmation,
    passwordError,
    requiresEmailConfirmation,
    result,
    setPassword,
    setPasswordConfirmation,
    setPasswordVisible,
    submit,
  }
}

function isRecoveryToken(value: string | undefined): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{43}$/.test(value)
}
