import { useRef, useState } from 'react'
import { AuthError } from '@/core/errors/auth-error'
import type { ChangeAccountPasswordInput } from '@/provision/auth/cookie-session-auth-provider'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

export const useChangeAccountPasswordAction = () => {
  const { changeAccountPassword: changePassword } = useAuthContext()
  const [isPending, setIsPending] = useState(false)
  const [error, setError] = useState<AuthError | null>(null)
  const inFlightRef = useRef(false)
  async function changeAccountPassword(input: ChangeAccountPasswordInput) {
    if (inFlightRef.current)
      throw new AuthError('unavailable', 'Aguarde a tentativa em andamento.')
    inFlightRef.current = true
    setIsPending(true)
    setError(null)
    try {
      return await changePassword(input)
    } catch (cause) {
      const failure =
        cause instanceof AuthError
          ? cause
          : new AuthError(
              'result-uncertain',
              'Não foi possível confirmar a troca. Sua senha pode ter sido alterada. Este acesso continua disponível.',
            )
      setError(failure)
      throw failure
    } finally {
      inFlightRef.current = false
      setIsPending(false)
    }
  }
  return { isPending, error, changeAccountPassword }
}
