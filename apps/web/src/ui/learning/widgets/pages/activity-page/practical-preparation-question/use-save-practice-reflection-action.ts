import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { PracticeDraft } from '@/core/learning/choice-activity'

import { keepNewestPracticeDraft } from './keep-newest-practice-draft'
import { PracticeDraftRequestError } from './practice-draft-request-error'
import {
  type PracticeDraftIds,
  isPracticeDraftFailure,
  savePracticeReflectionAction,
} from './practice-draft-server-functions'
import { practiceDraftQueryKey } from './use-practice-draft-query'

export const useSavePracticeReflectionAction = (ids: PracticeDraftIds | null) => {
  const queryClient = useQueryClient()
  const { mutateAsync: savePracticeReflection } = useMutation({
    mutationFn: async (reflection: string) => {
      if (!ids) throw new PracticeDraftRequestError('invalid-request')
      const result = await savePracticeReflectionAction({ data: { ids, reflection } })
      if (isPracticeDraftFailure(result)) throw new PracticeDraftRequestError(result.kind)
      return result
    },
    onSuccess: (draft: PracticeDraft) => {
      queryClient.setQueryData<PracticeDraft>(practiceDraftQueryKey(ids), (current) =>
        keepNewestPracticeDraft(current, draft),
      )
    },
  })

  return { savePracticeReflection }
}
