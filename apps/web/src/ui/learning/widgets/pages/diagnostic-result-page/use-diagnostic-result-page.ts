import { useQuery } from '@tanstack/react-query'

import { AuthError } from '@/core/errors/auth-error'
import { RestError } from '@/core/errors/rest-error'
import type { DiagnosticOverview } from '@/core/learning/goal-detail'
import type { SkillExperienceDetail } from '@/core/learning/skill-experience'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { getDiagnosticAction } from '@/ui/learning/widgets/pages/skill-page/use-skill-page'
import { getSkillExperienceAction } from '@/ui/learning/widgets/pages/skill-page/use-skill-experience'

export type DiagnosticResultPageProps = { goalId: string; skillId: string }

type DiagnosticResult = {
  diagnostic: DiagnosticOverview
  experience: SkillExperienceDetail
}

export function useDiagnosticResultPage(props: DiagnosticResultPageProps) {
  const { navigateTo } = useNavigation()
  const resultQuery = useQuery({
    queryKey: ['learning', 'diagnostic-result', props.goalId, props.skillId],
    queryFn: async (): Promise<DiagnosticResult> => {
      const [diagnostic, experience] = await Promise.all([
        getDiagnosticAction({ data: props }),
        getSkillExperienceAction({ data: props }),
      ])
      if ('kind' in diagnostic || 'kind' in experience) {
        if (
          ('kind' in diagnostic && diagnostic.kind === 'unauthorized') ||
          ('kind' in experience && experience.kind === 'unauthorized')
        ) {
          throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
            statusCode: 401,
          })
        }
        throw new RestError('Resultado não encontrado.', 404)
      }
      if (diagnostic.runState !== 'settled') {
        throw new RestError('Resultado não encontrado.', 404)
      }
      return { diagnostic, experience }
    },
    retry: false,
  })

  if (resultQuery.error instanceof AuthError) void navigateTo('login')

  return {
    diagnostic: resultQuery.data?.diagnostic ?? null,
    experience: resultQuery.data?.experience ?? null,
    isLoading: resultQuery.isPending,
    isPrivateAbsence:
      resultQuery.error instanceof RestError && resultQuery.error.statusCode === 404,
    isRecoverableError:
      Boolean(resultQuery.error) && !(resultQuery.error instanceof AuthError),
    handleRetry: resultQuery.refetch,
  }
}
