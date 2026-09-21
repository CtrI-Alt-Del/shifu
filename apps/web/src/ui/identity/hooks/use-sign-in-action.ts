import { useCallback, useState } from 'react'

import { AuthError } from '@/core/errors/auth-error'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

export function useSignInAction() {
  const { signIn } = useAuthContext()
  const [error, setError] = useState<AuthError | null>(null)
  const [isPending, setIsPending] = useState(false)

  const handleSignIn = useCallback(
    async (input: Parameters<typeof signIn>[0]) => {
      setError(null)
      setIsPending(true)

      try {
        return await signIn(input)
      } catch (cause) {
        const authError =
          cause instanceof AuthError
            ? cause
            : new AuthError(
                'unavailable',
                'Não foi possível entrar agora. Tente novamente.',
                { cause },
              )
        setError(authError)
        throw authError
      } finally {
        setIsPending(false)
      }
    },
    [signIn],
  )

  return {
    error,
    isPending,
    signIn: handleSignIn,
  }
}
