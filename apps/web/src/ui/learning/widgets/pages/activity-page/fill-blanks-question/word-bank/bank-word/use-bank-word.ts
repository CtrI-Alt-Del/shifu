import { useDraggable } from '@dnd-kit/core'

import { BANK_WORD_DRAG_PREFIX } from '../../use-fill-blanks-question'

import type { BankWordProps } from '.'

export function useBankWord({ disabled, onSelect, word }: BankWordProps) {
  const { isDragging, listeners, setNodeRef, transform } = useDraggable({
    disabled,
    id: `${BANK_WORD_DRAG_PREFIX}${word.key}`,
  })
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined

  function handleSelect() {
    onSelect(word.key)
  }

  return { isDragging, listeners, setNodeRef, style, handleSelect }
}
