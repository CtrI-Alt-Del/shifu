import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { AuthError } from '@/core/errors/auth-error'
import type { UpdateAccountProfileInput } from '@/provision/auth/cookie-session-auth-provider'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export const useUpdateAccountProfileAction = () => {
  const { updateAccountProfile: updateProfile } = useAuthContext()
  const { refreshCurrentRoute } = useNavigation()
  const queryClient = useQueryClient()
  const [refreshWarning, setRefreshWarning] = useState<string | null>(null)
  const { mutateAsync, isPending, error } = useMutation({
    mutationFn: (input: UpdateAccountProfileInput) => updateProfile(input),
    retry: false,
    async onSuccess(profile) {
      await queryClient.cancelQueries({
        queryKey: ['identity', 'account-profile', profile.email],
        exact: true,
      })
      queryClient.setQueryData(['identity', 'account-profile', profile.email], profile)
      setRefreshWarning(null)
      try {
        await refreshCurrentRoute()
      } catch {
        setRefreshWarning(
          'Perfil salvo. Não foi possível atualizar o menu agora. Recarregue a página para conferir seu nome.',
        )
      }
    },
  })
  return {
    isPending,
    error: error instanceof AuthError ? error : null,
    refreshWarning,
    updateAccountProfile: mutateAsync,
  }
}
