import { useDraggable, useDroppable } from '@dnd-kit/core'

import {
  BLANK_DROP_PREFIX,
  PLACED_WORD_DRAG_PREFIX,
} from '../../use-fill-blanks-question'

import type { BlankSlotProps } from '.'

export function useBlankSlot({
  blankKey,
  disabled,
  onActivate,
  placedWord,
}: BlankSlotProps) {
  const droppable = useDroppable({ id: `${BLANK_DROP_PREFIX}${blankKey}` })
  const draggable = useDraggable({
    disabled: disabled || placedWord === null,
    id: `${PLACED_WORD_DRAG_PREFIX}${blankKey}`,
  })
  const style = draggable.transform
    ? {
        transform: `translate3d(${draggable.transform.x}px, ${draggable.transform.y}px, 0)`,
      }
    : undefined

  function setNodeRef(node: HTMLElement | null) {
    droppable.setNodeRef(node)
    draggable.setNodeRef(node)
  }

  function handleActivate() {
    onActivate(blankKey)
  }

  return {
    isDragging: draggable.isDragging,
    isOver: droppable.isOver,
    listeners: draggable.listeners,
    style,
    setNodeRef,
    handleActivate,
  }
}
