import { z } from 'zod'
import { createServerFn } from '@tanstack/react-start'
import { getRequest } from '@tanstack/react-start/server'
import { useMutation } from '@tanstack/react-query'

import { RestError } from '@/core/errors/rest-error'
import type { MentorActionProposal } from '@/core/intelligence/mentor-action-proposal'
import { getMentorScopedService } from '@/provision/realtime/mentor-response-stream-server-provider'

const ID = z.string().regex(/^[0-9A-HJKMNP-TV-Z]{26}$/)
const INPUT = z.object({ sessionId: ID, proposalId: ID }).strict()

type DeclineResult =
  | { kind: 'success'; proposal: MentorActionProposal }
  | { kind: 'failure'; statusCode: number }

export const declineMentorActionProposalServer = createServerFn({ method: 'POST' })
  .validator((data: unknown) => INPUT.parse(data))
  .handler(async ({ data }): Promise<DeclineResult> => {
    const { accessToken, service } = await getMentorScopedService(getRequest())
    try {
      const proposal = await service.declineMentorActionProposal(
        accessToken,
        data.sessionId,
        data.proposalId,
      )
      return { kind: 'success', proposal }
    } catch (error) {
      return {
        kind: 'failure',
        statusCode: error instanceof RestError ? error.statusCode : 0,
      }
    }
  })

export const useDeclineMentorActionProposalAction = () => {
  const { error, isPending, mutateAsync } = useMutation({
    mutationFn: async (input: { sessionId: string; proposalId: string }) => {
      const result = await declineMentorActionProposalServer({ data: input })
      if (result.kind === 'failure')
        throw new RestError('Não foi possível recusar a ação.', result.statusCode)
      return result.proposal
    },
  })

  function declineActionProposal(sessionId: string, proposalId: string) {
    return mutateAsync({ sessionId, proposalId })
  }

  return { declineActionProposal, error, isPending }
}
