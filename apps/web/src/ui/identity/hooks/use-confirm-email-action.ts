import { useCallback, useState } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

export const useConfirmEmailAction = () => {
  const { confirmEmail } = useAuthContext()
  const [error, setError] = useState<AuthError | null>(null)
  const [isPending, setIsPending] = useState(false)

  const handleConfirmEmail = useCallback(
    async (token: string) => {
      setError(null)
      setIsPending(true)
      try {
        return await confirmEmail(token)
      } catch (cause) {
        const authError =
          cause instanceof AuthError
            ? cause
            : new AuthError('unavailable', 'Não foi possível confirmar agora.', { cause })
        setError(authError)
        throw authError
      } finally {
        setIsPending(false)
      }
    },
    [confirmEmail],
  )

  return { confirmEmail: handleConfirmEmail, error, isPending }
}
