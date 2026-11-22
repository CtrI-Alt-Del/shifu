import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { PracticeDraft } from '@/core/learning/choice-activity'

import { keepNewestPracticeDraft } from './keep-newest-practice-draft'
import { PracticeDraftRequestError } from './practice-draft-request-error'
import {
  type PracticeDraftIds,
  isPracticeDraftFailure,
  removePracticePhotoAction,
} from './practice-draft-server-functions'
import { practiceDraftQueryKey } from './use-practice-draft-query'

export const useRemovePracticePhotoAction = (ids: PracticeDraftIds | null) => {
  const queryClient = useQueryClient()
  const { mutateAsync: removePracticePhoto } = useMutation({
    mutationFn: async (recordKey: string) => {
      if (!ids) throw new PracticeDraftRequestError('invalid-request')
      const result = await removePracticePhotoAction({ data: { ids, recordKey } })
      if (isPracticeDraftFailure(result)) throw new PracticeDraftRequestError(result.kind)
      return result
    },
    onSuccess: (draft: PracticeDraft) => {
      queryClient.setQueryData<PracticeDraft>(practiceDraftQueryKey(ids), (current) =>
        keepNewestPracticeDraft(current, draft),
      )
    },
  })

  return { removePracticePhoto }
}
