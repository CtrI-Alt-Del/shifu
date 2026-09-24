import { useCallback, useState } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

export const useRegisterAccountAction = () => {
  const { registerAccount } = useAuthContext()
  const [error, setError] = useState<AuthError | null>(null)
  const [isPending, setIsPending] = useState(false)

  const handleRegisterAccount = useCallback(
    async (input: Parameters<typeof registerAccount>[0]) => {
      setError(null)
      setIsPending(true)
      try {
        return await registerAccount(input)
      } catch (cause) {
        const authError =
          cause instanceof AuthError
            ? cause
            : new AuthError('unavailable', 'Não foi possível criar sua conta agora.', {
                cause,
              })
        setError(authError)
        throw authError
      } finally {
        setIsPending(false)
      }
    },
    [registerAccount],
  )

  return { error, isPending, registerAccount: handleRegisterAccount }
}
