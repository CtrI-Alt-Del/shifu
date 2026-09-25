import { useCallback, useState } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

export const useResendConfirmationAction = () => {
  const { resendConfirmation } = useAuthContext()
  const [error, setError] = useState<AuthError | null>(null)
  const [isPending, setIsPending] = useState(false)

  const handleResendConfirmation = useCallback(async () => {
    setError(null)
    setIsPending(true)
    try {
      return await resendConfirmation()
    } catch (cause) {
      const authError =
        cause instanceof AuthError
          ? cause
          : new AuthError('unavailable', 'Não foi possível reenviar agora.', { cause })
      setError(authError)
      throw authError
    } finally {
      setIsPending(false)
    }
  }, [resendConfirmation])

  return { error, isPending, resendConfirmation: handleResendConfirmation }
}
