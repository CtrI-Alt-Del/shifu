import { useQuery } from '@tanstack/react-query'

import type { PracticeDraft } from '@/core/learning/choice-activity'

import { PracticeDraftRequestError } from './practice-draft-request-error'
import {
  type PracticeDraftIds,
  getPracticeDraftAction,
  isPracticeDraftFailure,
} from './practice-draft-server-functions'

export function practiceDraftQueryKey(ids: PracticeDraftIds | null) {
  return ['learning', 'practice-draft', ids?.activityId ?? null, ids?.skillId ?? null]
}

export type UsePracticeDraftQueryProps = {
  ids: PracticeDraftIds | null
  isEnabled: boolean
}

export const usePracticeDraftQuery = ({ ids, isEnabled }: UsePracticeDraftQueryProps) => {
  const {
    data: practiceDraft,
    error: practiceDraftFailure,
    refetch: reloadPracticeDraft,
  } = useQuery<PracticeDraft>({
    queryKey: practiceDraftQueryKey(ids),
    enabled: isEnabled && ids !== null,
    queryFn: async () => {
      if (!ids) throw new PracticeDraftRequestError('invalid-request')
      const result = await getPracticeDraftAction({ data: ids })
      if (isPracticeDraftFailure(result)) throw new PracticeDraftRequestError(result.kind)
      return result
    },
    retry: false,
    refetchOnMount: 'always',
    refetchOnWindowFocus: false,
    staleTime: 0,
  })

  return {
    practiceDraft,
    practiceDraftError:
      practiceDraftFailure instanceof PracticeDraftRequestError
        ? practiceDraftFailure
        : practiceDraftFailure
          ? new PracticeDraftRequestError('unavailable')
          : null,
    reloadPracticeDraft,
  }
}
