import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'

import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import type { MentorSkillActionOutcome } from '@/core/learning/mentor-skill-action-outcome'
import { getBetterAuthProvider } from '@/provision/auth/better-auth/better-auth-provider'
import { createServerRequestClient } from '@/rest/axios/server-request-client'
import { LearningService } from '@/rest/services/learning-service'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z.object({ goalId: ID, confirmationId: ID, skillExperienceId: ID }).strict()

type ConfirmationResult =
  | { kind: 'success'; outcome: MentorSkillActionOutcome }
  | { kind: 'failure'; statusCode: number }

export type ConfirmMentorSkillRemovalInput = {
  confirmationId: string
  skillExperienceId: string
}

export const confirmMentorSkillRemovalServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }): Promise<ConfirmationResult> => {
    const access = await getBetterAuthProvider().getCurrentAccess(getRequest())
    if (!access)
      throw new AppError('Sua sessão expirou. Atualize a página.', 'Erro de autenticação')
    const { goalId, ...input } = data
    try {
      const outcome = await LearningService(
        createServerRequestClient(undefined),
      ).removeSkillExperienceFromMentor(access.accessToken, goalId, input)
      return { kind: 'success', outcome }
    } catch (error) {
      // The status code crosses the BFF boundary so the card can tell a safe failure
      // from an unknown result; any other failure is reported as status 0.
      return {
        kind: 'failure',
        statusCode: error instanceof RestError ? error.statusCode : 0,
      }
    }
  })

export const useConfirmMentorSkillRemovalAction = () => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async (input: ConfirmMentorSkillRemovalInput & { goalId: string }) => {
      const result = await confirmMentorSkillRemovalServer({ data: input })
      if (result.kind === 'failure')
        throw new RestError('Não foi possível confirmar a remoção.', result.statusCode)
      return result.outcome
    },
  })

  function confirmSkillRemoval(goalId: string, input: ConfirmMentorSkillRemovalInput) {
    return mutateAsync({ goalId, ...input })
  }

  return { confirmSkillRemoval, error, isPending }
}
