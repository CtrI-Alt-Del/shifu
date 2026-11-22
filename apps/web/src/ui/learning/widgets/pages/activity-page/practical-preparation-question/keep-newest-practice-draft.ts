import type { PracticeDraft } from '@/core/learning/choice-activity'

export function keepNewestPracticeDraft(
  current: PracticeDraft | undefined,
  incoming: PracticeDraft,
): PracticeDraft {
  return current && current.revision > incoming.revision ? current : incoming
}
