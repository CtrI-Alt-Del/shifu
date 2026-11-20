import { useDroppable } from '@dnd-kit/core'

import { BANK_DROP_ID } from '../use-fill-blanks-question'

export function useWordBank() {
  const { isOver, setNodeRef } = useDroppable({ id: BANK_DROP_ID })

  return { isOver, setNodeRef }
}
