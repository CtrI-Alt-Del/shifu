import { useQuery } from '@tanstack/react-query'
import { AuthError } from '@/core/errors/auth-error'
import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'

export function useAccountProfileQuery(accountEmail: string) {
  const { getAccountProfile } = useAuthContext()
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['identity', 'account-profile', accountEmail],
    queryFn: getAccountProfile,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })
  async function refetchAccountProfile() {
    await refetch()
  }
  return {
    accountProfile: data ?? null,
    isLoadingAccountProfile: isPending,
    accountProfileError: error
      ? error instanceof AuthError
        ? error
        : new AuthError(
            'unavailable',
            'Não foi possível carregar sua conta. Tente novamente.',
          )
      : null,
    refetchAccountProfile,
  }
}
