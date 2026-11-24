import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useRouter } from '@tanstack/react-router'

import { AuthError } from '@/core/errors/auth-error'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

const ACCOUNT_CLOSURE_COMMITTED_KEY = 'shifu:account-closure-committed'

function getActionErrorMessage(error: unknown): string {
  if (error instanceof AuthError) return error.message
  return 'Não foi possível concluir agora. Tente novamente.'
}

function canRecoverClosedStatus(error: unknown): boolean {
  return (
    error instanceof AuthError &&
    (error.kind === 'result-uncertain' || error.kind === 'authentication-rejected')
  )
}

export function useDeleteAccountAction() {
  const auth = useAuthContext()
  const queryClient = useQueryClient()
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isCheckingStatus, setIsCheckingStatus] = useState(false)
  const [canCheckStatus, setCanCheckStatus] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isPasswordInvalid, setIsPasswordInvalid] = useState(false)

  async function showClosedStatus() {
    window.dispatchEvent(new Event(ACCOUNT_CLOSURE_COMMITTED_KEY))
    try {
      window.localStorage.setItem(ACCOUNT_CLOSURE_COMMITTED_KEY, crypto.randomUUID())
    } catch {
      // The current tab still receives the event; a later tab can revalidate on contact.
    }
    queryClient.clear()
    await router.invalidate({ sync: true })
  }

  async function submit(currentPassword: string) {
    setIsSubmitting(true)
    setErrorMessage(null)
    setIsPasswordInvalid(false)
    setCanCheckStatus(false)
    let prepared = false

    try {
      await auth.prepareAccountDeletion()
      prepared = true
      await auth.deleteAccount(currentPassword)
      await showClosedStatus()
    } catch (error) {
      if (prepared && canRecoverClosedStatus(error)) {
        setCanCheckStatus(true)
        try {
          await auth.getAccountDeletionStatus()
          await showClosedStatus()
          return
        } catch {
          // A failed status check never becomes evidence of closure.
        }
      }
      setErrorMessage(getActionErrorMessage(error))
      setIsPasswordInvalid(
        error instanceof AuthError && error.kind === 'invalid-current-password',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  async function checkStatus() {
    setIsCheckingStatus(true)
    setErrorMessage(null)
    setIsPasswordInvalid(false)
    try {
      await auth.getAccountDeletionStatus()
      await showClosedStatus()
    } catch {
      setErrorMessage(
        'Não foi possível confirmar o estado. Uma falha de conexão não confirma o encerramento.',
      )
    } finally {
      setIsCheckingStatus(false)
    }
  }

  function clearFeedback() {
    setCanCheckStatus(false)
    setErrorMessage(null)
    setIsPasswordInvalid(false)
  }

  return {
    canCheckStatus,
    errorMessage,
    isPasswordInvalid,
    isCheckingStatus,
    isSubmitting,
    clearFeedback,
    checkStatus,
    submit,
  }
}
